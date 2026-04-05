# YouTube Download Tool

You have access to the `youtube-dl` tool for downloading audio, video, and screenshots
from YouTube URLs, or processing local video files.

## Capabilities

- **Audio download**: Extract MP3 audio from any YouTube URL
- **Video download**: Download full MP4 video
- **Screenshot capture**: Extract a still frame at a specific timestamp
- **Local file processing**: Accept local file paths in addition to URLs

## Tool Parameters

- `url` (required): YouTube URL or local file path
- `audio_only` (optional): `true` for MP3 audio (default), `false` for MP4 video
- `output_filename` (optional): Custom filename for the output
- `use_cache` (optional): Skip re-download if file exists (default: `true`)
- `capture_screenshot` (optional): Extract a still frame (default: `false`)
- `screenshot_time` (optional): Timestamp in `HH:MM:SS` format (required when `capture_screenshot: true`)

## Usage Guidelines

- Default behavior is audio-only (MP3). Explicitly set `audio_only: false` for video.
- Screenshots require both `capture_screenshot: true` AND a `screenshot_time` value.
- Output goes to `~/downloads` by default (configurable via bundle config).
- The tool caches downloads — subsequent requests for the same URL return the cached file
  unless `use_cache: false` is specified.
- For local files, just pass the file path as `url` — the tool detects this automatically.

## System Requirements

- **ffmpeg** must be installed for audio extraction and video processing
- **yt-dlp** handles YouTube downloading (installed automatically as a Python dependency)
