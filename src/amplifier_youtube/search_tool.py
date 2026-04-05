"""YouTube Search Tool — searches with Data API (rich filters) or yt-dlp fallback."""

import logging
from typing import Any

import yt_dlp
from amplifier_core.models import ToolResult

logger = logging.getLogger(__name__)


def build(*args: Any, **kwargs: Any) -> Any:
    """Lazy proxy — delegates to googleapiclient.discovery.build on first API call.

    Defined at module level so tests can patch amplifier_youtube.search_tool.build
    without requiring a top-level import of google-api-python-client.
    """
    from googleapiclient.discovery import build as _build

    return _build(*args, **kwargs)


class YouTubeSearchTool:
    """Search YouTube videos. Uses Data API when api_key configured, yt-dlp otherwise."""

    def __init__(self, config: dict[str, Any]):
        self.api_key = config.get("api_key")
        self.default_max_results = config.get("max_results", 10)
        self.safe_search = config.get("safe_search", True)

    @property
    def name(self) -> str:
        return "youtube-search"

    @property
    def description(self) -> str:
        return (
            "Search YouTube for videos. When an API key is configured, supports rich filters "
            "(duration, date range, region, HD). Without an API key, searches by keyword and order only."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"},
                "max_results": {"type": "integer", "description": "Number of results (max 50, default 10)"},
                "order": {
                    "type": "string",
                    "enum": ["relevance", "date", "viewCount", "rating"],
                    "description": "Sort order. viewCount and rating require API key; yt-dlp supports relevance and date only.",
                },
                "duration": {
                    "type": "string",
                    "enum": ["any", "short", "medium", "long"],
                    "description": "short=<4min, medium=4-20min, long=>20min. Requires API key.",
                },
                "published_after": {
                    "type": "string",
                    "description": "ISO 8601 date filter (e.g. 2025-01-01T00:00:00Z). Requires API key.",
                },
                "published_before": {"type": "string", "description": "ISO 8601 date filter. Requires API key."},
                "region_code": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-2 country code (e.g. US). Requires API key.",
                },
                "hd_only": {"type": "boolean", "description": "Filter for HD content only. Requires API key."},
            },
            "required": ["query"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        query = input.get("query")
        if not query:
            return ToolResult(success=False, error={"message": "Missing required parameter: query"})

        max_results = input.get("max_results", self.default_max_results)

        if self.api_key:
            try:
                return await self._search_with_api(input, max_results)
            except Exception as e:
                logger.warning(f"YouTube Data API failed ({e}), falling back to yt-dlp")

        return await self._search_with_ytdlp(input, max_results)

    async def _search_with_api(self, input: dict[str, Any], max_results: int) -> ToolResult:
        youtube = build("youtube", "v3", developerKey=self.api_key)

        params: dict[str, Any] = {
            "q": input["query"],
            "part": "snippet",
            "type": "video",
            "maxResults": min(max_results, 50),
            "safeSearch": "moderate" if self.safe_search else "none",
        }

        order = input.get("order", "relevance")
        if order in ("relevance", "date", "viewCount", "rating"):
            params["order"] = order
        if input.get("duration") and input["duration"] != "any":
            params["videoDuration"] = input["duration"]
        if input.get("published_after"):
            params["publishedAfter"] = input["published_after"]
        if input.get("published_before"):
            params["publishedBefore"] = input["published_before"]
        if input.get("region_code"):
            params["regionCode"] = input["region_code"]
        if input.get("hd_only"):
            params["videoDefinition"] = "high"

        response = youtube.search().list(**params).execute()

        results = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            results.append(
                {
                    "id": video_id,
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"][:10],
                    "description": snippet.get("description", ""),
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "duration_seconds": None,
                }
            )

        return ToolResult(success=True, output={"results": results, "backend": "api", "total_results": len(results)})

    async def _search_with_ytdlp(self, input: dict[str, Any], max_results: int) -> ToolResult:
        order = input.get("order", "relevance")
        prefix = "ytsearchdate" if order == "date" else "ytsearch"
        search_query = f"{prefix}{max_results}:{input['query']}"

        ydl_opts = {"quiet": True, "extract_flat": True, "no_warnings": True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        results = []
        for entry in info.get("entries") or []:
            vid_id = entry.get("id", "")
            results.append(
                {
                    "id": vid_id,
                    "title": entry.get("title", ""),
                    "channel": entry.get("channel", entry.get("uploader", "")),
                    "published_at": entry.get("upload_date", ""),
                    "description": entry.get("description", ""),
                    "url": entry.get("url") or f"https://youtube.com/watch?v={vid_id}",
                    "duration_seconds": entry.get("duration"),
                }
            )

        return ToolResult(success=True, output={"results": results, "backend": "ytdlp", "total_results": len(results)})
