"""Tests for YouTubeSearchTool."""

import json
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError

from amplifier_youtube.search_tool import YouTubeSearchTool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_quota_error(reason: str = "quotaExceeded") -> HttpError:
    """Construct a fake HttpError that looks like a YouTube quota exhaustion."""
    resp = Mock(status=403, reason="Forbidden")
    body = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()
    err = HttpError(resp, body)
    err.error_details = [{"reason": reason, "domain": "youtube.quota", "message": "exhausted"}]
    return err


def _setup_ytdlp(mock_cls: MagicMock, results: dict) -> MagicMock:
    """Wire up a yt_dlp.YoutubeDL context-manager mock."""
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = results
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_ydl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
            {
                "id": "abc123",
                "title": "Test Video",
                "channel": "Test Channel",
                "upload_date": "20250101",
                "description": "desc",
                "url": "https://youtube.com/watch?v=abc123",
                "duration": 300,
            },
        ]
    }


@pytest.fixture
def mock_api_response():
    return {
        "items": [
            {
                "id": {"videoId": "xyz789"},
                "snippet": {
                    "title": "API Result",
                    "channelTitle": "API Channel",
                    "publishedAt": "2025-01-01T00:00:00Z",
                    "description": "API desc",
                },
            }
        ]
    }


# ---------------------------------------------------------------------------
# Existing tests (updated for new output fields)
# ---------------------------------------------------------------------------


class TestYouTubeSearchToolNoApiKey:
    @pytest.mark.asyncio
    async def test_search_uses_ytdlp_without_api_key(self, tool_no_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
            result = await tool_no_key.execute({"query": "python tutorial"})
        assert result.success is True
        assert result.output["backend"] == "ytdlp"
        assert result.output["degraded_filters"] == []
        assert result.output["quota_exhausted"] is False
        assert len(result.output["results"]) == 1
        assert result.output["results"][0]["id"] == "abc123"

    @pytest.mark.asyncio
    async def test_date_order_uses_ytsearchdate_prefix(self, tool_no_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
            await tool_no_key.execute({"query": "python tutorial", "order": "date"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg.startswith("ytsearchdate")

    @pytest.mark.asyncio
    async def test_relevance_order_uses_ytsearch_prefix(self, tool_no_key, mock_ytdlp_results):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl = _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
            await tool_no_key.execute({"query": "python tutorial", "order": "relevance"})
            call_arg = mock_ydl.extract_info.call_args[0][0]
        assert call_arg.startswith("ytsearch") and not call_arg.startswith("ytsearchdate")

    @pytest.mark.asyncio
    async def test_missing_query_returns_error(self, tool_no_key):
        result = await tool_no_key.execute({})
        assert result.success is False
        assert "query" in result.error["message"]

    @pytest.mark.asyncio
    async def test_ytdlp_failure_returns_error_result(self, tool_no_key):
        with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_cls:
            mock_ydl = MagicMock()
            mock_ydl.extract_info.side_effect = Exception("network error")
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = await tool_no_key.execute({"query": "python tutorial"})
        assert result.success is False
        assert "network error" in result.error["message"]


class TestYouTubeSearchToolWithApiKey:
    @pytest.mark.asyncio
    async def test_search_uses_api_when_filtered(self, tool_with_key, mock_api_response):
        """A query with an API-only filter (region_code) must route to the Data API."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.return_value = mock_api_response
            result = await tool_with_key.execute({"query": "python tutorial", "region_code": "US"})
        assert result.success is True
        assert result.output["backend"] == "api"
        assert result.output["degraded_filters"] == []
        assert result.output["quota_exhausted"] is False
        assert result.output["results"][0]["id"] == "xyz789"

    @pytest.mark.asyncio
    async def test_api_failure_falls_back_to_ytdlp_fallback(self, tool_with_key, mock_ytdlp_results):
        """Non-quota API error on a filtered request → ytdlp_fallback with degraded_filters."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_build.side_effect = Exception("transient network error")
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_with_key.execute({"query": "python tutorial", "region_code": "US"})
        assert result.success is True
        assert result.output["backend"] == "ytdlp_fallback"
        assert "region_code" in result.output["degraded_filters"]

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


# ---------------------------------------------------------------------------
# Smart routing tests
# ---------------------------------------------------------------------------


class TestSmartRouting:
    # -- No API key scenarios -----------------------------------------------

    @pytest.mark.asyncio
    async def test_no_key_simple_query_uses_ytdlp_build_not_called(self, tool_no_key, mock_ytdlp_results):
        """Simple query with no API key → ytdlp, no degraded filters, build never called."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_no_key.execute({"query": "cats"})
        assert result.output["backend"] == "ytdlp"
        assert result.output["degraded_filters"] == []
        mock_build.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_key_with_duration_filter_warns_and_degrades(self, tool_no_key, mock_ytdlp_results, caplog):
        """No api_key + duration filter → ytdlp, degraded_filters==[duration], warning logged."""
        with caplog.at_level(logging.WARNING, logger="amplifier_youtube.search_tool"):
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_no_key.execute({"query": "cats", "duration": "long"})
        assert result.output["backend"] == "ytdlp"
        assert result.output["degraded_filters"] == ["duration"]
        assert result.output["quota_exhausted"] is False
        assert "duration" in caplog.text

    # -- API key present scenarios ------------------------------------------

    @pytest.mark.asyncio
    async def test_api_key_simple_query_uses_ytdlp_not_api(self, tool_with_key, mock_ytdlp_results):
        """Simple query with api_key → ytdlp (no quota spent), build NOT called."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_with_key.execute({"query": "python"})
        assert result.output["backend"] == "ytdlp"
        assert result.output["degraded_filters"] == []
        mock_build.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_key_region_code_routes_to_api(self, tool_with_key, mock_api_response):
        """region_code is an API-only filter → build is called, backend=='api'."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.return_value = mock_api_response
            result = await tool_with_key.execute({"query": "news", "region_code": "US"})
        assert result.output["backend"] == "api"
        mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_key_viewcount_order_routes_to_api(self, tool_with_key, mock_api_response):
        """order=viewCount is API-only → routes to API, not ytdlp."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.return_value = mock_api_response
            result = await tool_with_key.execute({"query": "popular", "order": "viewCount"})
        assert result.output["backend"] == "api"
        mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_order_date_is_not_api_only_routes_to_ytdlp(self, tool_with_key, mock_ytdlp_results):
        """order=date is NOT in _API_ONLY_ORDERS → ytdlp, uses ytsearchdate prefix."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                mock_ydl = _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_with_key.execute({"query": "news", "order": "date"})
                call_arg = mock_ydl.extract_info.call_args[0][0]
        assert result.output["backend"] == "ytdlp"
        assert result.output["degraded_filters"] == []
        assert call_arg.startswith("ytsearchdate")
        mock_build.assert_not_called()

    # -- Quota exhaustion ---------------------------------------------------

    @pytest.mark.asyncio
    async def test_quota_exhaustion_sets_flag_and_returns_fallback(self, tool_with_key, mock_ytdlp_results):
        """Quota error → ytdlp_fallback + _quota_exhausted=True; next call skips build."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.side_effect = make_quota_error()
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_with_key.execute({"query": "python", "duration": "short"})

        assert result.success is True
        assert result.output["backend"] == "ytdlp_fallback"
        assert "duration" in result.output["degraded_filters"]
        assert result.output["quota_exhausted"] is True
        assert tool_with_key._quota_exhausted is True

        # Second call must not touch the API at all.
        with patch("amplifier_youtube.search_tool.build") as mock_build2:
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls2:
                _setup_ytdlp(mock_ydl_cls2, mock_ytdlp_results)
                result2 = await tool_with_key.execute({"query": "python", "duration": "short"})

        assert result2.output["backend"] == "ytdlp_fallback"
        assert result2.output["quota_exhausted"] is True
        mock_build2.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_quota_api_error_falls_back_without_setting_flag(self, tool_with_key, mock_ytdlp_results):
        """A non-quota API error → ytdlp_fallback for this request, but flag stays False."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            mock_youtube.search().list().execute.side_effect = Exception("network timeout")
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_with_key.execute({"query": "python", "duration": "short"})

        assert result.success is True
        assert result.output["backend"] == "ytdlp_fallback"
        assert tool_with_key._quota_exhausted is False

    # -- force_backend ------------------------------------------------------

    @pytest.mark.asyncio
    async def test_force_ytdlp_bypasses_api(self, tool_with_key, mock_ytdlp_results):
        """force_backend='ytdlp' must skip the API even with api_key set."""
        with patch("amplifier_youtube.search_tool.build") as mock_build:
            with patch("amplifier_youtube.search_tool.yt_dlp.YoutubeDL") as mock_ydl_cls:
                _setup_ytdlp(mock_ydl_cls, mock_ytdlp_results)
                result = await tool_with_key.execute({"query": "python", "force_backend": "ytdlp"})
        assert result.output["backend"] == "ytdlp"
        mock_build.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_api_without_key_returns_error(self, tool_no_key):
        """force_backend='api' with no api_key → success=False, no ytdlp fallback."""
        result = await tool_no_key.execute({"query": "python", "force_backend": "api"})
        assert result.success is False
        assert "API key" in result.error["message"]

    @pytest.mark.asyncio
    async def test_force_api_with_quota_exhausted_returns_error(self, tool_with_key):
        """force_backend='api' when quota already exhausted → success=False immediately."""
        tool_with_key._quota_exhausted = True
        tool_with_key._quota_reason = "quotaExceeded"
        result = await tool_with_key.execute({"query": "python", "force_backend": "api"})
        assert result.success is False
        assert "exhausted" in result.error["message"]


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestYouTubeSearchToolSchema:
    def test_name(self):
        assert YouTubeSearchTool({}).name == "youtube-search"

    def test_input_schema_has_required_query(self):
        schema = YouTubeSearchTool({}).input_schema
        assert "query" in schema["required"]

    def test_input_schema_has_force_backend(self):
        schema = YouTubeSearchTool({}).input_schema
        assert "force_backend" in schema["properties"]
        assert schema["properties"]["force_backend"]["enum"] == ["api", "ytdlp"]

    def test_description_mentions_routing(self):
        desc = YouTubeSearchTool({}).description
        assert "yt-dlp" in desc
        assert "quota" in desc
