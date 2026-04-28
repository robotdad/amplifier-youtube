"""
Tests for TranscriptFetcher and vtt_to_text.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from amplifier_youtube.transcript import TranscriptFetcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vtt(tmp_path: Path, name: str, content: str) -> Path:
    """Write a .vtt file into *tmp_path* and return its Path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _mock_ydl_cm(extract_info_side_effect=None, extract_info_return_value=None):
    """Return a mock that acts as a yt_dlp.YoutubeDL context manager."""
    mock_instance = MagicMock()
    if extract_info_side_effect is not None:
        mock_instance.extract_info.side_effect = extract_info_side_effect
    else:
        mock_instance.extract_info.return_value = extract_info_return_value

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_instance)
    mock_cm.__exit__ = MagicMock(return_value=False)

    mock_class = MagicMock(return_value=mock_cm)
    return mock_class, mock_instance


# ---------------------------------------------------------------------------
# vtt_to_text — pure-function unit tests
# ---------------------------------------------------------------------------


class TestVttToText:
    """Tests for TranscriptFetcher.vtt_to_text()."""

    def test_basic_timestamps_and_tags_stripped(self, tmp_path: Path):
        """Timestamps and inline tags are removed; clean text is returned."""
        vtt = _make_vtt(
            tmp_path,
            "sub.vtt",
            (
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:03.000\n"
                "<c>Hello</c> <b>world</b>\n\n"
                "00:00:04.000 --> 00:00:06.000\n"
                "This is a test\n"
            ),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "Hello world\nThis is a test"

    def test_duplicate_lines_deduplicated(self, tmp_path: Path):
        """Consecutive identical lines (auto-caption rolling) collapse to one."""
        vtt = _make_vtt(
            tmp_path,
            "dup.vtt",
            (
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:02.000\n"
                "Hello world\n\n"
                "00:00:02.000 --> 00:00:03.000\n"
                "Hello world\n\n"
                "00:00:03.000 --> 00:00:04.000\n"
                "Hello world next line\n"
            ),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "Hello world\nHello world next line"

    def test_non_consecutive_duplicates_preserved(self, tmp_path: Path):
        """Non-consecutive duplicate lines are NOT collapsed."""
        vtt = _make_vtt(
            tmp_path,
            "nc_dup.vtt",
            (
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:02.000\n"
                "Apple\n\n"
                "00:00:02.000 --> 00:00:03.000\n"
                "Banana\n\n"
                "00:00:03.000 --> 00:00:04.000\n"
                "Apple\n"
            ),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "Apple\nBanana\nApple"

    def test_cue_ids_not_included(self, tmp_path: Path):
        """Numeric cue IDs that precede timestamp lines are discarded."""
        vtt = _make_vtt(
            tmp_path,
            "cue_ids.vtt",
            (
                "WEBVTT\n\n"
                "1\n"
                "00:00:00.000 --> 00:00:02.000\n"
                "First line\n\n"
                "2\n"
                "00:00:02.000 --> 00:00:04.000\n"
                "Second line\n"
            ),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "First line\nSecond line"

    def test_note_blocks_skipped(self, tmp_path: Path):
        """NOTE metadata blocks are silently skipped."""
        vtt = _make_vtt(
            tmp_path,
            "note.vtt",
            (
                "WEBVTT\n\n"
                "NOTE This is a comment\n"
                "Second line of note\n\n"
                "00:00:00.000 --> 00:00:02.000\n"
                "Actual caption\n"
            ),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "Actual caption"

    def test_style_and_region_blocks_skipped(self, tmp_path: Path):
        """STYLE and REGION blocks are silently skipped."""
        vtt = _make_vtt(
            tmp_path,
            "style.vtt",
            (
                "WEBVTT\n\n"
                "STYLE\n"
                "::cue { color: white; }\n\n"
                "REGION\n"
                "id:r1\n\n"
                "00:00:00.000 --> 00:00:02.000\n"
                "Styled caption\n"
            ),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "Styled caption"

    def test_html_entities_decoded(self, tmp_path: Path):
        """HTML entities are decoded to their Unicode equivalents."""
        vtt = _make_vtt(
            tmp_path,
            "entities.vtt",
            ("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nA &amp; B &lt;tag&gt; &nbsp;space\n"),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert "&amp;" not in result
        assert "A & B" in result
        assert "<tag>" in result

    def test_empty_file_returns_empty_string(self, tmp_path: Path):
        """An empty .vtt file yields an empty string."""
        vtt = _make_vtt(tmp_path, "empty.vtt", "")
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == ""

    def test_header_only_returns_empty_string(self, tmp_path: Path):
        """A file with only the WEBVTT header line yields an empty string."""
        vtt = _make_vtt(tmp_path, "header_only.vtt", "WEBVTT\n\n")
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == ""

    def test_webvtt_header_with_metadata_skipped(self, tmp_path: Path):
        """WEBVTT header blocks carrying extra metadata lines are fully skipped."""
        vtt = _make_vtt(
            tmp_path,
            "meta.vtt",
            ("WEBVTT\nKind: captions\nLanguage: en\n\n00:00:00.000 --> 00:00:02.000\nCaption text\n"),
        )
        result = TranscriptFetcher.vtt_to_text(vtt)
        assert result == "Caption text"


# ---------------------------------------------------------------------------
# TranscriptFetcher.fetch() — integration tests (yt-dlp mocked)
# ---------------------------------------------------------------------------

FAKE_URL = "https://www.youtube.com/watch?v=fakeXYZ"

MOCK_INFO_BOTH = {
    "subtitles": {"en": [{"ext": "vtt", "url": "https://example.com/en.vtt"}]},
    "automatic_captions": {"en": [{"ext": "vtt", "url": "https://example.com/auto.en.vtt"}]},
}

MOCK_INFO_AUTO_ONLY = {
    "subtitles": {},
    "automatic_captions": {"en": [{"ext": "vtt", "url": "https://example.com/auto.en.vtt"}]},
}

MOCK_INFO_NO_EN = {
    "subtitles": {"fr": [{"ext": "vtt", "url": "https://example.com/fr.vtt"}]},
    "automatic_captions": {"fr": [{"ext": "vtt", "url": "https://example.com/auto.fr.vtt"}]},
}

_SAMPLE_VTT = "WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nHello from yt-dlp\n"


class TestTranscriptFetcherPicksManualOverAuto:
    """fetch() prefers manual subtitles when prefer_manual=True (default)."""

    def test_picks_manual_when_both_present(self, tmp_path: Path):
        fetcher = TranscriptFetcher()

        def fake_extract_info(url, download=False):
            if not download:
                return MOCK_INFO_BOTH
            # Simulate yt-dlp writing the subtitle file.
            (tmp_path / "video.en.vtt").write_text(_SAMPLE_VTT, encoding="utf-8")
            return None

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = fake_extract_info
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video")

        assert result.available is True
        assert result.source == "manual"
        assert result.language == "en"
        assert result.text == "Hello from yt-dlp"

        # Verify that the download call used writesubtitles=True, writeautomaticsub=False.
        download_call_kwargs = mock_class.call_args_list[1][0][0]  # second YoutubeDL() call
        assert download_call_kwargs.get("writesubtitles") is True
        assert download_call_kwargs.get("writeautomaticsub") is False

    def test_picks_auto_when_no_manual(self, tmp_path: Path):
        fetcher = TranscriptFetcher()

        def fake_extract_info(url, download=False):
            if not download:
                return MOCK_INFO_AUTO_ONLY
            (tmp_path / "video.en.vtt").write_text(_SAMPLE_VTT, encoding="utf-8")
            return None

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = fake_extract_info
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video")

        assert result.available is True
        assert result.source == "auto"
        assert result.language == "en"

        download_call_kwargs = mock_class.call_args_list[1][0][0]
        assert download_call_kwargs.get("writesubtitles") is False
        assert download_call_kwargs.get("writeautomaticsub") is True

    def test_prefer_auto_when_prefer_manual_false(self, tmp_path: Path):
        """When prefer_manual=False, auto-captions take priority over manual."""
        fetcher = TranscriptFetcher()

        def fake_extract_info(url, download=False):
            if not download:
                return MOCK_INFO_BOTH
            (tmp_path / "video.en.vtt").write_text(_SAMPLE_VTT, encoding="utf-8")
            return None

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = fake_extract_info
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", prefer_manual=False)

        assert result.available is True
        assert result.source == "auto"


class TestTranscriptFetcherLanguageSelection:
    """fetch() returns available=False when no requested language is present."""

    def test_returns_unavailable_when_no_matching_language(self, tmp_path: Path):
        fetcher = TranscriptFetcher()

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = MOCK_INFO_NO_EN
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", languages=["en"])

        assert result.available is False
        assert result.text == ""

    def test_respects_language_priority_order(self, tmp_path: Path):
        """The first matching language in the list is chosen."""
        fetcher = TranscriptFetcher()

        info = {
            "subtitles": {
                "es": [{"ext": "vtt"}],
                "fr": [{"ext": "vtt"}],
            },
            "automatic_captions": {},
        }

        def fake_extract_info(url, download=False):
            if not download:
                return info
            (tmp_path / "video.fr.vtt").write_text(_SAMPLE_VTT, encoding="utf-8")
            return None

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = fake_extract_info
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            # "fr" listed first → should be selected even though "es" exists
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", languages=["fr", "es"])

        assert result.available is True
        assert result.language == "fr"


class TestTranscriptFetcherCacheHit:
    """fetch() uses the cached .transcript.txt when available and non-empty."""

    def test_cache_hit_skips_yt_dlp(self, tmp_path: Path):
        fetcher = TranscriptFetcher()

        # Pre-create the cached text file.
        text_path = tmp_path / "video.transcript.txt"
        text_path.write_text("Cached transcript text", encoding="utf-8")

        mock_class = MagicMock()

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", use_cache=True)

        # yt-dlp should NOT have been called at all.
        mock_class.assert_not_called()

        assert result.available is True
        assert result.text == "Cached transcript text"
        assert result.text_path == text_path

    def test_cache_miss_when_empty_file(self, tmp_path: Path):
        """An empty .transcript.txt is treated as a cache miss."""
        fetcher = TranscriptFetcher()

        text_path = tmp_path / "video.transcript.txt"
        text_path.write_text("", encoding="utf-8")

        mock_class = MagicMock()
        mock_instance = MagicMock()
        # Probe returns no matching language → available=False
        mock_instance.extract_info.return_value = MOCK_INFO_NO_EN
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", use_cache=True)

        # yt-dlp was called (cache miss).
        mock_class.assert_called()
        assert result.available is False

    def test_cache_ignored_when_use_cache_false(self, tmp_path: Path):
        """use_cache=False bypasses the cache even when the file exists."""
        fetcher = TranscriptFetcher()

        text_path = tmp_path / "video.transcript.txt"
        text_path.write_text("Old transcript", encoding="utf-8")

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = MOCK_INFO_NO_EN
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", use_cache=False)

        mock_class.assert_called()
        assert result.available is False

    def test_cache_hit_finds_companion_vtt(self, tmp_path: Path):
        """Cache hit also populates raw_path and language from a companion .vtt file."""
        fetcher = TranscriptFetcher()

        text_path = tmp_path / "video.transcript.txt"
        text_path.write_text("Cached text", encoding="utf-8")
        vtt_path = tmp_path / "video.en.vtt"
        vtt_path.write_text(_SAMPLE_VTT, encoding="utf-8")

        mock_class = MagicMock()

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", use_cache=True)

        assert result.available is True
        assert result.raw_path == vtt_path
        assert result.language == "en"


class TestTranscriptFetcherLangRegionSuffix:
    """fetch() locates .vtt files with lang-region suffixes (e.g. en-US)."""

    def test_handles_en_us_vtt(self, tmp_path: Path):
        fetcher = TranscriptFetcher()

        def fake_extract_info(url, download=False):
            if not download:
                return MOCK_INFO_BOTH
            # yt-dlp writes en-US instead of bare en
            (tmp_path / "video.en-US.vtt").write_text(_SAMPLE_VTT, encoding="utf-8")
            return None

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = fake_extract_info
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video", languages=["en"])

        assert result.available is True
        assert result.raw_path == tmp_path / "video.en-US.vtt"
        assert result.language == "en"
        assert result.text == "Hello from yt-dlp"


class TestTranscriptFetcherSoftFailure:
    """fetch() returns available=False on yt-dlp errors (soft failure)."""

    def test_probe_exception_returns_unavailable(self, tmp_path: Path):
        fetcher = TranscriptFetcher()

        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = RuntimeError("Network error")
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video")

        assert result.available is False

    def test_missing_vtt_after_download_returns_unavailable(self, tmp_path: Path):
        """If yt-dlp download call succeeds but no .vtt file appears, return unavailable."""
        fetcher = TranscriptFetcher()

        mock_class = MagicMock()
        mock_instance = MagicMock()
        # Probe returns info with "en"; download call returns None but writes nothing.
        mock_instance.extract_info.side_effect = [MOCK_INFO_BOTH, None]
        mock_class.return_value.__enter__.return_value = mock_instance
        mock_class.return_value.__exit__.return_value = False

        with patch("amplifier_youtube.transcript.yt_dlp.YoutubeDL", mock_class):
            result = fetcher.fetch(FAKE_URL, tmp_path, "video")

        assert result.available is False
