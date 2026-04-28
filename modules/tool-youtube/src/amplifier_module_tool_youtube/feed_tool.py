"""YouTube Feed Tool — accesses authenticated account feeds via yt-dlp + cookies."""

import logging
from pathlib import Path
from typing import Any

import yt_dlp
from amplifier_core.models import ToolResult

logger = logging.getLogger(__name__)


class YouTubeFeedTool:
    """Access YouTube account feeds: history, subscriptions, liked, recommendations, watch later."""

    FEED_MAP = {
        "history": ":ythistory",
        "subscriptions": ":ytsubs",
        "liked": ":ytfav",
        "recommendations": ":ytrec",
        "watch_later": ":ytwatchlater",
    }

    def __init__(self, config: dict[str, Any], cookies_file: str | None = None):
        self.cookies_file = cookies_file or config.get("cookies_file")

    @property
    def name(self) -> str:
        return "youtube-feed"

    @property
    def description(self) -> str:
        return (
            "Access your YouTube account feeds: watch history, subscriptions, liked videos, "
            "recommendations, and watch later. Returns metadata only — pass URLs to youtube-dl to download. "
            "Requires cookies_file to be configured."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feed_type": {
                    "type": "string",
                    "enum": ["history", "subscriptions", "liked", "recommendations", "watch_later"],
                    "description": "Which account feed to retrieve",
                },
                "limit": {"type": "integer", "description": "Max items to return (default: 50)"},
            },
            "required": ["feed_type"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        if not self.cookies_file:
            return ToolResult(
                success=False,
                error={
                    "message": (
                        "youtube-feed requires cookies_file to be configured. "
                        "Export your browser cookies to a Netscape-format file and set "
                        "cookies_file in your bundle config."
                    )
                },
            )

        feed_type = input.get("feed_type")
        if feed_type not in self.FEED_MAP:
            return ToolResult(
                success=False,
                error={"message": f"Invalid feed_type. Must be one of: {', '.join(self.FEED_MAP)}"},
            )

        limit = input.get("limit", 50)
        yt_target = self.FEED_MAP[feed_type]

        try:
            ydl_opts = {
                "quiet": True,
                "extract_flat": True,
                "no_warnings": True,
                "cookiefile": str(Path(self.cookies_file).expanduser()),
                "playlistend": limit,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(yt_target, download=False)

            if info is None:
                return ToolResult(
                    success=False,
                    error={
                        "message": f"No data returned for feed '{feed_type}'. The feed may be temporarily unavailable."
                    },
                )

            items = []
            for entry in info.get("entries") or []:
                vid_id = entry.get("id", "")
                items.append(
                    {
                        "id": vid_id,
                        "title": entry.get("title", ""),
                        "channel": entry.get("channel", entry.get("uploader", "")),
                        "url": entry.get("url") or f"https://youtube.com/watch?v={vid_id}",
                        "upload_date": entry.get("upload_date", ""),
                        "duration_seconds": entry.get("duration"),
                    }
                )

            return ToolResult(success=True, output={"feed_type": feed_type, "items": items, "count": len(items)})

        except Exception as e:
            logger.error(f"Feed access failed for {feed_type}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error={
                    "message": str(e),
                    "hint": "If you see an authentication error, your cookies may have expired. Try re-exporting from your browser.",
                },
            )
