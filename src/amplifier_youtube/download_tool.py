"""YouTube Download Tool — downloads audio/video and captures screenshots."""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from amplifier_core.models import ToolResult

from .core import VideoLoader

logger = logging.getLogger(__name__)


class YouTubeDownloadTool:
    """Download audio or video from YouTube URLs or local files."""

    def __init__(self, config: dict[str, Any]):
        self.output_dir = Path(config.get("output_dir", "~/downloads")).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_only = config.get("audio_only", True)
        cookies_file = config.get("cookies_file")
        self.loader = VideoLoader(cookies_file=Path(cookies_file).expanduser() if cookies_file else None)

    @property
    def name(self) -> str:
        return "youtube-dl"

    @property
    def description(self) -> str:
        return "Download audio or video from YouTube with metadata extraction and screenshot capture"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube URL or local file path"},
                "audio_only": {
                    "type": "boolean",
                    "description": "Download audio (True) or full video (False). Overrides config.",
                },
                "output_filename": {"type": "string", "description": "Custom output filename"},
                "use_cache": {"type": "boolean", "description": "Use cached file if exists (default: true)"},
                "capture_screenshot": {"type": "boolean", "description": "Extract a screenshot (default: false)"},
                "screenshot_time": {
                    "type": "string",
                    "description": "Timestamp HH:MM:SS (required if capture_screenshot is true)",
                },
            },
            "required": ["url"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            url = input.get("url")
            if not url:
                return ToolResult(success=False, error={"message": "Missing required parameter: url"})

            audio_only = input.get("audio_only", self.audio_only)
            output_filename = input.get("output_filename")
            use_cache = input.get("use_cache", True)
            capture_screenshot = input.get("capture_screenshot", False)
            screenshot_time = input.get("screenshot_time")

            if capture_screenshot and not screenshot_time:
                return ToolResult(
                    success=False, error={"message": "screenshot_time required when capture_screenshot is True"}
                )

            logger.info(f"Loading video info from: {url}")
            video_info = self.loader.load(url)

            downloaded_path: Path

            if video_info.type == "url":
                if audio_only:
                    filename = output_filename or "audio.mp3"
                    downloaded_path = self.loader.download_audio(url, self.output_dir, filename, use_cache)
                    video_info.audio_path = downloaded_path
                else:
                    filename = output_filename or "video.mp4"
                    downloaded_path = self.loader.download_video(url, self.output_dir, filename, use_cache)
                    video_info.video_path = downloaded_path
            else:
                downloaded_path = Path(video_info.source)

            screenshot_path = None
            if capture_screenshot:
                if not isinstance(screenshot_time, str):
                    return ToolResult(success=False, error={"message": "screenshot_time must be a string in HH:MM:SS format"})
                screenshot_filename = (
                    Path(output_filename).with_suffix(".jpg").name if output_filename else "screenshot.jpg"
                )
                screenshot_output = self.output_dir / screenshot_filename
                logger.info(f"Capturing screenshot at {screenshot_time}")
                screenshot_path = self.loader.capture_screenshot(downloaded_path, screenshot_time, screenshot_output)

            result_data: dict[str, Any] = {"path": str(downloaded_path), "metadata": asdict(video_info)}
            if screenshot_path:
                result_data["screenshot_path"] = str(screenshot_path)

            logger.info(f"Download complete: {downloaded_path.name}")
            return ToolResult(success=True, output=result_data)

        except ValueError as e:
            logger.error(f"Download failed: {e}")
            return ToolResult(success=False, error={"message": str(e), "type": "ValueError"})
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return ToolResult(success=False, error={"message": str(e), "type": type(e).__name__})
