"""
YouTube Download Tool Implementation

Implements Tool protocol for YouTube audio/video downloading.
"""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from amplifier_core.models import ToolResult

from .core import VideoLoader

logger = logging.getLogger(__name__)


class YouTubeDLTool:
    """YouTube download tool with audio, video, and screenshot support."""

    def __init__(self, config: dict[str, Any]):
        """Initialize YouTube download tool.

        Args:
            config: Tool configuration with keys:
                - output_dir: Directory to save downloads (default: ~/downloads)
                - audio_only: Whether to download audio only vs full video (default: True)
                - cookies_file: Optional path to cookies file for yt-dlp
        """
        self.output_dir = Path(config.get("output_dir", "~/downloads")).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.audio_only = config.get("audio_only", True)

        cookies_file = config.get("cookies_file")
        self.loader = VideoLoader(cookies_file=Path(cookies_file).expanduser() if cookies_file else None)

    @property
    def name(self) -> str:
        """Tool name for invocation."""
        return "youtube-dl"

    @property
    def description(self) -> str:
        """Human-readable tool description."""
        return "Download audio or video from YouTube with metadata extraction and screenshot capture"

    @property
    def input_schema(self) -> dict:
        """JSON Schema for tool input validation."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "YouTube URL or local file path to process",
                },
                "audio_only": {
                    "type": "boolean",
                    "description": "Download audio only (True) vs full video (False). Overrides config setting.",
                },
                "output_filename": {
                    "type": "string",
                    "description": "Custom output filename (optional)",
                },
                "use_cache": {
                    "type": "boolean",
                    "description": "Use cached file if exists (default: True)",
                },
                "capture_screenshot": {
                    "type": "boolean",
                    "description": "Extract a screenshot from the video (default: False)",
                },
                "screenshot_time": {
                    "type": "string",
                    "description": "Timestamp for screenshot in HH:MM:SS format (required if capture_screenshot is True)",
                },
            },
            "required": ["url"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute YouTube download.

        Args:
            input: Tool input with keys:
                - url: YouTube URL or local file path (required)
                - audio_only: Override config setting for this request (optional)
                - output_filename: Custom filename (optional)
                - use_cache: Use cached file if exists (default: True)
                - capture_screenshot: Extract screenshot (default: False)
                - screenshot_time: Timestamp for screenshot in HH:MM:SS format
                                   (required if capture_screenshot is True)

        Returns:
            ToolResult with output containing:
                - path: Path to downloaded file
                - metadata: VideoInfo as dict
                - screenshot_path: Path to screenshot (if requested)
        """
        try:
            url = input.get("url")
            if not url:
                return ToolResult(success=False, error={"message": "Missing required parameter: url"})

            # Get configuration
            audio_only = input.get("audio_only", self.audio_only)
            output_filename = input.get("output_filename")
            use_cache = input.get("use_cache", True)
            capture_screenshot = input.get("capture_screenshot", False)
            screenshot_time = input.get("screenshot_time")

            # Validate screenshot parameters
            if capture_screenshot and not screenshot_time:
                return ToolResult(
                    success=False, error={"message": "screenshot_time required when capture_screenshot is True"}
                )

            # Load video metadata
            logger.info(f"Loading video info from: {url}")
            video_info = self.loader.load(url)

            # Determine download path
            downloaded_path: Path

            # If URL, download it
            if video_info.type == "url":
                if audio_only:
                    # Download audio
                    filename = output_filename or "audio.mp3"
                    downloaded_path = self.loader.download_audio(url, self.output_dir, filename, use_cache)
                    video_info.audio_path = downloaded_path
                else:
                    # Download video
                    filename = output_filename or "video.mp4"
                    downloaded_path = self.loader.download_video(url, self.output_dir, filename, use_cache)
                    video_info.video_path = downloaded_path
            else:
                # Local file - just use the path
                downloaded_path = Path(video_info.source)

            # Capture screenshot if requested
            screenshot_path = None
            if capture_screenshot:
                # screenshot_time is guaranteed to be a str here — validated above
                assert isinstance(screenshot_time, str)
                screenshot_filename = output_filename.replace(".mp4", ".jpg") if output_filename else "screenshot.jpg"
                screenshot_output = self.output_dir / screenshot_filename

                logger.info(f"Capturing screenshot at {screenshot_time}")
                screenshot_path = self.loader.capture_screenshot(downloaded_path, screenshot_time, screenshot_output)

            # Build result
            result_data = {
                "path": str(downloaded_path),
                "metadata": asdict(video_info),
            }

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
