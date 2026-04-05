"""
Video Loader Core Implementation

Extracts video information and downloads from YouTube or local files.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import yt_dlp

    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Video information container."""

    source: str  # URL or file path
    type: str  # "url" or "file"
    title: str
    id: str
    duration: float  # seconds
    description: str = ""
    uploader: str = ""
    audio_path: Path | None = None
    video_path: Path | None = None


class VideoLoader:
    """Load videos from URLs or local files."""

    def __init__(self, cookies_file: Path | None = None):
        """Initialize video loader.

        Args:
            cookies_file: Optional path to cookies file for yt-dlp
        """
        self.cookies_file = cookies_file.expanduser() if cookies_file else None
        self.yt_dlp_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        if self.cookies_file and self.cookies_file.exists():
            self.yt_dlp_opts["cookiefile"] = str(self.cookies_file)

    def load(self, source: str) -> VideoInfo:
        """Load video information from URL or file.

        Args:
            source: YouTube URL or local file path

        Returns:
            VideoInfo object with video metadata

        Raises:
            ValueError: If source cannot be loaded
        """
        if self._is_url(source):
            return self._load_from_url(source)
        return self._load_from_file(source)

    def _is_url(self, source: str) -> bool:
        """Check if source is a URL."""
        return source.startswith(("http://", "https://", "www."))

    def _load_from_url(self, url: str) -> VideoInfo:
        """Load video info from YouTube URL."""
        if not YT_DLP_AVAILABLE:
            raise ValueError("yt-dlp is not installed. Install with: pip install yt-dlp")

        logger.info(f"Loading video info from: {url}")

        try:
            with yt_dlp.YoutubeDL(self.yt_dlp_opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=False)

            return VideoInfo(
                source=url,
                type="url",
                title=str(info.get("title", "Unknown")),
                id=str(info.get("id", url)),
                duration=float(info.get("duration") or 0),
                description=str(info.get("description", "")),
                uploader=str(info.get("uploader", "")),
            )
        except Exception as e:
            raise ValueError(f"Failed to load URL {url}: {e}")

    def _load_from_file(self, filepath: str) -> VideoInfo:
        """Load video info from local file."""
        path = Path(filepath).expanduser()

        if not path.exists():
            raise ValueError(f"File not found: {filepath}")
        if not path.is_file():
            raise ValueError(f"Not a file: {filepath}")

        logger.info(f"Loading video info from: {path.name}")

        # Get duration using ffprobe
        duration = 0.0
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_info = json.loads(result.stdout)
            if "format" in probe_info and "duration" in probe_info["format"]:
                duration = float(probe_info["format"]["duration"])
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not get duration: {e}")

        return VideoInfo(
            source=str(path.absolute()),
            type="file",
            title=path.stem,
            id=path.stem,
            duration=duration,
        )

    def download_audio(
        self, url: str, output_dir: Path, output_filename: str = "audio.mp3", use_cache: bool = True
    ) -> Path:
        """Download audio from YouTube URL.

        Args:
            url: YouTube URL
            output_dir: Directory to save audio
            output_filename: Name for the output file (default: "audio.mp3")
            use_cache: If True, skip download if file exists (default: True)

        Returns:
            Path to downloaded audio file

        Raises:
            ValueError: If download fails
        """
        if not YT_DLP_AVAILABLE:
            raise ValueError("yt-dlp is not installed")

        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        # Check cache
        if use_cache and output_path.exists():
            logger.info(f"✓ Using cached audio: {output_path.name}")
            return output_path

        logger.info(f"Downloading audio from: {url}")

        # Configure for audio extraction
        # Remove extension from output filename for yt-dlp template
        output_stem = output_path.stem
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": str(output_dir / f"{output_stem}.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                ydl.extract_info(url, download=True)

                # The file should be at output_path after conversion to mp3
                if output_path.exists():
                    logger.info(f"Audio saved to: {output_path.name}")
                    return output_path

                # If not at expected location, look for it
                # Check for various extensions in case conversion didn't happen
                for ext in [".mp3", ".m4a", ".opus", ".wav"]:
                    possible_path = output_dir / f"{output_stem}{ext}"
                    if possible_path.exists():
                        # Move to expected location
                        possible_path.rename(output_path)
                        logger.info(f"Audio saved to: {output_path.name}")
                        return output_path

                raise ValueError("Could not find downloaded audio file")

        except Exception as e:
            raise ValueError(f"Failed to download audio: {e}")

    def download_video(
        self, url: str, output_dir: Path, output_filename: str = "video.mp4", use_cache: bool = True
    ) -> Path:
        """Download video from YouTube URL.

        Args:
            url: YouTube URL
            output_dir: Directory to save video
            output_filename: Name for the output file (default: "video.mp4")
            use_cache: If True, skip download if file exists (default: True)

        Returns:
            Path to downloaded video file

        Raises:
            ValueError: If download fails
        """
        if not YT_DLP_AVAILABLE:
            raise ValueError("yt-dlp is not installed")

        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        # Check cache
        if use_cache and output_path.exists():
            logger.info(f"✓ Using cached video: {output_path.name}")
            return output_path

        logger.info(f"Downloading video from: {url}")

        # Configure for video download
        output_stem = output_path.stem
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(output_dir / f"{output_stem}.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }

        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                ydl.extract_info(url, download=True)

                # Check if file exists
                if output_path.exists():
                    logger.info(f"Video saved to: {output_path.name}")
                    return output_path

                # Look for various video formats
                for ext in [".mp4", ".webm", ".mkv"]:
                    possible_path = output_dir / f"{output_stem}{ext}"
                    if possible_path.exists():
                        if ext != ".mp4":
                            # Rename to .mp4
                            possible_path.rename(output_path)
                        logger.info(f"Video saved to: {output_path.name}")
                        return output_path

                raise ValueError("Could not find downloaded video file")

        except Exception as e:
            raise ValueError(f"Failed to download video: {e}")

    def capture_screenshot(self, video_path: Path, timestamp: str, output_path: Path) -> Path:
        """Capture screenshot at timestamp using ffmpeg.

        Args:
            video_path: Path to video file
            timestamp: Time in HH:MM:SS format
            output_path: Where to save screenshot

        Returns:
            Path to screenshot file

        Raises:
            ValueError: If screenshot capture fails
        """
        video_path = video_path.expanduser()
        output_path = output_path.expanduser()

        if not video_path.exists():
            raise ValueError(f"Video file not found: {video_path}")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Capturing screenshot at {timestamp} from: {video_path.name}")

        cmd = [
            "ffmpeg",
            "-ss",
            timestamp,
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Screenshot saved to: {output_path.name}")
            return output_path
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to capture screenshot: {e}")
