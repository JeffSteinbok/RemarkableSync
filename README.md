# RemarkableSync

A comprehensive Python toolkit for backing up and converting reMarkable tablet notebooks to PDF with proper folder hierarchy preservation.

## Features

### 🔄 Backup & Sync
- **USB Connection**: Connects to reMarkable tablet over USB (10.11.99.1)
- **Incremental Sync**: Only downloads files that have changed since last backup
- **Complete Backup**: Backs up all notebooks, documents, and metadata
- **File Integrity**: MD5 hash verification for synced files

### 📄 PDF Conversion
- **Hybrid Converter**: Supports both v5 and v6 .rm file formats
- **SVG Pipeline**: Uses rmc → SVG → PDF conversion for high quality output
- **Folder Hierarchy**: Recreates original device folder structure in output
- **Single PDF per Notebook**: Merges all pages into one PDF file per notebook
- **Progress Tracking**: Visual progress bars and detailed logging

## Prerequisites

1. **reMarkable Tablet Setup**:
   - Connect your reMarkable tablet to your computer via USB
   - Enable SSH access (it's enabled by default)
   - Get your SSH password from Settings → Help → Copyright and licenses

2. **Python Requirements**:
   - Python 3.7 or higher
   - Required packages (install with `pip install -r requirements.txt`)

3. **External Tools** (for PDF conversion):
   - `rmc` (reMarkable file converter) - install via `pip install rmc`
   - `rmrl` (optional, for v5 file support) - install via `pip install rmrl`

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/RemarkableSync.git
   cd RemarkableSync
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Backup Your Device
```bash
python remarkable_backup.py
```

### 2. Convert to PDFs
```bash
# Basic conversion
python hybrid_converter.py -d remarkable_backup -o output_pdfs

# Convert with folder structure preservation
python hybrid_converter.py -d remarkable_backup -o output_pdfs --sample 10 --verbose

# Full conversion of all notebooks
python hybrid_converter.py -d remarkable_backup -o output_pdfs --verbose
```

### Command Line Options

**Backup (`remarkable_backup.py`)**:
- `--backup-dir`: Custom backup directory
- `--verbose`: Detailed logging

**Converter (`hybrid_converter.py`)**:
- `-d, --data-dir`: Input backup directory (required)
- `-o, --output-dir`: Output directory for PDFs (required)  
- `-s, --sample`: Convert only N notebooks for testing
- `-v, --verbose`: Enable verbose logging

## How It Works

1. **Connection**: Establishes SSH connection to ReMarkable tablet at 10.11.99.1
2. **File Discovery**: Scans `/home/root/.local/share/remarkable/xochitl/` for all files
3. **Incremental Sync**: Compares file metadata (size, modification time, hash) to determine what needs updating
4. **Download**: Uses SCP to efficiently transfer only changed files
5. **PDF Processing**: Identifies notebooks and prepares metadata for PDF conversion

## File Structure

After backup, your directory will contain:

```
remarkable_backup/
├── files/                 # Raw ReMarkable files
│   ├── *.metadata        # Document metadata
│   ├── *.content         # Document content info
│   ├── [uuid]/           # Notebook directories
│   │   ├── *.rm          # Drawing/writing data
│   │   └── *.json        # Page metadata
├── pdfs/                 # PDF outputs (metadata files)
├── sync_metadata.json    # Sync state tracking
└── logs/                 # Application logs
```

## PDF Conversion

This tool creates the file structure needed for PDF conversion but doesn't include the conversion engines. For actual PDF conversion, you can integrate:

- **rmc**: Modern tool for v6 .rm files - `https://github.com/ricklupton/rmc`
- **rmscene**: Python library for reading .rm files - `https://github.com/ricklupton/rmscene`
- **rm2pdf**: Legacy tool for older formats - `https://github.com/rorycl/rm2pdf`

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