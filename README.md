# RemarkableSync
[![GitHub](https://img.shields.io/badge/GitHub-RemarkableSync-blue?logo=github)](https://github.com/JeffSteinbok/RemarkableSync)
[![GitHub release](https://img.shields.io/github/v/release/JeffSteinbok/RemarkableSync)](https://github.com/JeffSteinbok/RemarkableSync/releases)

[![CI](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/ci.yml)
[![Build Executables](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/build-executables.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/build-executables.yml)
[![Release](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/release.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/release.yml)

[![Publish to PyPI](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/publish-pypi.yml)
[![PyPI version](https://img.shields.io/pypi/v/remarkablesync.svg)](https://pypi.org/project/remarkablesync/)
[![Homebrew](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/update-homebrew.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/update-homebrew.yml)


A comprehensive Python toolkit for backing up and converting reMarkable tablet notebooks to PDF with template support and proper folder hierarchy preservation — now with **Wi-Fi sync**, **AI handwriting recognition**, and direct **Markdown output export**.

> [!IMPORTANT]
> This tool has been tested exclusively on reMarkable 2. Compatibility with reMarkable 1 is not guaranteed.


## Features

### 🔄 Backup & Sync
- **USB Connection**: Connects to reMarkable tablet over USB (10.11.99.1)
- **Wi-Fi Connection**: Connect over your local network using an IP address or hostname; optional mDNS auto-discovery (`remarkable.local`)
- **Periodic Watch Mode**: Run syncs automatically every N minutes with file-locking to prevent overlapping runs and exponential back-off on failures
- **Incremental Sync**: Only downloads files that have changed since last backup
- **Complete Backup**: Backs up all notebooks, documents, and metadata
- **Template Support**: Automatically backs up template files from the device
- **File Integrity**: MD5 hash verification for synced files

### 📄 PDF Conversion
- **Hybrid Converter**: Supports both v5 and v6 .rm file formats
- **Template Rendering**: Applies original notebook templates (grids, lines, etc.) to PDFs
- **SVG Pipeline**: Uses rmc → SVG → PDF conversion for high quality output
- **Folder Hierarchy**: Recreates original device folder structure in output
- **Single PDF per Notebook**: Merges all pages into one PDF file per notebook
- **Smart Conversion**: Only converts notebooks updated in the last backup
- **Progress Tracking**: Visual progress bars and detailed logging

### 🤖 AI Handwriting Recognition
- **Vision-based OCR**: Send page images directly to Claude or GitHub Models (GPT-4o) for best-in-class handwriting transcription
- **AI Post-processing**: LLM-powered cleanup structures raw notes into clean Markdown with headings, bullets, and action items
- **pytesseract Fallback**: Offline OCR via Tesseract when no AI provider is configured
- **Provider Abstraction**: Pluggable architecture — add your own provider by subclassing `BaseAIProvider`

### 📓 Markdown Output Export
- **Markdown Notes**: Each notebook becomes a `.md` file with YAML frontmatter
- **Embedded Images**: Page images are copied into the output directory and linked with wiki-style `![[file]]` syntax
- **Folder Hierarchy**: Notes are placed in the same folder structure as on the device
- **Custom Tags**: Add your own frontmatter tags to every note
- **Incremental Export**: Only re-exports notebooks whose PDF has changed (tracked via MD5 hash)

## Prerequisites

1. **reMarkable Tablet Setup**:
   - Connect your reMarkable tablet to your computer via USB
   - Enable SSH access (it's enabled by default)
   - Get your SSH password from Settings → Help → Copyright and licenses

2. **Python Requirements**:
   - Python 3.11 or higher (required)
   - Required packages (install with `pip install -r requirements.txt`)
   - All dependencies including `rmc` are installed automatically

## Installation

### Option 1: Homebrew (Recommended for macOS)

**macOS users** can install RemarkableSync using Homebrew:

```bash
# Add the tap (one time only)
brew tap jeffsteinbok/remarkablesync

# Install RemarkableSync
brew install remarkablesync
```

This will automatically:
- Install Python 3.13 and all dependencies (including `rmc`)
- Set up everything needed for PDF conversion

**Updating to latest version:**
```bash
brew upgrade remarkablesync
```

**Uninstalling:**
```bash
brew uninstall remarkablesync
brew untap jeffsteinbok/remarkablesync
```

### Option 2: pip (All Platforms)

**For users with Python 3.11+** installed:

```bash
# Install using pip (recommended: use a virtual environment)
pip install remarkablesync
```

**Updating to latest version:**
```bash
pip install --upgrade remarkablesync
```

### Option 3: Pre-built Executables (Windows/macOS)

**For users without Python** or who prefer standalone executables, download from the [Releases page](https://github.com/JeffSteinbok/RemarkableSync/releases).

> [!IMPORTANT]
> **macOS Users:** Use the included `RemarkableSync.sh` script to launch the application. This automatically handles macOS Gatekeeper security:
> ```bash
> ./RemarkableSync.sh
> ```
> The script removes the quarantine flag and runs the executable. You can pass any command-line arguments:
> ```bash
> ./RemarkableSync.sh backup -v
> ./RemarkableSync.sh convert --sample 5
> ```


### Option 4: From Source (For Developers)

1. Clone this repository:
   ```bash
   git clone https://github.com/JeffSteinbok/RemarkableSync.git
   cd RemarkableSync
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

The simplest way to get started:

1. **Connect your reMarkable tablet** via USB
2. **Get your SSH password** from Settings → Help → Copyright and licenses on your tablet
3. **Run RemarkableSync**:
   ```bash
   # If installed via Homebrew (macOS)
   RemarkableSync

   # If using Python
   python3 RemarkableSync.py
   ```
4. Enter your password when prompted (you can save it for future use)
5. Your notebooks will be backed up to `./remarkable_backup/Notebooks/`
6. PDFs will be created in `./remarkable_backup/PDF/`

That's it! The tool will only sync changed files and convert updated notebooks on subsequent runs.

## Usage

### Unified Command Line Interface

RemarkableSync provides a single entry point with three main commands:

#### Default Command: Sync (Backup + Convert)

The most common workflow - backs up your device and converts only updated notebooks:

```bash
# If installed via Homebrew
RemarkableSync

# If using Python
python3 RemarkableSync.py
```

This will:
1. Connect to your ReMarkable tablet via USB
2. Backup all changed files (including templates)
3. Convert only notebooks that were updated in this backup

#### Individual Commands

**Backup only** (no conversion):
```bash
# Homebrew
RemarkableSync backup

# Python
python3 RemarkableSync.py backup
```

**Convert only** (from existing backup):
```bash
# Homebrew
RemarkableSync convert

# Python
python3 RemarkableSync.py convert
```

**Sync with options**:
```bash
# Force full backup and conversion (ignore sync status)
RemarkableSync sync --force-backup --force-convert

# Skip template backup
RemarkableSync sync --skip-templates

# Verbose output
RemarkableSync sync -v
```

#### Testing and Selective Conversion

**Convert a single notebook** (by name or UUID):
```bash
RemarkableSync convert --notebook "My Notebook"
```

**Convert first N notebooks** (for testing):
```bash
RemarkableSync convert --sample 5
```

**Force convert all notebooks** (ignore sync status):
```bash
RemarkableSync convert --force-all
```

### Command Line Options

**Common Options** (all commands):
- `-d, --backup-dir`: Directory for backups (default: `./remarkable_backup`)
- `-v, --verbose`: Enable debug logging
- `--version`: Show version and repository information

**Connection Options** (backup, sync, obsidian-sync, watch):
- `--host HOST`: Tablet USB IP address (default: `10.11.99.1`)
- `--wifi`: Connect over Wi-Fi instead of USB
- `--wifi-host HOST`: Tablet Wi-Fi IP or hostname (auto-discovered if omitted)

**Backup/Sync Options**:
- `-p, --password`: ReMarkable SSH password (will prompt if not provided)
- `--skip-templates`: Don't backup template files
- `-f, --force` / `--force-backup`: Backup all files (ignore sync status)

**Convert Options**:
- `-o, --output-dir`: Output directory for PDFs (default: `backup_dir/pdfs_final`)
- `-f, --force-all` / `--force-convert`: Convert all notebooks (ignore sync status)
- `-s, --sample N`: Convert only first N notebooks
- `-n, --notebook NAME`: Convert only specific notebook (by UUID or name)

**obsidian-sync Options**:
- `-V, --vault-dir PATH` (required): Root of your Markdown output directory
- `--ai-provider`: AI provider — `claude` or `github` (GitHub Models / GPT-4o)
- `--ai-model`: Override the default model for the chosen provider
- `--ai-api-key`: API key (or set `ANTHROPIC_API_KEY` / `GITHUB_TOKEN` env-vars)
- `--tags`: Comma-separated tags added to every note's frontmatter (default: `remarkable`)
- `--no-images`: Skip embedding page images in notes
- `--skip-backup`, `--skip-convert`: Skip earlier pipeline stages
- `--force-export`: Re-export all notes even if unchanged

**Watch Options**:
- `-i, --interval N`: Minutes between sync attempts (default: 30)
- `-V, --vault-dir PATH`: Markdown output directory — enables obsidian-sync mode
- `--systray/--no-systray`: Show/hide system tray status icon in watch mode (default: enabled)

## Wi-Fi Connection

You can connect to your reMarkable over your local Wi-Fi network instead of USB.

### Prerequisites
- reMarkable tablet and your computer on the same Wi-Fi network
- SSH enabled on the tablet (it is on by default)

### Usage

```bash
# Auto-discover the tablet on the LAN (tries remarkable.local then USB fallback)
RemarkableSync sync --wifi

# Specify the tablet's IP address directly
RemarkableSync sync --wifi --wifi-host 192.168.1.42

# Markdown export over Wi-Fi
RemarkableSync obsidian-sync --vault-dir ~/Notes --wifi --wifi-host 192.168.1.42

# Watch mode with Wi-Fi
RemarkableSync watch --wifi --wifi-host 192.168.1.42 --vault-dir ~/Notes
```

### Finding your tablet's IP address
On the tablet: **Settings → Wi-Fi → (tap your network)** — the IP is shown at the bottom.

> [!TIP]
> Assign a static DHCP lease to your tablet in your router settings so the IP doesn't change.

## Markdown Export

The `obsidian-sync` command runs the full pipeline in one step:

1. **Backup** changed files from the tablet
2. **Convert** updated notebooks to PDF
3. **OCR / AI transcription** of handwriting (optional)
4. **Export** Markdown notes into your output directory

### Quick start

```bash
# Basic export (no AI transcription)
RemarkableSync obsidian-sync --vault-dir ~/Documents/Markdown/MyNotes

# With Claude AI for handwriting recognition
export ANTHROPIC_API_KEY="sk-ant-…"
RemarkableSync obsidian-sync \
    --vault-dir ~/Documents/Markdown/MyNotes \
    --ai-provider claude

# With GitHub Models (GPT-4o)
export GITHUB_TOKEN="ghp_…"
RemarkableSync obsidian-sync \
    --vault-dir ~/Documents/Markdown/MyNotes \
    --ai-provider github

# Wi-Fi + Claude + custom tags
RemarkableSync obsidian-sync \
    --vault-dir ~/Documents/Markdown/MyNotes \
    --wifi --wifi-host 192.168.1.42 \
    --ai-provider claude \
    --tags "remarkable,handwriting,notes"
```

### Generated note format

Each notebook becomes a Markdown file at `output/<folder-path>/<notebook-name>.md`:

```markdown
---
title: My Meeting Notes
source: reMarkable
remarkable_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
folder: Work/Meetings
created: 2025-01-15
tags:
  - remarkable
---

# My Meeting Notes

## Action Items

- **Follow up** with Alice on the Q1 plan
- Schedule review for next Friday

...

---

## Pages

![[My Meeting Notes/page_001.png]]

![[My Meeting Notes/page_002.png]]
```

Page images are stored in `output/<folder-path>/<notebook-name>/page_NNN.png`.

### Incremental export

Re-running `obsidian-sync` is fast — only notebooks whose PDF has changed since the last run are re-exported. Force a full re-export with `--force-export`.

## Periodic Watch Mode

Keep your output directory automatically up to date in the background:

```bash
# Sync every 30 minutes (default), plain backup + PDF only
RemarkableSync watch

# Every 15 minutes with Markdown export
RemarkableSync watch --interval 15 \
    --vault-dir ~/Documents/Markdown/MyNotes \
    --ai-provider claude

# Run as a macOS launchd service or Linux systemd unit for true background operation
```

The watch command uses a file lock (`<backup-dir>/.remarkable_watch.lock`) to prevent
overlapping runs, and applies exponential back-off (up to 1 hour) after consecutive failures.
When available, a system tray icon shows watch status (idle/running/success/failure).

## AI Provider Setup

### Claude (Anthropic)

1. Create an account at https://console.anthropic.com
2. Generate an API key
3. Set the environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-…"
   ```
4. Install the package:
   ```bash
   pip install anthropic
   ```
5. Use `--ai-provider claude` (default model: `claude-3-5-sonnet-20241022`)

### GitHub Models / Copilot (GPT-4o)

1. Generate a GitHub personal access token (PAT) with `models:read` permission at
   https://github.com/settings/tokens
2. Set the environment variable:
   ```bash
   export GITHUB_TOKEN="ghp_…"
   ```
3. Install the OpenAI package:
   ```bash
   pip install openai
   ```
4. Use `--ai-provider github` (default model: `gpt-4o`)

### Offline OCR (pytesseract)

When no AI provider is configured the tool falls back to local Tesseract OCR:

```bash
# macOS
brew install tesseract
pip install pytesseract Pillow

# Ubuntu / Debian
sudo apt install tesseract-ocr
pip install pytesseract Pillow
```

Tesseract is less accurate for handwriting but works entirely offline and for free.

## How It Works

1. **Connection**: Establishes SSH connection to ReMarkable tablet (USB or Wi-Fi)
2. **File Discovery**: Scans `/home/root/.local/share/remarkable/xochitl/` for notebook files
3. **Template Backup**: Downloads template files from `/usr/share/remarkable/templates/`
4. **Incremental Sync**: Compares file metadata (size, modification time, hash) to determine what needs updating
5. **Download**: Uses SCP to efficiently transfer only changed files
6. **PDF Conversion**:
   - Converts .rm files to SVG using rmc (for v6 format)
   - Renders template backgrounds (grids, lines, dots)
   - Merges templates with notebook content
   - Combines all pages into single PDF per notebook
7. **OCR/AI** (obsidian-sync only):
   - Rasterises PDF pages to PNG via pdf2image
   - Sends images to AI provider for handwriting transcription
   - AI post-processes raw text into clean Markdown
8. **Markdown Export** (obsidian-sync only):
   - Writes YAML frontmatter + transcribed text + embedded images
   - Preserves folder hierarchy from the device
   - Tracks exported notebooks by PDF hash for incremental updates
9. **Smart Updates**: Only notebooks updated in the current backup cycle are processed


## File Structure

After backup, your directory will contain:

```
remarkable_backup/
├── Notebooks/                # All notebook files and metadata
│   ├── [uuid].metadata       # Document metadata files
│   ├── [uuid].content        # Document content info
│   └── [uuid]/               # Notebook directories
│       ├── [uuid]-metadata.json  # Page metadata
│       └── *.rm              # Drawing/writing data (v5 or v6 format)
├── Templates/                # Template files from device
│   ├── *.png                 # Template preview images
│   ├── *.template            # Template definition files
│   └── templates.json        # Template metadata
├── PDF/                      # Generated PDF outputs
│   └── [notebook folders with PDFs preserving hierarchy]
├── sync_metadata.json        # Sync state tracking
├── updated_notebooks.txt     # List of notebooks updated in last backup
├── obsidian_export_state.json # Incremental Markdown export state (MD5 hashes)
└── .remarkable_backup.log    # Backup operation log
```

## PDF Conversion Technical Details

RemarkableSync includes a hybrid converter that supports both v5 and v6 .rm file formats:

- **v6 Format** (newer tablets): Uses external `rmc` tool to convert .rm → SVG → PDF
- **v5 Format** (older tablets): Direct Python-based conversion (legacy support)
- **Template Rendering**: Custom renderer applies original device templates with accurate scaling (226 DPI → 72 DPI PDF points)
- **Page Merging**: Uses PyPDF2 to composite template backgrounds with notebook content

### rmc Python Package

For v6 notebook conversion, RemarkableSync uses the `rmc` Python package:
- **Repository**: https://github.com/ricklupton/rmc
- **Installation**: Automatically installed as a dependency with RemarkableSync
- **Note**: This is included in `requirements.txt` and installed via pip

## Incremental Sync Details

The tool maintains a `sync_metadata.json` file that tracks:
- File modification times
- File sizes  
- MD5 hashes of local files
- Last sync timestamps

Files are only downloaded if:
- They don't exist locally
- Remote modification time changed
- Remote file size changed
- Local file hash doesn't match stored hash

## Troubleshooting

### Connection Issues (USB)
- Ensure ReMarkable is connected via USB
- Verify the tablet shows up as network interface
- Try pinging `10.11.99.1`
- Check SSH password from tablet settings

### Connection Issues (Wi-Fi)
- Ensure tablet and computer are on the same Wi-Fi network
- Find the tablet's IP: **Settings → Wi-Fi → tap your network**
- Try `ping remarkable.local` — mDNS must be working on your LAN
- Use `--wifi-host <ip>` to skip discovery if mDNS is not available
- Check that nothing (firewall, router AP isolation) is blocking SSH (port 22) between devices

### AI Provider Issues
- **Claude**: verify `ANTHROPIC_API_KEY` is set; run `pip install anthropic`
- **GitHub Models**: verify `GITHUB_TOKEN` is set with `models:read` scope; run `pip install openai`
- **pytesseract**: install Tesseract system package (`brew install tesseract` or `sudo apt install tesseract-ocr`) then `pip install pytesseract Pillow`
- If AI transcription returns empty results, check API quotas and model availability

### Permission Errors
- Run as administrator on Windows if needed
- Ensure backup directory is writable

### File Access Issues
- Restart ReMarkable tablet if SSH becomes unresponsive
- Check available disk space on both devices

### Watch Mode Issues
- If watch mode says "another sync is already running", delete the stale lock file: `rm <backup-dir>/.remarkable_watch.lock`
- On Windows, `fcntl` is not available — watch mode requires macOS or Linux

## Security Notes

- SSH password is requested interactively (not stored)
- Uses paramiko with auto-add host key policy
- Files are transferred over local USB network (not internet)

## License

This tool is for personal use with your own ReMarkable tablet. Respect ReMarkable's terms of service.
