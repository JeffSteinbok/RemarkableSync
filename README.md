# RemarkableSync

[![GitHub](https://img.shields.io/badge/GitHub-RemarkableSync-blue?logo=github)](https://github.com/JeffSteinbok/RemarkableSync)
[![GitHub release](https://img.shields.io/github/v/release/JeffSteinbok/RemarkableSync)](https://github.com/JeffSteinbok/RemarkableSync/releases)
[![CI](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/ci.yml)
[![Build Executables](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/build-executables.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/build-executables.yml)
[![PyPI version](https://img.shields.io/pypi/v/remarkablesync.svg)](https://pypi.org/project/remarkablesync/)

A comprehensive Python toolkit for backing up reMarkable tablet notebooks, converting them to PDF, and transcribing handwriting to Markdown with AI — over USB or Wi-Fi.

> [!IMPORTANT]
> Tested on reMarkable 2. Compatibility with reMarkable 1 is not guaranteed.

## Features

- **USB & Wi-Fi sync** — connect via cable or wirelessly over your local network
- **Incremental backup** — only downloads files that have changed (tracked by size, mtime, and MD5)
- **PDF conversion** — v5 and v6 .rm formats with template backgrounds, folder hierarchy preserved
- **AI handwriting recognition** — send page images to GitHub Models (GPT-4o) or Claude for transcription
- **Markdown export** — each notebook becomes a `.md` file with YAML frontmatter and embedded page images
- **Watch mode** — automatic periodic sync with system-tray status icon and run-at-startup option
- **Secure credential storage** — SSH password and AI tokens stored in your system keyring

## Quick Start

### 1. Install

```bash
# macOS (Homebrew)
brew tap jeffsteinbok/remarkablesync && brew install remarkablesync

# All platforms (pip)
pip install remarkablesync

# Or download a pre-built executable from the Releases page
```

### 2. Run the configuration wizard

```bash
RemarkableSync config
```

The wizard walks you through:

| Setting | Default |
|---------|---------|
| **Connection mode** | USB or Wi-Fi (wizard can enable Wi-Fi SSH for you) |
| **SSH password** | Saved to system keyring |
| **Backup directory** | `<AppData>/remarkablesync/backup` (internal sync data) |
| **PDF output** | `~/Documents/RemarkableSync/PDF` |
| **Markdown output** | `~/Documents/RemarkableSync/Markdown` |
| **AI provider** | GitHub Models (free) or Claude (requires API key) |
| **AI token** | Stored securely in system keyring |
| **Folders** | Choose which tablet folders to sync (or all) |

> [!TIP]
> Clear any directory field and press Enter to reset it to the default.

### 3. Run watch mode once by hand

```bash
RemarkableSync watch
```

This performs a full sync cycle (backup → PDF → Markdown) and keeps running, syncing every 30 minutes. Verify everything works — check your PDF and Markdown output directories.

### 4. Set it to run at startup

Once you're happy with the output, enable run-at-startup from the system tray icon menu (or via the watch command). RemarkableSync will sync your tablet automatically in the background whenever your computer is on.

> [!TIP]
> **Obsidian users:** Point the Markdown output directory at a folder inside your Obsidian vault. Your handwritten notes appear as searchable Markdown with embedded page images. Pair with [Obsidian OneDrive Sync](https://github.com/JeffSteinbok/obsidian-onedrive) to sync your vault across devices.

## AI Provider Setup

The config wizard handles this interactively, but here's what each provider needs:

### GitHub Models (recommended — free)

The wizard runs a GitHub device-code flow to authenticate. No manual token setup needed.

Alternatively, set a `GITHUB_TOKEN` environment variable with a PAT that has `models:read` scope.

```bash
pip install openai  # required dependency
```

### Claude (Anthropic)

1. Go to https://console.anthropic.com/settings/keys
2. Click **Create Key** and copy it (starts with `sk-ant-api03-...`)
3. Paste it into the config wizard — it's saved in your system keyring

```bash
pip install anthropic  # required dependency
```

Default model: `claude-sonnet-4-6`. Supports both standard API keys and Claude Code OAuth tokens.

### Offline OCR (pytesseract)

When no AI provider is configured, falls back to local Tesseract:

```bash
# macOS
brew install tesseract && pip install pytesseract Pillow

# Ubuntu / Debian
sudo apt install tesseract-ocr && pip install pytesseract Pillow
```

Less accurate for handwriting but works entirely offline and for free.

## Usage

After running `config`, most users only need `watch`. For one-off or scripted use:

```bash
# Default: backup + PDF conversion (uses saved config)
RemarkableSync

# Full pipeline: backup + PDF + AI OCR + Markdown
RemarkableSync md --with-backup --with-pdf

# Individual steps
RemarkableSync backup          # backup only
RemarkableSync convert         # PDF conversion only (from existing backup)
RemarkableSync md              # Markdown export only (from existing PDFs)

# Watch mode (periodic sync)
RemarkableSync watch           # uses saved config for interval, dirs, AI
```

### Command Line Options

All commands read defaults from the saved config. CLI flags override config values.

**Common:**
- `-d, --backup-dir PATH` — backup directory
- `-v, --verbose` — debug logging
- `--version` — version info

**Connection:**
- `--host HOST` — tablet IP (default: `10.11.99.1`)
- `--wifi` — connect over Wi-Fi
- `--wifi-host HOST` — tablet Wi-Fi IP (auto-discovered if omitted)

**Backup:**
- `-p, --password` — SSH password (prompted if not saved)
- `--skip-templates` — don't backup templates
- `--force-backup` — re-download everything

**Convert:**
- `-o, --output-dir PATH` — PDF output directory
- `--force-all` — reconvert all notebooks
- `--sample N` — convert first N notebooks only
- `--notebook NAME` — convert a single notebook

**Markdown (md):**
- `-V, --vault-dir PATH` — Markdown output directory
- `--ai-provider` — `github` or `claude`
- `--ai-model` — override default model
- `--ai-api-key` — API key (prefer keyring or env vars)
- `--tags` — comma-separated frontmatter tags (default: `remarkable`)
- `--no-images` — skip embedding page images
- `--with-backup` / `--with-pdf` — include earlier pipeline stages
- `--force-export` — re-export all notes

**Watch:**
- `-i, --interval N` — minutes between syncs (default: 30)
- `--systray / --no-systray` — system tray icon (default: enabled)

## Wi-Fi Connection

The config wizard can enable Wi-Fi SSH on your tablet automatically via USB. If you prefer to do it manually:

1. Connect tablet via USB and SSH into `10.11.99.1`
2. Run `rm-ssh-over-wlan on`
3. Find the IP: `ip addr show wlan0`
4. Use that IP in the config wizard or `--wifi-host`

> [!TIP]
> Assign a static DHCP lease to your tablet in your router so the IP doesn't change.

## Generated Markdown Format

Each notebook becomes a `.md` file preserving the device folder hierarchy:

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

---

## Pages

![[My Meeting Notes/page_001.png]]

![[My Meeting Notes/page_002.png]]
```

Page images are stored alongside in `<notebook-name>/page_NNN.png`.

## Directory Structure

```
# Internal backup data (AppData by default)
<backup_dir>/
├── Notebooks/              # Raw notebook files and metadata
├── Templates/              # Template files from device
├── PagePDFs/               # Cached per-page PDFs
├── sync_metadata.json      # Sync state
└── remarkablesync.log      # Log file

# PDF output (Documents by default)
<pdf_dir>/
└── [folder hierarchy]/
    └── Notebook Name.pdf

# Markdown output (Documents by default)
<output_dir>/
└── [folder hierarchy]/
    ├── Notebook Name.md
    └── Notebook Name/
        ├── page_001.png
        └── page_002.png
```

## How It Works

1. **Connect** to tablet via SSH (USB or Wi-Fi)
2. **Discover** notebooks in `/home/root/.local/share/remarkable/xochitl/`
3. **Backup** changed files incrementally via SCP
4. **Convert** .rm files → SVG (via rmc) → PDF with template backgrounds
5. **Rasterise** PDF pages to PNG images
6. **Transcribe** handwriting via AI vision model (or pytesseract offline)
7. **Clean up** raw text into structured Markdown via LLM
8. **Export** Markdown files with frontmatter + embedded images

Only changed notebooks are processed on each run.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Can't connect via USB | Verify cable, ping `10.11.99.1`, check SSH password |
| Can't connect via Wi-Fi | Same network? Try `ping remarkable.local` or use `--wifi-host <ip>` |
| AI OCR returns errors | Check API key/token, verify package installed (`anthropic` or `openai`), check rate limits |
| Empty Markdown files | AI provider may have failed — check log file for details |
| Watch lock error | Delete `<backup-dir>/.remarkable_watch.lock` |
| Permission errors | Ensure output directories are writable; run as admin on Windows if needed |

## Security

- SSH password and AI tokens are stored in your **system keyring** (never in plain-text config files)
- All communication is over your local network (USB or LAN) — nothing goes to the internet except AI API calls
- Config file at `<AppData>/remarkablesync/config.json` contains only non-secret settings

## License

This tool is for personal use with your own reMarkable tablet. Respect reMarkable's terms of service.
