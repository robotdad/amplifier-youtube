# YouTube Tools

You have access to three YouTube tools.

## youtube-dl — Download

Download audio or video from YouTube URLs or local video files.

**Parameters:**
- `url` (required): YouTube URL or local file path
- `audio_only` (optional): `true` for MP3 audio (default), `false` for MP4 video
- `output_filename` (optional): Custom output filename
- `use_cache` (optional): Skip re-download if file exists (default: `true`)
- `capture_screenshot` (optional): Extract a still frame (default: `false`)
- `screenshot_time` (optional): Timestamp `HH:MM:SS` — required when `capture_screenshot: true`

## youtube-search — Search

Search YouTube for videos. Returns a list of results with URLs that can be passed to `youtube-dl`.

**Parameters:**
- `query` (required): Search terms
- `max_results` (optional): Number of results, default 10, max 50
- `order` (optional): `relevance` (default) | `date` | `viewCount` | `rating`
- `duration` (optional): `any` | `short` (<4 min) | `medium` (4–20 min) | `long` (>20 min) — *API key required*
- `published_after` / `published_before` (optional): ISO 8601 date range — *API key required*
- `region_code` (optional): ISO 3166-1 alpha-2 country code — *API key required*
- `hd_only` (optional): Filter for HD content — *API key required*

The response includes a `backend` field (`"api"` or `"ytdlp"`) indicating which search engine was used.
Filters marked *API key required* are silently ignored when no API key is configured.

## youtube-feed — Account Data

Access your YouTube account feeds. **Requires `cookies_file` to be configured.**

**Parameters:**
- `feed_type` (required): `history` | `subscriptions` | `liked` | `recommendations` | `watch_later`
- `limit` (optional): Max items to return (default: 50)

Returns metadata only (id, title, channel, url, upload_date, duration_seconds).
Pass `url` values to `youtube-dl` to download items.

**Cookies setup:** Export your browser cookies to a Netscape-format file (use a browser extension
like "Get cookies.txt LOCALLY") and set `cookies_file: ~/path/to/cookies.txt` in your bundle config.
Cookies may expire — re-export if you see authentication errors.
