"""Tests for the mount() entry point registering all three tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from amplifier_youtube import mount


class TestMount:
    @pytest.mark.asyncio
    async def test_mount_registers_three_tools(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        result = await mount(coordinator)
        assert coordinator.mount.call_count == 3
        names = {call[1]["name"] for call in coordinator.mount.call_args_list}
        assert names == {"youtube-dl", "youtube-search", "youtube-feed"}
        assert set(result["provides"]) == {"youtube-dl", "youtube-search", "youtube-feed"}

    @pytest.mark.asyncio
    async def test_mount_distributes_search_config(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        await mount(coordinator, {"search": {"api_key": "test-key", "max_results": 25}})
        search_tool = next(c[0][1] for c in coordinator.mount.call_args_list if c[1]["name"] == "youtube-search")
        assert search_tool.api_key == "test-key"
        assert search_tool.default_max_results == 25

    @pytest.mark.asyncio
    async def test_mount_passes_cookies_to_feed_tool(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        await mount(coordinator, {"cookies_file": "~/cookies.txt"})
        feed_tool = next(c[0][1] for c in coordinator.mount.call_args_list if c[1]["name"] == "youtube-feed")
        assert feed_tool.cookies_file == "~/cookies.txt"

    @pytest.mark.asyncio
    async def test_mount_returns_correct_manifest(self):
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        result = await mount(coordinator)
        assert result["name"] == "youtube"
        assert result["version"] == "0.2.0"
