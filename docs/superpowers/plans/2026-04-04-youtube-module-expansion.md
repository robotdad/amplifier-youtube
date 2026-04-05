# YouTube Module Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `amplifier-module-tool-youtube-dl` into `amplifier-youtube` — a full YouTube capability module with three tools: download (`youtube-dl`), search (`youtube-search`), and account feed access (`youtube-feed`).

**Architecture:** The single-tool module becomes a three-tool module under a new Python package (`amplifier_youtube`). A unified `mount()` entry point registers all three tools with the coordinator. The search tool uses the YouTube Data API v3 when an `api_key` is configured, falling back transparently to yt-dlp for unlimited basic searches. The feed tool uses yt-dlp with Netscape-format cookie authentication to access account data (watch history, subscriptions, liked videos, recommendations, watch later). Existing download functionality is preserved as-is under a renamed class (`YouTubeDownloadTool`).

**Tech Stack:** Python 3.11+, yt-dlp (YouTube downloading and search fallback), google-api-python-client (YouTube Data API v3), amplifier-core (Tool protocol / ToolResult), pytest + pytest-asyncio (testing), hatchling (build backend), UV (package management)

**Spec:** `docs/superpowers/specs/2026-04-04-youtube-module-expansion-design.md`

---

## File Structure

After all tasks are complete, the repo will contain:

```
amplifier-youtube/                           (repo root — GitHub rename separate)
├── src/amplifier_youtube/                   NEW package directory
│   ├── __init__.py                          CREATE — mount() registers all 3 tools
│   ├── download_tool.py                     CREATE — YouTubeDownloadTool (renamed from YouTubeDLTool)
│   ├── search_tool.py                       CREATE — YouTubeSearchTool (new)
│   ├── feed_tool.py                         CREATE — YouTubeFeedTool (new)
│   ├── core.py                              MOVE   — VideoLoader, VideoInfo (unchanged content)
│   └── audio_utils.py                       MOVE   — AudioExtractor (unchanged content)
├── tests/
│   ├── test_download_tool.py                CREATE — migrated from test_youtube_tool.py (16 tests)
│   ├── test_search_tool.py                  CREATE — new (9 tests)
│   ├── test_feed_tool.py                    CREATE — new (11 tests)
│   └── test_mount.py                        CREATE — new (4 tests)
├── behaviors/
│   └── youtube.yaml                         RENAME — was youtube-dl.yaml, updated content
├── context/
│   └── instructions.md                      MODIFY — expanded for 3 tools
├── bundle.md                                MODIFY — updated bundle name and references
├── pyproject.toml                           MODIFY — new package name, deps, entry point
└── README.md                                MODIFY — updated for 3-tool module
```

**Files to DELETE in cleanup (Task 7):**
- `src/amplifier_module_tool_youtube_dl/` (entire old package directory)
- `tests/test_youtube_tool.py` (old test file)
- `behaviors/youtube-dl.yaml` (replaced by `behaviors/youtube.yaml`)

---

## Test Runner Note

After `uv sync` in Task 1, use this command pattern to run tests quickly (avoids repeated dependency resolution):

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/<file> -v --tb=short
```

Or if you prefer the simpler form (slightly slower on first run due to git dependency check):

```bash
uv run pytest tests/<file> -v --tb=short
```

Both are shown interchangeably below. Use whichever you prefer.

---

### Task 1: Scaffold new package and update build configuration

**Files:**
- Create: `src/amplifier_youtube/__init__.py` (minimal — shared exports only)
- Copy: `src/amplifier_youtube/core.py` (from `src/amplifier_module_tool_youtube_dl/core.py`)
- Copy: `src/amplifier_youtube/audio_utils.py` (from `src/amplifier_module_tool_youtube_dl/audio_utils.py`)
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the new package directory and copy shared modules**

```bash
mkdir -p src/amplifier_youtube
cp src/amplifier_module_tool_youtube_dl/core.py src/amplifier_youtube/core.py
cp src/amplifier_module_tool_youtube_dl/audio_utils.py src/amplifier_youtube/audio_utils.py
```

- [ ] **Step 2: Create the minimal `__init__.py`**

Create `src/amplifier_youtube/__init__.py` with only the shared exports (tools and `mount()` are added in later tasks):

```python
"""Amplifier YouTube Module — download, search, and account feed access."""

from .audio_utils import AudioExtractor
from .core import VideoInfo, VideoLoader

__all__ = ["VideoInfo", "VideoLoader", "AudioExtractor"]
```

- [ ] **Step 3: Update `pyproject.toml` to the final state**

Replace the entire contents of `pyproject.toml` with:

```toml
[project]
name = "amplifier-youtube"
version = "0.2.0"
description = "YouTube capability module for Amplifier — download, search, and account feed access"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Microsoft Corporation" }]
dependencies = [
    "yt-dlp>=2024.0.0",
    "google-api-python-client>=2.0.0",
]

[project.entry-points."amplifier.modules"]
"youtube" = "amplifier_youtube:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = true

[tool.hatch.build.targets.wheel]
packages = ["src/amplifier_youtube"]

[tool.hatch.metadata]
allow-direct-references = true

[dependency-groups]
dev = [
    "amplifier-core",
    "pytest>=8.0.0",
    "pytest-asyncio>=1.0.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.1.0",
]

[tool.uv.sources]
amplifier-core = { git = "https://github.com/microsoft/amplifier-core", branch = "main" }

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

- [ ] **Step 4: Sync the virtual environment**

```bash
uv sync
```

Expected: resolves dependencies, installs `google-api-python-client` and the new `amplifier-youtube` package. This may take 30-60 seconds due to the `amplifier-core` git dependency.

- [ ] **Step 5: Verify the new package imports correctly**

```bash
PYTHONPATH=src .venv/bin/python -c "from amplifier_youtube import VideoInfo, VideoLoader, AudioExtractor; print('OK')"
```

Expected output: `OK`

- [ ] **Step 6: Verify old package still imports (for backward compat until cleanup)**

```bash
PYTHONPATH=src .venv/bin/python -c "from amplifier_module_tool_youtube_dl import VideoInfo; print('OK')"
```

Expected output: `OK`

- [ ] **Step 7: Commit scaffold**

```bash
git add src/amplifier_youtube/__init__.py src/amplifier_youtube/core.py src/amplifier_youtube/audio_utils.py pyproject.toml
git commit -m "chore: scaffold amplifier_youtube package with shared modules and updated pyproject.toml"
```

---

### Task 2: Download tool — rename and migrate tests

**Files:**
- Create: `tests/test_download_tool.py`
- Create: `src/amplifier_youtube/download_tool.py`
- Modify: `src/amplifier_youtube/__init__.py`

- [ ] **Step 1: Write the migrated test file**

Create `tests/test_download_tool.py` with the full contents below. This is the existing `test_youtube_tool.py` with three changes: imports updated to `amplifier_youtube`, class renamed from `YouTubeDLTool` to `YouTubeDownloadTool`, and `TestMount` class removed (mount tests move to Task 5):

```python
"""
Tests for YouTubeDownloadTool implementation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplifier_youtube import VideoInfo
from amplifier_youtube.download_tool import YouTubeDownloadTool


@pytest.fixture
def tool_config():
    """Basic tool configuration."""
    return {
        "output_dir": "/tmp/test_downloads",
        "audio_only": True,
    }


@pytest.fixture
def youtube_tool(tool_config):
    """Create YouTubeDownloadTool instance."""
    return YouTubeDownloadTool(tool_config)


@pytest.fixture
def mock_video_info():
    """Mock video information."""
    return VideoInfo(
        source="https://youtube.com/watch?v=test",
        type="url",
        title="Test Video",
        id="test123",
        duration=300.0,
        description="Test description",
        uploader="Test Uploader",
    )


class TestYouTubeDownloadToolInitialization:
    """Test tool initialization."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        tool = YouTubeDownloadTool({})
        assert tool.output_dir == Path.home() / "downloads"
        assert tool.audio_only is True

    def test_init_custom_config(self, tool_config):
        """Test initialization with custom configuration."""
        tool = YouTubeDownloadTool(tool_config)
        assert tool.output_dir == Path("/tmp/test_downloads")
        assert tool.audio_only is True

    def test_name_property(self, youtube_tool):
        """Test tool name property."""
        assert youtube_tool.name == "youtube-dl"

    def test_description_property(self, youtube_tool):
        """Test tool description property."""
        assert "Download audio or video" in youtube_tool.description
        assert "YouTube" in youtube_tool.description


class TestYouTubeDownloadToolAudioDownload:
    """Test audio download functionality."""

    @pytest.mark.asyncio
    async def test_audio_download_success(self, youtube_tool, mock_video_info):
        """Test successful audio download."""
        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_audio", return_value=Path("/tmp/test_downloads/audio.mp3")
            ):
                result = await youtube_tool.execute({"url": "https://youtube.com/watch?v=test"})

                assert result.success is True
                assert result.output["path"] == "/tmp/test_downloads/audio.mp3"
                assert result.output["metadata"]["title"] == "Test Video"

    @pytest.mark.asyncio
    async def test_audio_download_with_custom_filename(self, youtube_tool, mock_video_info):
        """Test audio download with custom filename."""
        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_audio", return_value=Path("/tmp/test_downloads/custom.mp3")
            ) as mock_download:
                await youtube_tool.execute({"url": "https://youtube.com/watch?v=test", "output_filename": "custom.mp3"})

                mock_download.assert_called_once()
                # Check positional args: (url, output_dir, filename, use_cache)
                call_args = mock_download.call_args[0]
                assert call_args[2] == "custom.mp3"  # filename is 3rd positional arg

    @pytest.mark.asyncio
    async def test_audio_download_with_cache(self, youtube_tool, mock_video_info):
        """Test audio download respects cache parameter."""
        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_audio", return_value=Path("/tmp/test_downloads/audio.mp3")
            ) as mock_download:
                await youtube_tool.execute({"url": "https://youtube.com/watch?v=test", "use_cache": False})

                # Check positional args: (url, output_dir, filename, use_cache)
                call_args = mock_download.call_args[0]
                assert call_args[3] is False  # use_cache is 4th positional arg


class TestYouTubeDownloadToolVideoDownload:
    """Test video download functionality."""

    @pytest.mark.asyncio
    async def test_video_download_success(self, youtube_tool, mock_video_info):
        """Test successful video download."""
        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_video", return_value=Path("/tmp/test_downloads/video.mp4")
            ):
                result = await youtube_tool.execute({"url": "https://youtube.com/watch?v=test", "audio_only": False})

                assert result.success is True
                assert result.output["path"] == "/tmp/test_downloads/video.mp4"
                assert result.output["metadata"]["title"] == "Test Video"

    @pytest.mark.asyncio
    async def test_video_download_overrides_config(self, youtube_tool, mock_video_info):
        """Test video download overrides audio_only config."""
        # Tool configured for audio_only=True
        assert youtube_tool.audio_only is True

        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_video", return_value=Path("/tmp/test_downloads/video.mp4")
            ) as mock_video:
                with patch.object(youtube_tool.loader, "download_audio") as mock_audio:
                    await youtube_tool.execute({"url": "https://youtube.com/watch?v=test", "audio_only": False})

                    # Should call download_video, not download_audio
                    mock_video.assert_called_once()
                    mock_audio.assert_not_called()


class TestYouTubeDownloadToolScreenshotCapture:
    """Test screenshot capture functionality."""

    @pytest.mark.asyncio
    async def test_screenshot_capture_success(self, youtube_tool, mock_video_info):
        """Test successful screenshot capture."""
        mock_video_info.video_path = Path("/tmp/test_downloads/video.mp4")

        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_video", return_value=Path("/tmp/test_downloads/video.mp4")
            ):
                with patch.object(
                    youtube_tool.loader, "capture_screenshot", return_value=Path("/tmp/test_downloads/screenshot.jpg")
                ):
                    result = await youtube_tool.execute(
                        {
                            "url": "https://youtube.com/watch?v=test",
                            "audio_only": False,
                            "capture_screenshot": True,
                            "screenshot_time": "00:05:00",
                        }
                    )

                    assert result.success is True
                    assert "screenshot_path" in result.output
                    assert result.output["screenshot_path"] == "/tmp/test_downloads/screenshot.jpg"

    @pytest.mark.asyncio
    async def test_screenshot_without_timestamp_fails(self, youtube_tool, mock_video_info):
        """Test screenshot capture fails without timestamp."""
        result = await youtube_tool.execute({"url": "https://youtube.com/watch?v=test", "capture_screenshot": True})

        assert result.success is False
        assert "screenshot_time required" in result.error["message"]


class TestYouTubeDownloadToolLocalFiles:
    """Test local file handling."""

    @pytest.mark.asyncio
    async def test_local_file_handling(self, youtube_tool):
        """Test handling of local video files."""
        local_video_info = VideoInfo(
            source="/path/to/video.mp4",
            type="file",
            title="local_video",
            id="local_video",
            duration=180.0,
        )

        with patch.object(youtube_tool.loader, "load", return_value=local_video_info):
            result = await youtube_tool.execute({"url": "/path/to/video.mp4"})

            assert result.success is True
            assert result.output["path"] == "/path/to/video.mp4"
            assert result.output["metadata"]["type"] == "file"


class TestYouTubeDownloadToolErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_missing_url_parameter(self, youtube_tool):
        """Test error when URL parameter is missing."""
        result = await youtube_tool.execute({})

        assert result.success is False
        assert "Missing required parameter: url" in result.error["message"]

    @pytest.mark.asyncio
    async def test_download_failure(self, youtube_tool, mock_video_info):
        """Test handling of download failures."""
        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(youtube_tool.loader, "download_audio", side_effect=ValueError("Download failed")):
                result = await youtube_tool.execute({"url": "https://youtube.com/watch?v=test"})

                assert result.success is False
                assert "Download failed" in result.error["message"]
                assert result.error["type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_unexpected_error(self, youtube_tool):
        """Test handling of unexpected errors."""
        with patch.object(youtube_tool.loader, "load", side_effect=RuntimeError("Unexpected error")):
            result = await youtube_tool.execute({"url": "https://youtube.com/watch?v=test"})

            assert result.success is False
            assert "Unexpected error" in result.error["message"]
            assert result.error["type"] == "RuntimeError"


class TestYouTubeDownloadToolMetadata:
    """Test metadata extraction."""

    @pytest.mark.asyncio
    async def test_metadata_extraction(self, youtube_tool, mock_video_info):
        """Test complete metadata is returned."""
        with patch.object(youtube_tool.loader, "load", return_value=mock_video_info):
            with patch.object(
                youtube_tool.loader, "download_audio", return_value=Path("/tmp/test_downloads/audio.mp3")
            ):
                result = await youtube_tool.execute({"url": "https://youtube.com/watch?v=test"})

                metadata = result.output["metadata"]
                assert metadata["source"] == "https://youtube.com/watch?v=test"
                assert metadata["type"] == "url"
                assert metadata["title"] == "Test Video"
                assert metadata["id"] == "test123"
                assert metadata["duration"] == 300.0
                assert metadata["description"] == "Test description"
                assert metadata["uploader"] == "Test Uploader"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_download_tool.py -v --tb=short
```

Expected: FAILED — all 16 tests fail with `ModuleNotFoundError: No module named 'amplifier_youtube.download_tool'`

- [ ] **Step 3: Create the download tool implementation**

Create `src/amplifier_youtube/download_tool.py`:

```python
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
                "audio_only": {"type": "boolean", "description": "Download audio (True) or full video (False). Overrides config."},
                "output_filename": {"type": "string", "description": "Custom output filename"},
                "use_cache": {"type": "boolean", "description": "Use cached file if exists (default: true)"},
                "capture_screenshot": {"type": "boolean", "description": "Extract a screenshot (default: false)"},
                "screenshot_time": {"type": "string", "description": "Timestamp HH:MM:SS (required if capture_screenshot is true)"},
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
                return ToolResult(success=False, error={"message": "screenshot_time required when capture_screenshot is True"})

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
                assert isinstance(screenshot_time, str)
                screenshot_filename = output_filename.replace(".mp4", ".jpg") if output_filename else "screenshot.jpg"
                screenshot_output = self.output_dir / screenshot_filename
                logger.info(f"Capturing screenshot at {screenshot_time}")
                screenshot_path = self.loader.capture_screenshot(downloaded_path, screenshot_time, screenshot_output)

            result_data = {"path": str(downloaded_path), "metadata": asdict(video_info)}
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
```

- [ ] **Step 4: Update `__init__.py` to export `YouTubeDownloadTool`**

Replace `src/amplifier_youtube/__init__.py` with:

```python
"""Amplifier YouTube Module — download, search, and account feed access."""

from .audio_utils import AudioExtractor
from .core import VideoInfo, VideoLoader
from .download_tool import YouTubeDownloadTool

__all__ = ["YouTubeDownloadTool", "VideoInfo", "VideoLoader", "AudioExtractor"]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_download_tool.py -v --tb=short
```

Expected: `16 passed`

- [ ] **Step 6: Commit**

```bash
git add src/amplifier_youtube/download_tool.py src/amplifier_youtube/__init__.py tests/test_download_tool.py
git commit -m "feat: add YouTubeDownloadTool with migrated tests (16 passing)"
```

---

### Task 3: Search tool (TDD)

**Files:**
- Create: `tests/test_search_tool.py`
- Create: `src/amplifier_youtube/search_tool.py`

- [ ] **Step 1: Write the search tool tests**

Create `tests/test_search_tool.py`:

```python
"""Tests for YouTubeSearchTool."""
from unittest.mock import MagicMock, patch
import pytest
from amplifier_youtube.search_tool import YouTubeSearchTool

@pytest.fixture
def tool_no_key():
    return YouTubeSearchTool({})

@pytest.fixture
def tool_with_key():
    return YouTubeSearchTool({"api_key": "fake-key", "max_results": 5})

@pytest.fixture
def mock_ytdlp_results():
    return {
        "entries": [
            {"id": "abc123", "title": "Test Video", "channel": "Test Channel",
             "upload_date": "20250101", "description": "desc", "url": "https://youtube.com/watch?v=abc123",
             "duration": 300},
        ]
    }

class TestYouTubeSearchToolNoApiKey:
    @pytest.mark.asyncio
    async def test_search_uses_ytdlp_without_api_key(self, tool_no_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_ytdlp_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = await tool_no_key.execute({"query": "python tutorial"})
        assert result.success is True
        assert result.output["backend"] == "ytdlp"
        assert len(result.output["results"]) == 1
        assert result.output["results"][0]["id"] == "abc123"

    @pytest.mark.asyncio
    async def test_date_order_uses_ytsearchdate_prefix(self, tool_no_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_ytdlp_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_no_key.execute({"query": "python tutorial", "order": "date"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg.startswith("ytsearchdate")

    @pytest.mark.asyncio
    async def test_relevance_order_uses_ytsearch_prefix(self, tool_no_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_ytdlp_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_no_key.execute({"query": "python tutorial", "order": "relevance"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg.startswith("ytsearch") and not call_arg.startswith("ytsearchdate")

    @pytest.mark.asyncio
    async def test_missing_query_returns_error(self, tool_no_key):
        result = await tool_no_key.execute({})
        assert result.success is False
        assert "query" in result.error["message"]

class TestYouTubeSearchToolWithApiKey:
    @pytest.mark.asyncio
    async def test_search_uses_api_when_key_configured(self, tool_with_key):
        mock_response = {
            "items": [{
                "id": {"videoId": "xyz789"},
                "snippet": {
                    "title": "API Result",
                    "channelTitle": "API Channel",
                    "publishedAt": "2025-01-01T00:00:00Z",
                    "description": "API desc",
                },
            }]
        }
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.return_value = mock_response
            result = await tool_with_key.execute({"query": "python tutorial"})
        assert result.success is True
        assert result.output["backend"] == "api"
        assert result.output["results"][0]["id"] == "xyz789"

    @pytest.mark.asyncio
    async def test_api_failure_falls_back_to_ytdlp(self, tool_with_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_build.side_effect = Exception("quota exceeded")
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                mock_ydl = MagicMock()
                mock_ydl.extract_info.return_value = mock_ytdlp_results
                mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
                mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
                result = await tool_with_key.execute({"query": "python tutorial"})
        assert result.success is True
        assert result.output["backend"] == "ytdlp"

    @pytest.mark.asyncio
    async def test_duration_filter_sent_to_api(self, tool_with_key):
        mock_response = {"items": []}
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.return_value = mock_response
            await tool_with_key.execute({"query": "tutorial", "duration": "short"})
            call_kwargs = mock_youtube.search().list.call_args[1]
        assert call_kwargs.get("videoDuration") == "short"

class TestYouTubeSearchToolSchema:
    def test_name(self):
        assert YouTubeSearchTool({}).name == "youtube-search"

    def test_input_schema_has_required_query(self):
        schema = YouTubeSearchTool({}).input_schema
        assert "query" in schema["required"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_search_tool.py -v --tb=short
```

Expected: FAILED — all tests fail with `ModuleNotFoundError: No module named 'amplifier_youtube.search_tool'`

- [ ] **Step 3: Create the search tool implementation**

Create `src/amplifier_youtube/search_tool.py`:

```python
"""YouTube Search Tool — searches with Data API (rich filters) or yt-dlp fallback."""

import logging
from typing import Any

import yt_dlp
from amplifier_core.models import ToolResult

logger = logging.getLogger(__name__)


def build(*args, **kwargs):
    """Lazy proxy — replaced by googleapiclient.discovery.build on first API call."""
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
                "published_after": {"type": "string", "description": "ISO 8601 date filter (e.g. 2025-01-01T00:00:00Z). Requires API key."},
                "published_before": {"type": "string", "description": "ISO 8601 date filter. Requires API key."},
                "region_code": {"type": "string", "description": "ISO 3166-1 alpha-2 country code (e.g. US). Requires API key."},
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
            results.append({
                "id": video_id,
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "published_at": snippet["publishedAt"][:10],
                "description": snippet.get("description", ""),
                "url": f"https://youtube.com/watch?v={video_id}",
                "duration_seconds": None,
            })

        return ToolResult(success=True, output={"results": results, "backend": "api", "total_results": len(results)})

    async def _search_with_ytdlp(self, input: dict[str, Any], max_results: int) -> ToolResult:
        order = input.get("order", "relevance")
        prefix = "ytsearchdate" if order == "date" else "ytsearch"
        search_query = f"{prefix}{max_results}:{input['query']}"

        ydl_opts = {"quiet": True, "extract_flat": True, "no_warnings": True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        results = []
        for entry in (info.get("entries") or []):
            vid_id = entry.get("id", "")
            results.append({
                "id": vid_id,
                "title": entry.get("title", ""),
                "channel": entry.get("channel", entry.get("uploader", "")),
                "published_at": entry.get("upload_date", ""),
                "description": entry.get("description", ""),
                "url": entry.get("url") or f"https://youtube.com/watch?v={vid_id}",
                "duration_seconds": entry.get("duration"),
            })

        return ToolResult(success=True, output={"results": results, "backend": "ytdlp", "total_results": len(results)})
```

**Note on `build()` function:** The module-level `build()` function acts as a lazy proxy for `googleapiclient.discovery.build`. This allows tests to patch `amplifier_youtube.search_tool.build` cleanly without requiring `google-api-python-client` to be imported at module load time. The real `googleapiclient.discovery.build` is only imported when the function is actually called.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_search_tool.py -v --tb=short
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add src/amplifier_youtube/search_tool.py tests/test_search_tool.py
git commit -m "feat: add YouTubeSearchTool with API + yt-dlp fallback (9 tests passing)"
```

---

### Task 4: Feed tool (TDD)

**Files:**
- Create: `tests/test_feed_tool.py`
- Create: `src/amplifier_youtube/feed_tool.py`

- [ ] **Step 1: Write the feed tool tests**

Create `tests/test_feed_tool.py`:

```python
"""Tests for YouTubeFeedTool."""
from unittest.mock import MagicMock, patch
import pytest
from amplifier_youtube.feed_tool import YouTubeFeedTool

@pytest.fixture
def tool_with_cookies():
    return YouTubeFeedTool({}, cookies_file="~/test-cookies.txt")

@pytest.fixture
def tool_no_cookies():
    return YouTubeFeedTool({})

@pytest.fixture
def mock_feed_results():
    return {
        "entries": [
            {"id": "vid001", "title": "History Video 1", "channel": "Ch1",
             "url": "https://youtube.com/watch?v=vid001", "upload_date": "20250101", "duration": 300},
            {"id": "vid002", "title": "History Video 2", "channel": "Ch2",
             "url": "https://youtube.com/watch?v=vid002", "upload_date": "20250102", "duration": 600},
        ]
    }

class TestYouTubeFeedToolNoCookies:
    @pytest.mark.asyncio
    async def test_returns_error_without_cookies(self, tool_no_cookies):
        result = await tool_no_cookies.execute({"feed_type": "history"})
        assert result.success is False
        assert "cookies_file" in result.error["message"]

class TestYouTubeFeedToolFeedTypes:
    @pytest.mark.asyncio
    async def test_history_uses_correct_target(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_with_cookies.execute({"feed_type": "history"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == ":ythistory"

    @pytest.mark.asyncio
    async def test_subscriptions_uses_correct_target(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_with_cookies.execute({"feed_type": "subscriptions"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == ":ytsubs"

    @pytest.mark.asyncio
    async def test_liked_uses_correct_target(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_with_cookies.execute({"feed_type": "liked"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == ":ytfav"

    @pytest.mark.asyncio
    async def test_recommendations_uses_correct_target(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_with_cookies.execute({"feed_type": "recommendations"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == ":ytrec"

    @pytest.mark.asyncio
    async def test_watch_later_uses_correct_target(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_with_cookies.execute({"feed_type": "watch_later"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg == ":ytwatchlater"

class TestYouTubeFeedToolResults:
    @pytest.mark.asyncio
    async def test_returns_correct_schema(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = await tool_with_cookies.execute({"feed_type": "history", "limit": 10})
        assert result.success is True
        assert result.output["feed_type"] == "history"
        assert result.output["count"] == 2
        item = result.output["items"][0]
        assert all(k in item for k in ("id", "title", "channel", "url", "upload_date", "duration_seconds"))

    @pytest.mark.asyncio
    async def test_limit_passed_as_playlistend(self, tool_with_cookies, mock_feed_results):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.return_value = mock_feed_results
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            await tool_with_cookies.execute({"feed_type": "history", "limit": 25})
            ydl_opts = mock_ydl_cls.call_args[0][0]
        assert ydl_opts["playlistend"] == 25

    @pytest.mark.asyncio
    async def test_expired_cookies_returns_hint(self, tool_with_cookies):
        with patch("amplifier_youtube.feed_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.side_effect = Exception("Sign in to confirm your age")
            mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = await tool_with_cookies.execute({"feed_type": "history"})
        assert result.success is False
        assert "hint" in result.error

class TestYouTubeFeedToolSchema:
    def test_name(self):
        assert YouTubeFeedTool({}).name == "youtube-feed"

    def test_input_schema_has_required_feed_type(self):
        schema = YouTubeFeedTool({}).input_schema
        assert "feed_type" in schema["required"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_feed_tool.py -v --tb=short
```

Expected: FAILED — all tests fail with `ModuleNotFoundError: No module named 'amplifier_youtube.feed_tool'`

- [ ] **Step 3: Create the feed tool implementation**

Create `src/amplifier_youtube/feed_tool.py`:

```python
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
    def input_schema(self) -> dict:
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

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(yt_target, download=False)

            items = []
            for entry in (info.get("entries") or []):
                vid_id = entry.get("id", "")
                items.append({
                    "id": vid_id,
                    "title": entry.get("title", ""),
                    "channel": entry.get("channel", entry.get("uploader", "")),
                    "url": entry.get("url") or f"https://youtube.com/watch?v={vid_id}",
                    "upload_date": entry.get("upload_date", ""),
                    "duration_seconds": entry.get("duration"),
                })

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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_feed_tool.py -v --tb=short
```

Expected: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add src/amplifier_youtube/feed_tool.py tests/test_feed_tool.py
git commit -m "feat: add YouTubeFeedTool with cookie-based account feed access (11 tests passing)"
```

---

### Task 5: Mount entry point — register all three tools

**Files:**
- Create: `tests/test_mount.py`
- Modify: `src/amplifier_youtube/__init__.py`

- [ ] **Step 1: Write the mount tests**

Create `tests/test_mount.py`:

```python
"""Tests for the mount() entry point registering all three tools."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from amplifier_youtube import mount

class TestMount:
    @pytest.mark.asyncio
    async def test_mount_registers_three_tools(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        result = await mount(coordinator)
        assert coordinator.mount.call_count == 3
        names = {call[1]["name"] for call in coordinator.mount.call_args_list}
        assert names == {"youtube-dl", "youtube-search", "youtube-feed"}
        assert set(result["provides"]) == {"youtube-dl", "youtube-search", "youtube-feed"}

    @pytest.mark.asyncio
    async def test_mount_distributes_search_config(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        await mount(coordinator, {"search": {"api_key": "test-key", "max_results": 25}})
        search_tool = next(c[0][1] for c in coordinator.mount.call_args_list if c[1]["name"] == "youtube-search")
        assert search_tool.api_key == "test-key"
        assert search_tool.default_max_results == 25

    @pytest.mark.asyncio
    async def test_mount_passes_cookies_to_feed_tool(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        await mount(coordinator, {"cookies_file": "~/cookies.txt"})
        feed_tool = next(c[0][1] for c in coordinator.mount.call_args_list if c[1]["name"] == "youtube-feed")
        assert feed_tool.cookies_file == "~/cookies.txt"

    @pytest.mark.asyncio
    async def test_mount_returns_correct_manifest(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        result = await mount(coordinator)
        assert result["name"] == "youtube"
        assert result["version"] == "0.2.0"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_mount.py -v --tb=short
```

Expected: FAILED — `ImportError: cannot import name 'mount' from 'amplifier_youtube'` (because the current `__init__.py` doesn't define `mount`)

- [ ] **Step 3: Update `__init__.py` to the final version with `mount()`**

Replace `src/amplifier_youtube/__init__.py` with the complete final version:

```python
"""Amplifier YouTube Module — download, search, and account feed access."""

import logging
from typing import Any

from .audio_utils import AudioExtractor
from .core import VideoInfo, VideoLoader
from .download_tool import YouTubeDownloadTool
from .feed_tool import YouTubeFeedTool
from .search_tool import YouTubeSearchTool

logger = logging.getLogger(__name__)

__all__ = ["YouTubeDownloadTool", "YouTubeSearchTool", "YouTubeFeedTool", "VideoInfo", "VideoLoader", "AudioExtractor", "mount"]


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
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
    return {
        "name": "youtube",
        "version": "0.2.0",
        "provides": ["youtube-dl", "youtube-search", "youtube-feed"],
    }
```

- [ ] **Step 4: Run the mount tests to verify they pass**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_mount.py -v --tb=short
```

Expected: `4 passed`

- [ ] **Step 5: Run all new tests together to verify nothing broke**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_download_tool.py tests/test_search_tool.py tests/test_feed_tool.py tests/test_mount.py -v --tb=short
```

Expected: `40 passed` (16 + 9 + 11 + 4)

- [ ] **Step 6: Commit**

```bash
git add src/amplifier_youtube/__init__.py tests/test_mount.py
git commit -m "feat: add mount() entry point registering all three YouTube tools (40 tests passing)"
```

---

### Task 6: Bundle, behavior, context, and README updates

**Files:**
- Rename: `behaviors/youtube-dl.yaml` → `behaviors/youtube.yaml`
- Modify: `behaviors/youtube.yaml` (new content)
- Modify: `bundle.md`
- Modify: `context/instructions.md`
- Modify: `README.md`

- [ ] **Step 1: Rename and update the behavior file**

```bash
git mv behaviors/youtube-dl.yaml behaviors/youtube.yaml
```

Then replace `behaviors/youtube.yaml` with:

```yaml
bundle:
  name: youtube-behavior
  version: 2.0.0
  description: Adds YouTube download, search, and account feed capabilities to any Amplifier session

tools:
  - module: youtube
    source: git+https://github.com/microsoft/amplifier-youtube@main
    config:
      output_dir: ~/downloads
      audio_only: true
      # cookies_file: ~/yt-cookies.txt  # uncomment for account feed access
      search:
        # api_key: AIza...  # uncomment for rich search filters
        max_results: 10

context:
  include:
    - youtube:context/instructions.md
```

- [ ] **Step 2: Update `bundle.md`**

Replace the entire contents of `bundle.md` with:

```markdown
---
bundle:
  name: youtube
  version: 2.0.0
  description: YouTube assistant — download audio/video, search with rich filters, and access account feeds

includes:
  - bundle: youtube:behaviors/youtube
---

# YouTube Assistant

@youtube:context/instructions.md
```

- [ ] **Step 3: Update `context/instructions.md`**

Replace the entire contents of `context/instructions.md` with:

```markdown
# YouTube Tools

You have access to three YouTube tools.

## youtube-dl — Download

Download audio or video from YouTube URLs or local video files.

**Parameters:**
- `url` (required): YouTube URL or local file path
- `audio_only` (optional): `true` for MP3 audio (default), `false` for MP4 video
- `output_filename` (optional): Custom output filename
- `use_cache` (optional): Skip re-download if file exists (default: `true`)
- `capture_screenshot` (optional): Extract a still frame (default: `false`)
- `screenshot_time` (optional): Timestamp `HH:MM:SS` — required when `capture_screenshot: true`

## youtube-search — Search

Search YouTube for videos. Returns a list of results with URLs that can be passed to `youtube-dl`.

**Parameters:**
- `query` (required): Search terms
- `max_results` (optional): Number of results, default 10, max 50
- `order` (optional): `relevance` (default) | `date` | `viewCount` | `rating`
- `duration` (optional): `any` | `short` (<4 min) | `medium` (4–20 min) | `long` (>20 min) — *API key required*
- `published_after` / `published_before` (optional): ISO 8601 date range — *API key required*
- `region_code` (optional): ISO 3166-1 alpha-2 country code — *API key required*
- `hd_only` (optional): Filter for HD content — *API key required*

The response includes a `backend` field (`"api"` or `"ytdlp"`) indicating which search engine was used.
Filters marked *API key required* are silently ignored when no API key is configured.

## youtube-feed — Account Data

Access your YouTube account feeds. **Requires `cookies_file` to be configured.**

**Parameters:**
- `feed_type` (required): `history` | `subscriptions` | `liked` | `recommendations` | `watch_later`
- `limit` (optional): Max items to return (default: 50)

Returns metadata only (id, title, channel, url, upload_date, duration_seconds).
Pass `url` values to `youtube-dl` to download items.

**Cookies setup:** Export your browser cookies to a Netscape-format file (use a browser extension
like "Get cookies.txt LOCALLY") and set `cookies_file: ~/path/to/cookies.txt` in your bundle config.
Cookies may expire — re-export if you see authentication errors.
```

- [ ] **Step 4: Update `README.md`**

Replace the entire contents of `README.md` with:

```markdown
# Amplifier YouTube Module

YouTube capability module for Amplifier — download audio/video, search with rich filters, and access account feeds.

## Tools

### youtube-dl — Download
- **YouTube audio/video download** — Extract audio or download full video
- **Screenshot capture** — Capture frames at specific timestamps
- **Metadata extraction** — Get title, duration, description, uploader
- **Local file support** — Also handles local audio/video files
- **Smart caching** — Avoid re-downloading the same content

### youtube-search — Search
- **Rich filters** — Duration, date range, region, HD (with API key)
- **Dual backend** — YouTube Data API v3 with yt-dlp fallback
- **Zero-config** — Works without API key using yt-dlp search

### youtube-feed — Account Data
- **Watch history, subscriptions, liked videos, recommendations, watch later**
- **Cookie-based auth** — Uses browser cookies via yt-dlp
- **Metadata only** — Returns URLs for piping to youtube-dl

## Prerequisites

- **Python 3.11+**
- **[UV](https://github.com/astral-sh/uv)** — Fast Python package manager
- **ffmpeg** — Required for audio extraction and conversion

### Installing UV

```bash
# macOS/Linux/WSL
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installing ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Installation

```bash
uv pip install -e .
```

## Usage

### As an Amplifier Bundle (ad-hoc use)

```bash
amplifier run --bundle git+https://github.com/microsoft/amplifier-youtube@main \
  "Download audio from https://youtube.com/watch?v=..."
```

### Adding to Your Own Bundle

Include the `youtube` behavior in your bundle to add all three tools:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-youtube@main#behaviors/youtube.yaml
```

### Programmatic Use

```python
from amplifier_youtube import YouTubeDownloadTool, YouTubeSearchTool, YouTubeFeedTool

# Download audio from YouTube
dl_tool = YouTubeDownloadTool({"output_dir": "~/downloads", "audio_only": True})
result = await dl_tool.execute({
    "url": "https://youtube.com/watch?v=...",
    "output_filename": "audio.mp3",
})

# Search YouTube
search_tool = YouTubeSearchTool({"api_key": "AIza..."})  # api_key optional
result = await search_tool.execute({
    "query": "python tutorial",
    "max_results": 5,
    "order": "relevance",
})

# Access account feed (requires cookies)
feed_tool = YouTubeFeedTool({}, cookies_file="~/yt-cookies.txt")
result = await feed_tool.execute({
    "feed_type": "history",
    "limit": 20,
})
```

### In a Mount Plan

```yaml
tools:
  - module: youtube
    source: git+https://github.com/microsoft/amplifier-youtube@main
    config:
      output_dir: ~/downloads
      audio_only: true
      cookies_file: ~/yt-cookies.txt    # optional — for feed access
      search:
        api_key: AIza...                 # optional — enables rich filters
        max_results: 10
        safe_search: true
```

## Configuration

### Top-Level Config

| Key | Used By | Default | Description |
|-----|---------|---------|-------------|
| `output_dir` | youtube-dl | `~/downloads` | Where to save downloads |
| `audio_only` | youtube-dl | `true` | Extract audio only by default |
| `cookies_file` | youtube-dl, youtube-feed | — | Path to Netscape-format cookies file |

### Search Config (`search:` sub-key)

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | — | YouTube Data API v3 key (enables rich filters) |
| `max_results` | `10` | Default results per search |
| `safe_search` | `true` | Enable safe search filtering |

### Cookies Setup (for youtube-feed)

Export your browser cookies to a Netscape-format file (use a browser extension like
"Get cookies.txt LOCALLY") and set `cookies_file` in your config. Cookies may expire —
re-export if you see authentication errors.

## Migration from v0.1.0 (amplifier-module-tool-youtube-dl)

This is a **breaking change**. Update your configs:

1. `module: tool-youtube-dl` → `module: youtube`
2. Update source URLs: `amplifier-module-tool-youtube-dl` → `amplifier-youtube`
3. `cookies_file` is now at the top level of module config (shared across tools)

## Dependencies

- `yt-dlp>=2024.0.0` — YouTube download and search engine
- `google-api-python-client>=2.0.0` — YouTube Data API v3 (rich search filters)
- **ffmpeg** (external) — Audio extraction and conversion

> **Note:** `amplifier-core` is a peer dependency provided by the Amplifier runtime — it is not
> listed as a Python package dependency of this module.

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
```

- [ ] **Step 5: Commit all documentation updates**

```bash
git add behaviors/youtube.yaml bundle.md context/instructions.md README.md
git commit -m "docs: update bundle, behavior, context, and README for three-tool youtube module"
```

---

### Task 7: Cleanup old package and final verification

**Files:**
- Delete: `src/amplifier_module_tool_youtube_dl/` (entire directory)
- Delete: `tests/test_youtube_tool.py`

- [ ] **Step 1: Delete the old package directory**

```bash
git rm -r src/amplifier_module_tool_youtube_dl/
```

- [ ] **Step 2: Delete the old test file**

```bash
git rm tests/test_youtube_tool.py
```

- [ ] **Step 3: Run the full new test suite**

Run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -v --tb=short
```

Expected: `40 passed` across 4 test files:
- `tests/test_download_tool.py` — 16 passed
- `tests/test_search_tool.py` — 9 passed
- `tests/test_feed_tool.py` — 11 passed
- `tests/test_mount.py` — 4 passed

- [ ] **Step 4: Verify the package imports cleanly**

```bash
PYTHONPATH=src .venv/bin/python -c "
from amplifier_youtube import (
    YouTubeDownloadTool, YouTubeSearchTool, YouTubeFeedTool,
    VideoInfo, VideoLoader, AudioExtractor, mount
)
print(f'Exports OK: {len([YouTubeDownloadTool, YouTubeSearchTool, YouTubeFeedTool, VideoInfo, VideoLoader, AudioExtractor, mount])} symbols')
"
```

Expected: `Exports OK: 7 symbols`

- [ ] **Step 5: Verify old package is gone**

```bash
PYTHONPATH=src .venv/bin/python -c "import amplifier_module_tool_youtube_dl" 2>&1 || echo "Old package removed (expected)"
```

Expected: `ModuleNotFoundError` followed by `Old package removed (expected)`

- [ ] **Step 6: Commit cleanup**

```bash
git add -A
git commit -m "chore: remove old amplifier_module_tool_youtube_dl package and legacy test file"
```

- [ ] **Step 7: Verify clean git status**

```bash
git status
git log --oneline -7
```

Expected: clean working tree with 7 commits (one per task):
```
chore: remove old amplifier_module_tool_youtube_dl package and legacy test file
docs: update bundle, behavior, context, and README for three-tool youtube module
feat: add mount() entry point registering all three YouTube tools (40 tests passing)
feat: add YouTubeFeedTool with cookie-based account feed access (11 tests passing)
feat: add YouTubeSearchTool with API + yt-dlp fallback (9 tests passing)
feat: add YouTubeDownloadTool with migrated tests (16 passing)
chore: scaffold amplifier_youtube package with shared modules and updated pyproject.toml
```

---

## Self-Review

### 1. Spec Coverage

| Spec Requirement | Task |
|-----------------|------|
| Repo/package rename (`amplifier_youtube`) | Task 1 (pyproject.toml + package dir) |
| Entry point key change (`youtube`) | Task 1 (pyproject.toml) |
| `YouTubeDownloadTool` (renamed, functionally unchanged) | Task 2 |
| `YouTubeSearchTool` with API + yt-dlp fallback | Task 3 |
| `YouTubeFeedTool` with cookies auth | Task 4 |
| `mount()` registers all 3 tools | Task 5 |
| Config distribution (search sub-key, shared cookies_file) | Task 5 (mount tests verify) |
| `google-api-python-client` dependency | Task 1 (pyproject.toml) |
| Bundle name → `youtube` | Task 6 |
| Behavior file rename → `youtube.yaml` | Task 6 |
| Context instructions for 3 tools | Task 6 |
| Breaking change documented | Task 6 (README migration section) |
| Old package removed | Task 7 |
| 5 feed types (history, subscriptions, liked, recommendations, watch_later) | Task 4 (tested individually) |
| API-only filters silently ignored in yt-dlp mode | Task 3 (by design — yt-dlp path ignores those params) |
| `backend` field in search response | Task 3 (tested in both API and yt-dlp paths) |

No gaps found.

### 2. Placeholder Scan

Scanned all task steps for: "TBD", "TODO", "implement later", "fill in details", "add appropriate", "similar to Task N", "write tests for the above". **None found.** Every step contains complete, executable code or commands.

### 3. Type Consistency

| Symbol | Defined in | Used in | Consistent? |
|--------|-----------|---------|-------------|
| `YouTubeDownloadTool` | Task 2 (download_tool.py) | Task 2 (tests), Task 5 (__init__.py, mount) | Yes |
| `YouTubeSearchTool` | Task 3 (search_tool.py) | Task 3 (tests), Task 5 (__init__.py, mount) | Yes |
| `YouTubeFeedTool` | Task 4 (feed_tool.py) | Task 4 (tests), Task 5 (__init__.py, mount) | Yes |
| `mount()` signature | Task 5 (`coordinator: Any, config: dict | None`) | Task 5 (tests use `MagicMock()` + optional dict) | Yes |
| `ToolResult` | amplifier_core.models | All 3 tools return it, tests assert `.success` and `.output`/`.error` | Yes |
| `VideoInfo` | core.py (dataclass) | Task 2 tests import from `amplifier_youtube` | Yes |
| `self.api_key` | Task 3 (`__init__` reads `config.get("api_key")`) | Task 5 mount test asserts `search_tool.api_key` | Yes |
| `self.default_max_results` | Task 3 (`config.get("max_results", 10)`) | Task 5 mount test asserts `search_tool.default_max_results` | Yes |
| `self.cookies_file` | Task 4 (`cookies_file or config.get("cookies_file")`) | Task 5 mount test asserts `feed_tool.cookies_file` | Yes |
| `.name` property | All 3 tools define it | mount() uses `tool.name` in `coordinator.mount()` call | Yes |

No inconsistencies found.
