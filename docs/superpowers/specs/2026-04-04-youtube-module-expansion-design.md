# Design: amplifier-youtube — YouTube Module Expansion

**Date:** 2026-04-04  
**Status:** Approved  
**Repo (current):** `amplifier-module-tool-youtube-dl`  
**Repo (target):** `amplifier-youtube`

---

## Overview

Expand the existing YouTube download module into a comprehensive YouTube capability module
providing three focused tools: download, search, and account feed access. The repo is renamed
to `amplifier-youtube` following the current ecosystem naming convention (domain-only, no type
qualifier).

### Goals

- Add YouTube search with YouTube Data API (rich filters) falling back to yt-dlp (unlimited, basic)
- Add account data access (watch history, subscriptions, liked videos, recommendations, watch later)
  via yt-dlp with cookies authentication
- Keep all three tools in a single repo and Python package
- Rename repo and package to reflect the expanded scope

### Non-Goals

- OAuth support for the YouTube Data API (API key only; account data goes through yt-dlp + cookies)
- Downloading from non-YouTube platforms (yt-dlp supports them, but this module stays YouTube-focused)
- Real-time streaming or live video handling

---

## Repo & Package Rename

| Item | Before | After |
|------|--------|-------|
| GitHub repo | `amplifier-module-tool-youtube-dl` | `amplifier-youtube` |
| PyPI package name | `amplifier-module-tool-youtube-dl` | `amplifier-youtube` |
| Python package dir | `src/amplifier_module_tool_youtube_dl/` | `src/amplifier_youtube/` |
| Module entry point key | `tool-youtube-dl` | `youtube` |
| Bundle name | `youtube-dl` | `youtube` |
| Behavior file | `behaviors/youtube-dl.yaml` | `behaviors/youtube.yaml` |

**Breaking change:** Any mount plan or bundle referencing `module: tool-youtube-dl` must be
updated to `module: youtube`. This is the correct moment to make the break cleanly.

---

## Architecture

```
amplifier-youtube/
├── src/amplifier_youtube/
│   ├── __init__.py          ← mount() — registers all three tools
│   ├── download_tool.py     ← YouTubeDownloadTool  (name: "youtube-dl")
│   ├── search_tool.py       ← YouTubeSearchTool    (name: "youtube-search")
│   ├── feed_tool.py         ← YouTubeFeedTool      (name: "youtube-feed")
│   └── core.py              ← shared: VideoLoader, VideoInfo, AudioExtractor
├── tests/
│   ├── test_download_tool.py
│   ├── test_search_tool.py
│   └── test_feed_tool.py
├── bundle.md
├── behaviors/youtube.yaml
├── context/instructions.md
└── pyproject.toml
```

### mount() — Registers All Three Tools

```python
async def mount(coordinator, config=None):
    cfg = config or {}
    shared_output_dir = cfg.get("output_dir", "~/downloads")
    shared_cookies    = cfg.get("cookies_file")

    await coordinator.mount("tools", YouTubeDownloadTool(cfg), name="youtube-dl")
    await coordinator.mount("tools", YouTubeSearchTool(cfg.get("search", {})), name="youtube-search")
    await coordinator.mount("tools", YouTubeFeedTool(cfg.get("feed", {}), cookies_file=shared_cookies), name="youtube-feed")

    return {
        "name": "youtube",
        "version": "0.2.0",
        "provides": ["youtube-dl", "youtube-search", "youtube-feed"],
    }
```

---

## Tool Designs

### 1. `youtube-dl` — Download Tool *(refactored, functionally unchanged)*

**Class:** `YouTubeDownloadTool`  
**File:** `download_tool.py`  
**Changes from current:** rename only; `cookies_file` is now passed from top-level config.

**Input schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ✅ | — | YouTube URL or local file path |
| `audio_only` | boolean | — | config default | Download audio (MP3) or full video (MP4) |
| `output_filename` | string | — | auto | Custom output filename |
| `use_cache` | boolean | — | `true` | Skip re-download if file exists |
| `capture_screenshot` | boolean | — | `false` | Extract a frame from the video |
| `screenshot_time` | string | — | — | Timestamp `HH:MM:SS`; required if `capture_screenshot` is true |

**Returns:** `{path, metadata: {title, id, duration, description, uploader, type}, screenshot_path?}`

**Config:** `output_dir` (default `~/downloads`), `audio_only` (default `true`), `cookies_file` (optional, from top-level)

---

### 2. `youtube-search` — Search Tool *(new)*

**Class:** `YouTubeSearchTool`  
**File:** `search_tool.py`

**Backend selection (transparent to LLM):**

```
api_key in config?
  YES → YouTube Data API v3 (rich filters, 100 searches/day on free tier)
         on quota error or API failure → silent fallback to yt-dlp
  NO  → yt-dlp ytsearch (keyword + sort order, unlimited)
```

API-only parameters are silently ignored when yt-dlp handles the call. The `backend` field in
the response tells callers which path fired.

**Input schema:**

| Parameter | Type | Required | Default | API only? | Description |
|-----------|------|----------|---------|-----------|-------------|
| `query` | string | ✅ | — | — | Search terms |
| `max_results` | integer | — | `10` | — | Number of results (max 50) |
| `order` | enum | — | `relevance` | partial | `relevance` \| `date` \| `viewCount` \| `rating`. yt-dlp supports `relevance` and `date` only |
| `duration` | enum | — | `any` | ✅ | `any` \| `short` (<4 min) \| `medium` (4–20 min) \| `long` (>20 min) |
| `published_after` | string | — | — | ✅ | ISO 8601 date (e.g. `2025-01-01T00:00:00Z`) |
| `published_before` | string | — | — | ✅ | ISO 8601 date |
| `region_code` | string | — | — | ✅ | ISO 3166-1 alpha-2 (e.g. `"US"`) |
| `hd_only` | boolean | — | `false` | ✅ | Filter for HD content only |

**Returns:**
```json
{
  "results": [
    {
      "id": "dQw4w9WgXcQ",
      "title": "...",
      "channel": "...",
      "duration_seconds": 212,
      "published_at": "2009-10-25",
      "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "description": "..."
    }
  ],
  "backend": "api",
  "total_results": 10
}
```

**Config:** `api_key` (optional), `max_results` default (10), `safe_search` (bool, default `true`)

**Error handling:**
- API quota exhausted → silently retry with yt-dlp, set `backend: "ytdlp"` in response
- API key invalid → log warning, fall back to yt-dlp permanently for session
- yt-dlp search fails → return error result with `success: false`

---

### 3. `youtube-feed` — Account Feed Tool *(new)*

**Class:** `YouTubeFeedTool`  
**File:** `feed_tool.py`

Provides read-only access to the authenticated user's YouTube account feeds. All feeds are
accessed via yt-dlp with a cookies file — the YouTube Data API does not support watch history
or recommendations, and the cookies approach works for all five feed types uniformly.

Returns metadata only (no download). Results are intended to be passed to `youtube-dl`.

**Input schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `feed_type` | enum | ✅ | — | `history` \| `subscriptions` \| `liked` \| `recommendations` \| `watch_later` |
| `limit` | integer | — | `50` | Max items to return. Maps to yt-dlp `-I 1:N` slice |

**yt-dlp feed mapping:**

| `feed_type` | yt-dlp target |
|-------------|--------------|
| `history` | `:ythistory` |
| `subscriptions` | `:ytsubs` |
| `liked` | `:ytfav` |
| `recommendations` | `:ytrec` |
| `watch_later` | `:ytwatchlater` |

**Returns:**
```json
{
  "feed_type": "history",
  "items": [
    {
      "id": "dQw4w9WgXcQ",
      "title": "...",
      "channel": "...",
      "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "upload_date": "20250101",
      "duration_seconds": 212
    }
  ],
  "count": 50
}
```

**Config:** `cookies_file` (inherited from top-level config, **required** for all feed types)

**Error handling:**
- `cookies_file` not configured → return clear error: `"youtube-feed requires cookies_file to be configured"`
- Cookies expired or invalid → surface yt-dlp error message, suggest re-exporting cookies
- Feed access denied → return error with feed-specific guidance

---

## Shared Config Structure

```yaml
tools:
  - module: youtube
    source: git+https://github.com/microsoft/amplifier-youtube@main
    config:
      output_dir: ~/downloads          # used by: youtube-dl
      audio_only: true                 # used by: youtube-dl (default)
      cookies_file: ~/yt-cookies.txt   # used by: youtube-dl, youtube-feed

      search:
        api_key: AIza...               # optional — enables rich search filters
        max_results: 10                # default results per search
        safe_search: true

      feed:
        # No feed-specific config currently — limit is a per-call parameter
```

---

## Bundle Updates

`bundle.md` and `behaviors/youtube.yaml` are updated to reflect the new module ID (`youtube`)
and include context for all three tools.

`context/instructions.md` is expanded to document `youtube-search` and `youtube-feed` alongside
the existing `youtube-dl` instructions.

---

## Dependencies

**Runtime (pyproject.toml `[project] dependencies`):**
- `yt-dlp >= 2024.0.0` *(unchanged)*
- `google-api-python-client >= 2.0.0` *(new — YouTube Data API v3)*

**Dev only (`[dependency-groups] dev`):**
- `amplifier-core` (peer dep, from git)
- `pytest`, `pytest-asyncio`, `pytest-mock`, `ruff` *(unchanged)*

`google-api-python-client` is a runtime dep because it is always installed alongside the
package. The API client is only *initialized* when `api_key` is present in config — no API
key means yt-dlp handles all search calls and the installed library sits idle.

---

## Testing Plan

Each tool gets its own test file. Existing download tests are migrated from
`tests/test_youtube_tool.py` to `tests/test_download_tool.py` with minor rename updates.

**`test_search_tool.py` coverage:**
- Search with API key → calls Data API, returns results with `backend: "api"`
- Search without API key → calls yt-dlp, returns results with `backend: "ytdlp"`
- API quota error → silently falls back to yt-dlp
- API-only params ignored gracefully in yt-dlp fallback mode
- `max_results` respected in both backends
- Missing `query` → validation error

**`test_feed_tool.py` coverage:**
- Each `feed_type` maps to the correct yt-dlp target string
- `limit` maps to correct `-I 1:N` slice
- Missing `cookies_file` config → clear error message
- yt-dlp error (expired cookies) → error surfaced with guidance
- Returns correct response schema

**`test_download_tool.py` coverage:**
- All existing tests from `test_youtube_tool.py`, migrated

**`test_mount.py` (or updated `__init__` test):**
- `mount()` calls `coordinator.mount()` exactly 3 times
- All three tool names registered: `youtube-dl`, `youtube-search`, `youtube-feed`
- `provides` list contains all three
- Config is correctly distributed to each tool

---

## Migration Notes

This is a **breaking change** from `amplifier-module-tool-youtube-dl`. Consumers must:

1. Update `module: tool-youtube-dl` → `module: youtube` in all mount plans and bundles
2. Update the `source:` URL from `amplifier-module-tool-youtube-dl` → `amplifier-youtube`
3. Flatten the `cookies_file` config: it was previously under the tool config; it is now
   at the top level of the module config (shared across tools)

A `v0.2.0` version bump accompanies this release to signal the breaking change.
