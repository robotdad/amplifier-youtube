"""
Transcript Fetcher — fetch YouTube transcripts via yt-dlp and convert VTT to plain text.
"""

import html
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yt_dlp

    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    """Result of a transcript fetch operation."""

    available: bool
    text: str = ""
    raw_path: Path | None = None
    text_path: Path | None = None
    language: str = ""
    source: str = ""


class TranscriptFetcher:
    """Fetch YouTube transcripts via yt-dlp and convert VTT to plain text."""

    def __init__(self, cookies_file: Path | None = None):
        """Initialize transcript fetcher.

        Args:
            cookies_file: Optional path to cookies file for yt-dlp
        """
        self.cookies_file = cookies_file.expanduser() if cookies_file else None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch(
        self,
        url: str,
        output_dir: Path,
        output_stem: str,
        languages: list[str] | None = None,
        prefer_manual: bool = True,
        use_cache: bool = True,
    ) -> TranscriptResult:
        """Fetch transcript for a YouTube video.

        Args:
            url: YouTube URL
            output_dir: Directory to save transcript files
            output_stem: Base filename stem (without extension)
            languages: Language codes in priority order (default: ["en"])
            prefer_manual: Prefer manual subtitles over auto-generated (default: True)
            use_cache: Use cached transcript if available (default: True)

        Returns:
            TranscriptResult with transcript text and metadata.
            ``available=False`` when no transcript could be obtained.
        """
        if not YT_DLP_AVAILABLE:
            logger.warning("yt-dlp not available, cannot fetch transcript")
            return TranscriptResult(available=False)

        if languages is None:
            languages = ["en"]

        output_dir = output_dir.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        text_path = output_dir / f"{output_stem}.transcript.txt"

        # ------------------------------------------------------------------
        # Step 3: Cache check
        # ------------------------------------------------------------------
        if use_cache and text_path.exists() and text_path.stat().st_size > 0:
            logger.info(f"✓ Using cached transcript: {text_path.name}")
            text = text_path.read_text(encoding="utf-8")
            raw_path, language = self._find_cached_vtt(output_dir, output_stem)
            return TranscriptResult(
                available=True,
                text=text,
                raw_path=raw_path,
                text_path=text_path,
                language=language,
                source="",
            )

        # ------------------------------------------------------------------
        # Step 4: Probe available subtitles
        # ------------------------------------------------------------------
        probe_opts: dict[str, Any] = {
            **self._base_opts(),
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
        }

        try:
            with yt_dlp.YoutubeDL(probe_opts) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.warning(f"Failed to probe subtitles for {url}: {e}")
            return TranscriptResult(available=False)

        if not info:
            return TranscriptResult(available=False)

        subtitles: dict[str, Any] = info.get("subtitles") or {}
        auto_captions: dict[str, Any] = info.get("automatic_captions") or {}

        # ------------------------------------------------------------------
        # Step 5: Pick best (lang, source)
        # ------------------------------------------------------------------
        chosen_lang: str | None = None
        chosen_source: str | None = None

        for lang in languages:
            if prefer_manual:
                if lang in subtitles:
                    chosen_lang = lang
                    chosen_source = "manual"
                    break
                if lang in auto_captions:
                    chosen_lang = lang
                    chosen_source = "auto"
                    break
            else:
                if lang in auto_captions:
                    chosen_lang = lang
                    chosen_source = "auto"
                    break
                if lang in subtitles:
                    chosen_lang = lang
                    chosen_source = "manual"
                    break

        if chosen_lang is None or chosen_source is None:
            logger.info(f"No subtitles found for languages {languages}")
            return TranscriptResult(available=False)

        logger.info(f"Downloading {chosen_source} subtitles for language: {chosen_lang}")

        # ------------------------------------------------------------------
        # Step 6: Download chosen variant
        # ------------------------------------------------------------------
        dl_opts: dict[str, Any] = {
            **self._base_opts(),
            "skip_download": True,
            "writesubtitles": chosen_source == "manual",
            "writeautomaticsub": chosen_source == "auto",
            "subtitlesformat": "vtt",
            "subtitleslangs": [chosen_lang],
            "outtmpl": str(output_dir / f"{output_stem}.%(ext)s"),
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:  # type: ignore[arg-type]
                ydl.extract_info(url, download=True)
        except Exception as e:
            logger.warning(f"Failed to download subtitles for {url}: {e}")
            return TranscriptResult(available=False)

        # ------------------------------------------------------------------
        # Step 7: Locate .vtt file (handle lang-region suffixes like en-US)
        # ------------------------------------------------------------------
        vtt_path = self._find_vtt_file(output_dir, output_stem, chosen_lang)
        if vtt_path is None:
            logger.warning(f"Could not find downloaded .vtt file for language '{chosen_lang}'")
            return TranscriptResult(available=False)

        # ------------------------------------------------------------------
        # Step 8: Convert via vtt_to_text, write to text_path
        # ------------------------------------------------------------------
        try:
            text = self.vtt_to_text(vtt_path)
        except Exception as e:
            logger.warning(f"Failed to convert VTT to text: {e}")
            return TranscriptResult(available=False)

        text_path.write_text(text, encoding="utf-8")
        logger.info(f"Transcript saved to: {text_path.name}")

        # ------------------------------------------------------------------
        # Step 9: Return populated result
        # ------------------------------------------------------------------
        return TranscriptResult(
            available=True,
            text=text,
            raw_path=vtt_path,
            text_path=text_path,
            language=chosen_lang,
            source=chosen_source,
        )

    @staticmethod
    def vtt_to_text(vtt_path: Path) -> str:
        """Convert a WebVTT subtitle file to plain text.

        Strips the WEBVTT header, NOTE/STYLE/REGION metadata blocks, timestamp
        lines, cue IDs, and inline tags (``<c>``, ``<b>``, etc.).  HTML entities
        are decoded and consecutive duplicate lines (produced by rolling
        auto-captions) are collapsed to a single occurrence.

        Args:
            vtt_path: Path to the .vtt file.

        Returns:
            Plain-text transcript with one logical line per unique caption.
        """
        content = vtt_path.read_text(encoding="utf-8", errors="replace")
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Split into cue blocks separated by one-or-more blank lines.
        blocks = re.split(r"\n{2,}", content)

        # Matches WebVTT timestamp lines, e.g.:
        #   00:00:01.000 --> 00:00:03.500 align:start position:0%
        # Also handles compact HH:MM:SS.mmm without hours: MM:SS.mmm
        timestamp_re = re.compile(r"\d{1,2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[.,]\d{3}")
        # Inline tags: <c>, <c.colorWhite>, <b>, <i>, </c>, timestamp tags <00:00:00.000>
        inline_tag_re = re.compile(r"<[^>]+>")

        text_lines: list[str] = []

        for block in blocks:
            lines = [ln.strip() for ln in block.strip().splitlines()]
            if not lines:
                continue

            first = lines[0]

            # Skip the WEBVTT file header block (may carry extra metadata lines).
            if first.startswith("WEBVTT"):
                continue

            # Skip NOTE, STYLE, REGION blocks entirely.
            if first.startswith(("NOTE", "STYLE", "REGION")):
                continue

            # Find the timestamp line that marks the boundary between the
            # optional cue ID and the cue payload.
            timestamp_idx: int | None = None
            for i, line in enumerate(lines):
                if timestamp_re.search(line):
                    timestamp_idx = i
                    break

            if timestamp_idx is None:
                # No timestamp found — skip (metadata or unknown block).
                continue

            # Everything after the timestamp line is cue payload text.
            for line in lines[timestamp_idx + 1 :]:
                clean = inline_tag_re.sub("", line)
                clean = html.unescape(clean)
                clean = clean.strip()
                if clean:
                    text_lines.append(clean)

        # Collapse consecutive duplicate lines produced by rolling auto-captions.
        result: list[str] = []
        for line in text_lines:
            if not result or result[-1] != line:
                result.append(line)

        return "\n".join(result)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _base_opts(self) -> dict[str, Any]:
        """Build base yt-dlp options, injecting cookies when available."""
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        if self.cookies_file and self.cookies_file.exists():
            opts["cookiefile"] = str(self.cookies_file)
        return opts

    def _find_vtt_file(self, output_dir: Path, output_stem: str, lang: str) -> Path | None:
        """Locate the downloaded .vtt file, handling lang-region suffixes.

        yt-dlp may write ``stem.en.vtt`` or ``stem.en-US.vtt`` when the lang
        code in the video metadata includes a region qualifier.

        Args:
            output_dir: Directory where yt-dlp wrote the file.
            output_stem: Base stem used in the outtmpl (e.g. ``"video"``).
            lang: Language code that was requested (e.g. ``"en"``).

        Returns:
            Path to the .vtt file, or ``None`` if not found.
        """
        # 1. Exact match: stem.en.vtt
        exact = output_dir / f"{output_stem}.{lang}.vtt"
        if exact.exists():
            return exact

        # 2. Lang-region match: stem.en-US.vtt, stem.en_US.vtt, etc.
        for candidate in sorted(output_dir.glob(f"{output_stem}.{lang}*.vtt")):
            return candidate

        return None

    def _find_cached_vtt(self, output_dir: Path, output_stem: str) -> tuple[Path | None, str]:
        """Locate an existing .vtt file and extract its language from the name.

        Returns a ``(raw_path, language)`` pair for populating a cache hit
        ``TranscriptResult``.
        """
        for vtt_file in sorted(output_dir.glob(f"{output_stem}.*.vtt")):
            # Filename pattern: stem.LANG.vtt  →  parts[-1] after splitting on "."
            # e.g. "video.en.vtt" → stem="video.en", so split on "." gives ["video", "en"]
            name_parts = vtt_file.stem.split(".")
            language = name_parts[-1] if len(name_parts) >= 2 else ""
            return vtt_file, language
        return None, ""
