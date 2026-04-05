"""
Tests for the amplifier_youtube package scaffold (Task 1).

Verifies that the new package:
- Exists and is importable
- Exports VideoInfo, VideoLoader, and AudioExtractor from shared modules
- Maintains backward compatibility in the old amplifier_module_tool_youtube_dl package
"""

import importlib.util

import pytest


class TestAmplifierYoutubePackageImports:
    """Test that amplifier_youtube package exports the correct shared symbols."""

    def test_package_is_importable(self):
        """The amplifier_youtube package must be importable."""
        import amplifier_youtube  # noqa: F401

    def test_video_info_is_exported(self):
        """VideoInfo must be importable from amplifier_youtube."""
        from amplifier_youtube import VideoInfo  # noqa: F401

    def test_video_loader_is_exported(self):
        """VideoLoader must be importable from amplifier_youtube."""
        from amplifier_youtube import VideoLoader  # noqa: F401

    def test_audio_extractor_is_exported(self):
        """AudioExtractor must be importable from amplifier_youtube."""
        from amplifier_youtube import AudioExtractor  # noqa: F401

    def test_all_contains_expected_symbols(self):
        """__all__ must declare exactly VideoInfo, VideoLoader, AudioExtractor, YouTubeDownloadTool."""
        import amplifier_youtube

        assert hasattr(amplifier_youtube, "__all__")
        assert set(amplifier_youtube.__all__) == {"VideoInfo", "VideoLoader", "AudioExtractor", "YouTubeDownloadTool", "YouTubeSearchTool"}

    def test_video_info_is_dataclass(self):
        """VideoInfo exported from amplifier_youtube should be usable as a dataclass."""
        from amplifier_youtube import VideoInfo

        info = VideoInfo(
            source="https://youtube.com/watch?v=test",
            type="url",
            title="Test",
            id="testid",
            duration=120.0,
        )
        assert info.title == "Test"
        assert info.duration == 120.0

    def test_video_loader_is_instantiable(self):
        """VideoLoader exported from amplifier_youtube should be directly instantiable."""
        from amplifier_youtube import VideoLoader

        loader = VideoLoader()
        assert loader is not None

    def test_audio_extractor_is_instantiable(self, tmp_path):
        """AudioExtractor exported from amplifier_youtube should be directly instantiable."""
        from amplifier_youtube import AudioExtractor

        extractor = AudioExtractor(temp_dir=tmp_path)
        assert extractor is not None

    def test_mount_is_not_exported(self):
        """mount() is added in a later task — must NOT be in amplifier_youtube yet."""
        import amplifier_youtube

        assert not hasattr(amplifier_youtube, "mount"), "mount() should not be in amplifier_youtube until Task 3+"


_amplifier_core_available = importlib.util.find_spec("amplifier_core") is not None


@pytest.mark.skipif(not _amplifier_core_available, reason="amplifier_core not installed (requires uv sync with network)")
class TestBackwardCompatibility:
    """Ensure the old amplifier_module_tool_youtube_dl package still works."""

    def test_old_package_video_info_importable(self):
        """VideoInfo must still be importable from the old package."""
        from amplifier_module_tool_youtube_dl import VideoInfo  # noqa: F401

    def test_old_package_youtube_dl_tool_importable(self):
        """YouTubeDLTool must still be importable from the old package."""
        from amplifier_module_tool_youtube_dl import YouTubeDLTool  # noqa: F401

    def test_old_package_mount_importable(self):
        """mount() must still be importable from the old package."""
        from amplifier_module_tool_youtube_dl import mount  # noqa: F401
