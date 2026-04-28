"""Amplifier YouTube Module — download, search, and account feed access."""

import logging
from typing import Any

from .audio_utils import AudioExtractor
from .core import VideoInfo, VideoLoader
from .download_tool import YouTubeDownloadTool
from .feed_tool import YouTubeFeedTool
from .search_tool import YouTubeSearchTool
from .transcript import TranscriptFetcher, TranscriptResult

logger = logging.getLogger(__name__)

__all__ = [
    "YouTubeDownloadTool",
    "YouTubeSearchTool",
    "YouTubeFeedTool",
    "VideoInfo",
    "VideoLoader",
    "AudioExtractor",
    "TranscriptFetcher",
    "TranscriptResult",
    "mount",
]


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """Mount all three YouTube tools into the coordinator."""
    cfg = config or {}
    cookies_file = cfg.get("cookies_file")

    dl_tool = YouTubeDownloadTool(cfg)
    search_tool = YouTubeSearchTool(cfg.get("search", {}))
    feed_tool = YouTubeFeedTool(cfg.get("feed", {}), cookies_file=cookies_file)

    await coordinator.mount("tools", dl_tool, name=dl_tool.name)
    await coordinator.mount("tools", search_tool, name=search_tool.name)
    await coordinator.mount("tools", feed_tool, name=feed_tool.name)

    logger.info("youtube module mounted: youtube-dl, youtube-search, youtube-feed")
