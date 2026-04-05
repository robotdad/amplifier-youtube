# Amplifier YouTube-DL Tool Module

Download audio and video from YouTube with metadata extraction.

## Features

- **YouTube audio/video download** - Extract audio or download full video
- **Screenshot capture** - Capture frames at specific timestamps
- **Metadata extraction** - Get title, duration, description, uploader
- **Local file support** - Also handles local audio/video files
- **Smart caching** - Avoid re-downloading the same content
- **Format conversion** - Automatic conversion to MP3 or MP4

## Prerequisites

- **Python 3.11+**
- **[UV](https://github.com/astral-sh/uv)** - Fast Python package manager
- **ffmpeg** - Required for audio extraction and conversion

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

### As an Amplifier Tool

```python
from amplifier_module_tool_youtube_dl import YouTubeDLTool

# Create tool with config
tool = YouTubeDLTool({
    "output_dir": "~/downloads",
    "audio_only": True  # Set False for video
})

# Download audio from YouTube
result = await tool.execute({
    "url": "https://youtube.com/watch?v=...",
    "output_filename": "audio.mp3",  # Optional
    "use_cache": True  # Optional (default: True)
})

# Download video
result = await tool.execute({
    "url": "https://youtube.com/watch?v=...",
    "audio_only": False,  # Override config
    "output_filename": "video.mp4"
})

# Capture screenshot at specific timestamp
result = await tool.execute({
    "url": "https://youtube.com/watch?v=...",
    "capture_screenshot": True,
    "screenshot_time": "00:05:30",  # HH:MM:SS format
    "output_filename": "screenshot.jpg"
})

# Result includes:
# - path: Path to downloaded file
# - metadata: {title, id, duration, description, uploader}
# - screenshot_path: Path to screenshot (if requested)
```

### As an Amplifier Bundle (ad-hoc use)

The simplest way to use this tool is via the companion bundle, which includes the
tool registration and context instructions in one command:

```bash
amplifier run --bundle git+https://github.com/microsoft/amplifier-module-tool-youtube-dl@main \
  "Download audio from https://youtube.com/watch?v=..."
```

### Adding to Your Own Bundle

Include the `youtube-dl` behavior in your own bundle to add download capability:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-module-tool-youtube-dl@main#behaviors/youtube-dl.yaml
```

### In an Amplifier Profile (legacy)

You can also register the module directly in a profile:

```yaml
---
profile:
  name: youtube-downloader
  extends: base

tools:
  - module: tool-youtube-dl
    source: git+https://github.com/microsoft/amplifier-module-tool-youtube-dl@main
    config:
      output_dir: ~/downloads
      audio_only: true
---

# YouTube Downloader Profile

Enables YouTube content downloading in amplifier sessions.
```

Then use in conversation:

```bash
amplifier run --profile youtube-downloader
> "Download audio from https://youtube.com/watch?v=..."
```

### Local File Handling

The tool also extracts metadata from local audio/video files:

```python
result = await tool.execute({
    "url": "/path/to/local-video.mp4"
})

# Extracts: duration, format info, etc.
```

## Configuration

Tool configuration options:

- `output_dir`: Where to save downloads (default: `~/downloads`)
- `audio_only`: Extract audio only vs. full video (default: `True`)
- `cookies_file`: Path to a Netscape-format cookies file for yt-dlp (optional, useful for age-restricted or authenticated content)

### Execution Parameters

Per-request options:

- `url`: YouTube URL or local file path (required)
- `audio_only`: Override config setting for this request
- `output_filename`: Custom filename (optional)
- `use_cache`: Use cached file if exists (default: `True`)
- `capture_screenshot`: Extract screenshot (default: `False`)
- `screenshot_time`: Timestamp for screenshot in HH:MM:SS format (required if capture_screenshot is True)

## Caching

The tool caches downloaded files by default. If the output file already exists:
- Uses cached version (fast)
- Skips re-download
- Override with `use_cache: False` in execute params

## Supported Platforms

Currently supports:
- **YouTube** - Videos, playlists (individual videos)
- **Local files** - MP4, MP3, WAV, M4A, etc.

## Event Emission

Emits standard amplifier events:

- `tool:pre` - Before download starts
- `tool:post` - After successful download
- `tool:error` - On download failure

## Dependencies

- `yt-dlp>=2024.0.0` - YouTube download engine (Python, installed automatically)
- **ffmpeg** (external) - Audio extraction and conversion (must be installed separately)

> **Note:** `amplifier-core` is a peer dependency provided by the Amplifier runtime — it is not
> listed as a Python package dependency of this module.

## Troubleshooting

### "yt-dlp is not installed"

Install with UV:
```bash
uv add yt-dlp
```

### "ffmpeg not found"

Install ffmpeg for your platform (see Prerequisites section).

### "Failed to download URL"

Common causes:
- Video is private or deleted
- Age-restricted content
- Geographic restrictions
- Rate limiting (try again later)

### "Could not find downloaded audio file"

Ensure ffmpeg is installed. The tool requires ffmpeg for audio extraction.

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
