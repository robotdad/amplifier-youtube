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
