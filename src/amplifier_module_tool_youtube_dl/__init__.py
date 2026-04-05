"""
Amplifier YouTube-DL Tool Module

Download audio and video from YouTube with metadata extraction.
"""

import logging
from typing import Any

from .audio_utils import AudioExtractor
from .core import VideoInfo, VideoLoader
from .youtube_tool import YouTubeDLTool

logger = logging.getLogger(__name__)

__all__ = ["YouTubeDLTool", "VideoInfo", "VideoLoader", "AudioExtractor", "mount"]


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mount the YouTube download tool into the coordinator.

    This is the Amplifier module entry point. It instantiates YouTubeDLTool
    with the provided config and registers it with the coordinator.

    Args:
        coordinator: The Amplifier coordinator to mount into.
        config: Optional tool configuration with keys:
            - output_dir: Directory to save downloads (default: ~/downloads)
            - audio_only: Whether to download audio only vs full video (default: True)
            - cookies_file: Optional path to cookies file for yt-dlp

    Returns:
        Module manifest describing what was registered.
    """
    tool = YouTubeDLTool(config or {})
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("tool-youtube-dl mounted: registered 'youtube-dl'")
    return {
        "name": "tool-youtube-dl",
        "version": "0.1.0",
        "provides": ["youtube-dl"],
    }
