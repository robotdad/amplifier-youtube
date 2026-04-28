---
bundle:
  name: youtube-downloader
  version: 1.0.0
  description: YouTube download and transcription assistant

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-youtube@main
---

# YouTube Downloader

A minimal bundle that adds YouTube download, transcript, search, and feed
capabilities to an Amplifier session.

## Quick Start

1. Install ffmpeg (required for audio/video processing):
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   ```

2. Run:
   ```bash
   amplifier run --bundle examples/youtube-dl.md
   ```

3. Use in conversation:
   ```
   > Download and transcribe https://youtube.com/watch?v=...
   > Search YouTube for "rust programming" tutorials from this year
   > Show my watch history
   ```

## What You Get

Three tools are available in your session:

- **youtube-dl** — Download video + fetch transcript (subtitles preferred,
  auto-captions as fallback). Falls back to Whisper-ready video when no
  transcript is available.
- **youtube-search** — Search YouTube. Simple queries use yt-dlp (free);
  filtered queries (duration, date range, region) use the Data API when
  an API key is configured.
- **youtube-feed** — Access watch history, subscriptions, liked videos,
  recommendations. Requires a cookies file.

## Custom Configuration

Override defaults by adding a `tools:` section:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-youtube@main

tools:
  - module: tool-youtube
    source: git+https://github.com/microsoft/amplifier-youtube@main#subdirectory=modules/tool-youtube
    config:
      output_dir: ~/my-videos
      prefer_transcript: false    # legacy mode: audio_only controls output
      audio_only: false           # download full video (only when prefer_transcript is false)
      transcript_languages: ["es", "en"]  # prefer Spanish, fall back to English
      cookies_file: ~/yt-cookies.txt
      search:
        api_key: AIza...          # enables rich search filters
        max_results: 20
```

## Combining with Whisper

When `transcript_available` is `false` in the download result, the video is
already saved and ready for Whisper transcription:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-youtube@main
  - bundle: git+https://github.com/microsoft/amplifier-module-tool-whisper@main
```

The AI will use both tools: download + transcript first, Whisper only when needed.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "yt-dlp is not installed" | Should install automatically; if not: `pip install yt-dlp` |
| "ffmpeg not found" | Install ffmpeg for your platform (see Quick Start) |
| "Failed to download URL" | Check URL in browser — may be private, age-restricted, or geo-blocked |
| "cookies may have expired" | Re-export cookies from your browser |
