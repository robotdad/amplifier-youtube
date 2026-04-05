"""Amplifier YouTube Module — download, search, and account feed access."""

from .audio_utils import AudioExtractor
from .core import VideoInfo, VideoLoader

__all__ = ["VideoInfo", "VideoLoader", "AudioExtractor"]
