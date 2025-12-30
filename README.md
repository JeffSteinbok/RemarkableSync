# RemarkableSync
[![PyPI version](https://badge.fury.io/py/remarkablesync.svg)](https://badge.fury.io/py/remarkablesync)
[![GitHub](https://img.shields.io/badge/GitHub-RemarkableSync-blue?logo=github)](https://github.com/JeffSteinbok/RemarkableSync)
[![CI](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/ci.yml)
[![Build Executables](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/build-executables.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/build-executables.yml)
[![Release](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/release.yml/badge.svg)](https://github.com/JeffSteinbok/RemarkableSync/actions/workflows/release.yml)

A comprehensive Python toolkit for backing up and converting reMarkable tablet notebooks to PDF with template support and proper folder hierarchy preservation.

> [!IMPORTANT]
> This tool has been tested exclusively on reMarkable 2. Compatibility with reMarkable 1 is not guaranteed.


## Features

### 🔄 Backup & Sync
- **USB Connection**: Connects to reMarkable tablet over USB (10.11.99.1)
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

## Prerequisites

1. **reMarkable Tablet Setup**:
   - Connect your reMarkable tablet to your computer via USB
   - Enable SSH access (it's enabled by default)
   - Get your SSH password from Settings → Help → Copyright and licenses

2. **Python Requirements**:
   - Python 3.11 or higher (required)
   - Required packages (install with `pip install -r requirements.txt`)

3. **External Tools** (for v6 PDF conversion):
   - `rmc` (reMarkable file converter) - Install from https://github.com/ricklupton/rmc
   - Note: rmc is a Rust tool, not a Python package. Install via cargo or download binaries.

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
- Install Python 3.13 and all dependencies
- Install the `rmc` tool for v6 format conversion
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

# Then install rmc separately
pip install rmc
```

**Using a virtual environment** (recommended):
```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install RemarkableSync
pip install remarkablesync
```

**Updating to latest version:**
```bash
pip install --upgrade remarkablesync
```

### Option 3: Pre-built Executables (Windows/macOS)

**For users without Python** or who prefer standalone executables:

1. Download the latest release from the [Releases page](https://github.com/JeffSteinbok/RemarkableSync/releases)
2. Extract the archive:
   - **Windows**: Extract `RemarkableSync-Windows.zip`
   - **macOS**: Extract `RemarkableSync-macOS.zip`
3. Run the executable:
   - **Windows**: `RemarkableSync.exe`
   - **macOS**: `./RemarkableSync/RemarkableSync`

For detailed instructions on building executables yourself, see [BUILD_EXECUTABLES.md](BUILD_EXECUTABLES.md).

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

   # If using pre-built executable
   ./RemarkableSync

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

# If using pre-built executable
./RemarkableSync

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

**Backup/Sync Options**:
- `-p, --password`: ReMarkable SSH password (will prompt if not provided)
- `--skip-templates`: Don't backup template files
- `-f, --force` / `--force-backup`: Backup all files (ignore sync status)

**Convert Options**:
- `-o, --output-dir`: Output directory for PDFs (default: `backup_dir/pdfs_final`)
- `-f, --force-all` / `--force-convert`: Convert all notebooks (ignore sync status)
- `-s, --sample N`: Convert only first N notebooks
- `-n, --notebook NAME`: Convert only specific notebook (by UUID or name)

## How It Works

1. **Connection**: Establishes SSH connection to ReMarkable tablet at 10.11.99.1
2. **File Discovery**: Scans `/home/root/.local/share/remarkable/xochitl/` for notebook files
3. **Template Backup**: Downloads template files from `/usr/share/remarkable/templates/`
4. **Incremental Sync**: Compares file metadata (size, modification time, hash) to determine what needs updating
5. **Download**: Uses SCP to efficiently transfer only changed files
6. **PDF Conversion**:
   - Converts .rm files to SVG using rmc (for v6 format)
   - Renders template backgrounds (grids, lines, dots)
   - Merges templates with notebook content
   - Combines all pages into single PDF per notebook
7. **Smart Updates**: Tracks which notebooks changed and only converts those

## File Structure

After backup, your directory will contain three clean folders:

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
└── .remarkable_backup.log    # Backup operation log
```

## PDF Conversion Technical Details

RemarkableSync includes a hybrid converter that supports both v5 and v6 .rm file formats:

- **v6 Format** (newer tablets): Uses external `rmc` tool to convert .rm → SVG → PDF
- **v5 Format** (older tablets): Direct Python-based conversion (legacy support)
- **Template Rendering**: Custom renderer applies original device templates with accurate scaling (226 DPI → 72 DPI PDF points)
- **Page Merging**: Uses PyPDF2 to composite template backgrounds with notebook content

### External Tool: rmc

For v6 notebook conversion, you'll need the `rmc` tool:
- **Repository**: https://github.com/ricklupton/rmc
- **Installation**: Via Rust cargo or download pre-built binaries
- **Note**: This is NOT a Python package - install separately

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

### Connection Issues
- Ensure ReMarkable is connected via USB
- Verify the tablet shows up as network interface
- Try pinging `10.11.99.1`
- Check SSH password from tablet settings

### Permission Errors
- Run as administrator on Windows if needed
- Ensure backup directory is writable

### File Access Issues
- Restart ReMarkable tablet if SSH becomes unresponsive
- Check available disk space on both devices

## Security Notes

- SSH password is requested interactively (not stored)
- Uses paramiko with auto-add host key policy
- Files are transferred over local USB network (not internet)

## License

This tool is for personal use with your own ReMarkable tablet. Respect ReMarkable's terms of service.
