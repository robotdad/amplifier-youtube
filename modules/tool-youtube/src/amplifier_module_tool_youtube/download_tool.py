"""YouTube Download Tool — downloads audio/video and captures screenshots."""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from amplifier_core.models import ToolResult

from .core import VideoInfo, VideoLoader
from .transcript import TranscriptFetcher, TranscriptResult

logger = logging.getLogger(__name__)

_PATH_FIELDS = frozenset({"audio_path", "video_path", "transcript_path", "transcript_raw_path"})


def _serialize_video_info(info: VideoInfo) -> dict[str, Any]:
    """Convert VideoInfo to a JSON-safe dict (Path → str)."""
    d = asdict(info)
    for key in _PATH_FIELDS:
        if d.get(key) is not None:
            d[key] = str(d[key])
    return d


class YouTubeDownloadTool:
    """Download audio or video from YouTube URLs or local files."""

    def __init__(self, config: dict[str, Any]):
        self.output_dir = Path(config.get("output_dir", "~/downloads")).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_only = config.get("audio_only", True)
        self.prefer_transcript_default: bool = config.get("prefer_transcript", True)
        self.transcript_languages_default: list[str] = config.get("transcript_languages", ["en"])
        cookies_file = config.get("cookies_file")
        cookies_path = Path(cookies_file).expanduser() if cookies_file else None
        self.loader = VideoLoader(cookies_file=cookies_path)
        self.transcript_fetcher = TranscriptFetcher(cookies_file=cookies_path)

    @property
    def name(self) -> str:
        return "youtube-dl"

    @property
    def description(self) -> str:
        return "Download audio or video from YouTube with metadata extraction and screenshot capture"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube URL or local file path"},
                "audio_only": {
                    "type": "boolean",
                    "description": "Download audio (True) or full video (False). Overrides config. Ignored in transcript-first mode.",
                },
                "prefer_transcript": {
                    "type": "boolean",
                    "description": (
                        "Transcript-first mode (default true): download video then attempt to fetch "
                        "existing subtitles or auto-captions via yt-dlp. audio_only is ignored in "
                        "this mode. Set to false to use legacy audio-only/video-only behaviour."
                    ),
                },
                "transcript_languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        'ISO 639-1 language codes in priority order for transcript lookup (default: ["en"]).'
                    ),
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

            prefer_transcript: bool = input.get("prefer_transcript", self.prefer_transcript_default)
            transcript_languages: list[str] = input.get("transcript_languages", self.transcript_languages_default)
            audio_only: bool = input.get("audio_only", self.audio_only)
            output_filename: str | None = input.get("output_filename")
            use_cache: bool = input.get("use_cache", True)
            capture_screenshot: bool = input.get("capture_screenshot", False)
            screenshot_time: str | None = input.get("screenshot_time")

            if capture_screenshot and not screenshot_time:
                return ToolResult(
                    success=False, error={"message": "screenshot_time required when capture_screenshot is True"}
                )

            logger.info(f"Loading video info from: {url}")
            video_info = self.loader.load(url)

            downloaded_path: Path
            transcript_result: TranscriptResult | None = None

            if video_info.type == "url":
                if prefer_transcript:
                    # ----------------------------------------------------------
                    # Transcript-first mode: download video then attempt to fetch
                    # existing subtitles/auto-captions (audio_only is ignored).
                    # ----------------------------------------------------------
                    filename = output_filename or "video.mp4"
                    downloaded_path = self.loader.download_video(url, self.output_dir, filename, use_cache)
                    video_info.video_path = downloaded_path

                    output_stem = Path(filename).stem
                    try:
                        transcript_result = self.transcript_fetcher.fetch(
                            url,
                            self.output_dir,
                            output_stem,
                            languages=transcript_languages,
                            use_cache=use_cache,
                        )
                    except Exception as exc:
                        logger.warning(f"Transcript fetch failed (soft failure): {exc}")
                        transcript_result = TranscriptResult(available=False)

                    if transcript_result.available:
                        video_info.transcript_text = transcript_result.text
                        video_info.transcript_path = transcript_result.text_path
                        video_info.transcript_raw_path = transcript_result.raw_path
                        video_info.transcript_language = transcript_result.language
                        video_info.transcript_source = transcript_result.source
                else:
                    # ----------------------------------------------------------
                    # Legacy mode: respect audio_only flag, no transcript fetch.
                    # ----------------------------------------------------------
                    if audio_only:
                        filename = output_filename or "audio.mp3"
                        downloaded_path = self.loader.download_audio(url, self.output_dir, filename, use_cache)
                        video_info.audio_path = downloaded_path
                    else:
                        filename = output_filename or "video.mp4"
                        downloaded_path = self.loader.download_video(url, self.output_dir, filename, use_cache)
                        video_info.video_path = downloaded_path
            else:
                # Local file: no transcript attempt.
                downloaded_path = Path(video_info.source)

            screenshot_path = None
            if capture_screenshot:
                if not isinstance(screenshot_time, str):
                    return ToolResult(
                        success=False, error={"message": "screenshot_time must be a string in HH:MM:SS format"}
                    )
                screenshot_filename = (
                    Path(output_filename).with_suffix(".jpg").name if output_filename else "screenshot.jpg"
                )
                screenshot_output = self.output_dir / screenshot_filename
                logger.info(f"Capturing screenshot at {screenshot_time}")
                screenshot_path = self.loader.capture_screenshot(downloaded_path, screenshot_time, screenshot_output)

            result_data: dict[str, Any] = {"path": str(downloaded_path), "metadata": _serialize_video_info(video_info)}
            if screenshot_path:
                result_data["screenshot_path"] = str(screenshot_path)

            # Add transcript outcome to result when in transcript-first mode.
            if transcript_result is not None:
                if transcript_result.available:
                    result_data["transcript_available"] = True
                    result_data["transcript"] = {
                        "text": transcript_result.text,
                        "language": transcript_result.language,
                        "source": transcript_result.source,
                        "raw_path": str(transcript_result.raw_path) if transcript_result.raw_path else None,
                        "text_path": str(transcript_result.text_path) if transcript_result.text_path else None,
                    }
                else:
                    result_data["transcript_available"] = False
                    result_data["fallback_hint"] = "no_transcript_use_whisper_on_video"

            logger.info(f"Download complete: {downloaded_path.name}")
            return ToolResult(success=True, output=result_data)

        except ValueError as e:
            logger.error(f"Download failed: {e}")
            return ToolResult(success=False, error={"message": str(e), "type": "ValueError"})
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return ToolResult(success=False, error={"message": str(e), "type": type(e).__name__})
