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
    async def test_search_uses_api_when_key_configured(self, tool_with_key):
        mock_response = {
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
