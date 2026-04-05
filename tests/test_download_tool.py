"""
Tests for YouTubeDownloadTool implementation.
"""

from pathlib import Path
from unittest.mock import patch

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
