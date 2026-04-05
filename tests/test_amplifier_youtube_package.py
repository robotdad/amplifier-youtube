"""
Tests for the amplifier_youtube package scaffold (Task 1).

Verifies that the new package:
- Exists and is importable
- Exports VideoInfo, VideoLoader, and AudioExtractor from shared modules
"""


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
        """__all__ must declare all public symbols including all three tools and mount()."""
        import amplifier_youtube

        assert hasattr(amplifier_youtube, "__all__")
        assert set(amplifier_youtube.__all__) == {
            "VideoInfo",
            "VideoLoader",
            "AudioExtractor",
            "YouTubeDownloadTool",
            "YouTubeSearchTool",
            "YouTubeFeedTool",
            "mount",
        }

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

    def test_mount_is_exported(self):
        """mount() must be exported from amplifier_youtube as of Task 5."""
        import amplifier_youtube
        from amplifier_youtube import mount  # noqa: F401

        assert hasattr(amplifier_youtube, "mount"), "mount() must be present in amplifier_youtube after Task 5"

