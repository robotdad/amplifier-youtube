"""
Tests for YouTubeDLTool implementation.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifier_module_tool_youtube_dl import VideoInfo, YouTubeDLTool, mount


@pytest.fixture
def tool_config():
    """Basic tool configuration."""
    return {
        "output_dir": "/tmp/test_downloads",
        "audio_only": True,
    }


@pytest.fixture
def youtube_tool(tool_config):
    """Create YouTubeDLTool instance."""
    return YouTubeDLTool(tool_config)


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


class TestYouTubeDLToolInitialization:
    """Test tool initialization."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        tool = YouTubeDLTool({})
        assert tool.output_dir == Path.home() / "downloads"
        assert tool.audio_only is True

    def test_init_custom_config(self, tool_config):
        """Test initialization with custom configuration."""
        tool = YouTubeDLTool(tool_config)
        assert tool.output_dir == Path("/tmp/test_downloads")
        assert tool.audio_only is True

    def test_name_property(self, youtube_tool):
        """Test tool name property."""
        assert youtube_tool.name == "youtube-dl"

    def test_description_property(self, youtube_tool):
        """Test tool description property."""
        assert "Download audio or video" in youtube_tool.description
        assert "YouTube" in youtube_tool.description


class TestYouTubeDLToolAudioDownload:
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


class TestYouTubeDLToolVideoDownload:
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


class TestYouTubeDLToolScreenshotCapture:
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


class TestYouTubeDLToolLocalFiles:
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


class TestYouTubeDLToolErrorHandling:
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


class TestMount:
    """Test module mount() entry point."""

    @pytest.mark.asyncio
    async def test_mount_registers_tool(self):
        """Test that mount() registers the tool with the coordinator."""
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()

        result = await mount(coordinator)

        # Verify coordinator.mount was called with the tool
        coordinator.mount.assert_called_once()
        call_args = coordinator.mount.call_args
        assert call_args[0][0] == "tools"  # first positional arg is "tools"

        # Verify the manifest returned
        assert result is not None
        assert result["name"] == "tool-youtube-dl"
        assert "youtube-dl" in result["provides"]

    @pytest.mark.asyncio
    async def test_mount_with_config(self):
        """Test that mount() passes config to YouTubeDLTool."""
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()

        config = {"output_dir": "/tmp/test", "audio_only": False}
        result = await mount(coordinator, config)

        assert result is not None
        # Retrieve the tool instance that was passed to coordinator.mount
        tool = coordinator.mount.call_args[0][1]
        assert tool.output_dir.as_posix() == "/tmp/test"
        assert tool.audio_only is False

    @pytest.mark.asyncio
    async def test_mount_without_config_uses_defaults(self):
        """Test that mount() works with no config (uses defaults)."""
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()

        result = await mount(coordinator, None)

        assert result is not None
        tool = coordinator.mount.call_args[0][1]
        assert tool.audio_only is True  # default


class TestYouTubeDLToolMetadata:
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
