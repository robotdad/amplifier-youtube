# YouTube Tools

You have access to three YouTube tools.

## youtube-dl — Download

Download YouTube videos and fetch transcripts. By default, the tool downloads the video and
attempts to grab the YouTube-provided transcript (manual subtitles preferred, auto-captions
as fallback). When no transcript is available, the tool signals this so you can fall back to
audio transcription (Whisper) using the saved video.

**Parameters:**
- `url` (required): YouTube URL or local file path
- `prefer_transcript` (optional): `true` (default) fetches transcript/auto-captions after
  downloading video — `audio_only` is ignored in this mode. Set `false` for legacy
  audio-only/video-only behavior.
- `transcript_languages` (optional): Language priority list for transcript lookup, e.g.
  `["en", "fr"]` (default: `["en"]`)
- `audio_only` (optional): Legacy mode only — `true` for MP3, `false` for MP4.
  Ignored when `prefer_transcript` is `true`.
- `output_filename` (optional): Custom output filename
- `use_cache` (optional): Skip re-download if file exists (default: `true`).
  Applies to video, audio, and transcript files.
- `capture_screenshot` (optional): Extract a still frame (default: `false`)
- `screenshot_time` (optional): Timestamp `HH:MM:SS` — required when `capture_screenshot: true`

**Transcript result fields (when prefer_transcript is true):**
- `transcript_available`: `true` if subtitles/auto-captions were found
- `transcript.text`: plain-text transcript content
- `transcript.language`: language code used (e.g. `"en"`)
- `transcript.source`: `"manual"` (creator-uploaded) or `"auto"` (auto-generated)
- `transcript.text_path`: path to saved `.transcript.txt` file
- `fallback_hint`: `"no_transcript_use_whisper_on_video"` — present when
  `transcript_available` is false, indicates the video was saved and Whisper
  can be used as a fallback

## youtube-search — Search

Search YouTube for videos. Routes simple keyword searches to yt-dlp (no quota cost) and
rich filtered searches to the YouTube Data API when an API key is configured. Automatically
degrades to yt-dlp if the API quota is exhausted.

**Parameters:**
- `query` (required): Search terms
- `max_results` (optional): Number of results, default 10, max 50
- `order` (optional): `relevance` (default) | `date` | `viewCount` | `rating`
- `duration` (optional): `any` | `short` (<4 min) | `medium` (4–20 min) | `long` (>20 min) — *API key required*
- `published_after` / `published_before` (optional): ISO 8601 date range — *API key required*
- `region_code` (optional): ISO 3166-1 alpha-2 country code — *API key required*
- `hd_only` (optional): Filter for HD content — *API key required*
- `force_backend` (optional): `"api"` or `"ytdlp"` — bypasses smart routing. `"api"` requires
  an API key and will fail if quota is exhausted. `"ytdlp"` skips the API entirely. Omit for
  automatic routing.

**Routing behavior:** Simple keyword searches (no filters) always use yt-dlp, even with an
API key configured. This preserves API quota for when filters are actually needed. Filters
marked *API key required* trigger the Data API path.

The response includes a `backend` field (`"api"`, `"ytdlp"`, or `"ytdlp_fallback"`) indicating
which search engine was used, a `degraded_filters` list (API-only filters that were silently
dropped when falling back to yt-dlp), and `quota_exhausted: true` when the API quota was hit
this session.

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
