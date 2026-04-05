# Amplifier YouTube Module

YouTube capability module for Amplifier — download audio/video, search with rich filters, and access account feeds.

## Tools

### youtube-dl — Download
- **YouTube audio/video download** — Extract audio or download full video
- **Screenshot capture** — Capture frames at specific timestamps
- **Metadata extraction** — Get title, duration, description, uploader
- **Local file support** — Also handles local audio/video files
- **Smart caching** — Avoid re-downloading the same content

### youtube-search — Search
- **Rich filters** — Duration, date range, region, HD (with API key)
- **Dual backend** — YouTube Data API v3 with yt-dlp fallback
- **Zero-config** — Works without API key using yt-dlp search

### youtube-feed — Account Data
- **Watch history, subscriptions, liked videos, recommendations, watch later**
- **Cookie-based auth** — Uses browser cookies via yt-dlp
- **Metadata only** — Returns URLs for piping to youtube-dl

## Prerequisites

- **Python 3.11+**
- **[UV](https://github.com/astral-sh/uv)** — Fast Python package manager
- **ffmpeg** — Required for audio extraction and conversion

### Installing UV

```bash
# macOS/Linux/WSL
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installing ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Installation

```bash
uv pip install -e .
```

## Usage

### As an Amplifier Bundle (ad-hoc use)

```bash
amplifier run --bundle git+https://github.com/microsoft/amplifier-youtube@main \
  "Download audio from https://youtube.com/watch?v=..."
```

### Adding to Your Own Bundle

Include the `youtube` behavior in your bundle to add all three tools:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-youtube@main#behaviors/youtube.yaml
```

### Programmatic Use

```python
from amplifier_youtube import YouTubeDownloadTool, YouTubeSearchTool, YouTubeFeedTool

# Download audio from YouTube
dl_tool = YouTubeDownloadTool({"output_dir": "~/downloads", "audio_only": True})
result = await dl_tool.execute({
    "url": "https://youtube.com/watch?v=...",
    "output_filename": "audio.mp3",
})

# Search YouTube
search_tool = YouTubeSearchTool({"api_key": "AIza..."})  # api_key optional
result = await search_tool.execute({
    "query": "python tutorial",
    "max_results": 5,
    "order": "relevance",
})

# Access account feed (requires cookies)
feed_tool = YouTubeFeedTool({}, cookies_file="~/yt-cookies.txt")
result = await feed_tool.execute({
    "feed_type": "history",
    "limit": 20,
})
```

### In a Mount Plan

```yaml
tools:
  - module: youtube
    source: git+https://github.com/microsoft/amplifier-youtube@main
    config:
      output_dir: ~/downloads
      audio_only: true
      cookies_file: ~/yt-cookies.txt    # optional — for feed access
      search:
        api_key: AIza...                 # optional — enables rich filters
        max_results: 10
        safe_search: true
```

## Configuration

### Top-Level Config

| Key | Used By | Default | Description |
|-----|---------|---------|-------------|
| `output_dir` | youtube-dl | `~/downloads` | Where to save downloads |
| `audio_only` | youtube-dl | `true` | Extract audio only by default |
| `cookies_file` | youtube-dl, youtube-feed | — | Path to Netscape-format cookies file |

### Search Config (`search:` sub-key)

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | — | YouTube Data API v3 key (enables rich filters) |
| `max_results` | `10` | Default results per search |
| `safe_search` | `true` | Enable safe search filtering |

### Cookies Setup (for youtube-feed)

Export your browser cookies to a Netscape-format file (use a browser extension like
"Get cookies.txt LOCALLY") and set `cookies_file` in your config. Cookies may expire —
re-export if you see authentication errors.

## Migration from v0.1.0 (amplifier-module-tool-youtube-dl)

This is a **breaking change**. Update your configs:

1. `module: tool-youtube-dl` → `module: youtube`
2. Update source URLs: `amplifier-module-tool-youtube-dl` → `amplifier-youtube`
3. `cookies_file` is now at the top level of module config (shared across tools)

## Dependencies

- `yt-dlp>=2024.0.0` — YouTube download and search engine
- `google-api-python-client>=2.0.0` — YouTube Data API v3 (rich search filters)
- **ffmpeg** (external) — Audio extraction and conversion

> **Note:** `amplifier-core` is a peer dependency provided by the Amplifier runtime — it is not
> listed as a Python package dependency of this module.

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
