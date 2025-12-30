# RemarkableSync - Quick Start Guide

Welcome! This package contains an easy-to-use tool for backing up your reMarkable tablet and converting notebooks to PDF with template support.

## What's Included

- **RemarkableSync** (or RemarkableSync.exe on Windows) - Unified tool for backup and conversion

## Before You Start

1. **Connect your reMarkable tablet** to your computer via USB cable
2. **Get your SSH password** from your tablet:
   - Tap Settings → Help → Copyright and licenses
   - Look for "GPLv3 Compliance" section - your password is shown there

## Quick Start: Backup and Convert in One Step

The simplest way to use RemarkableSync is to run it with no arguments - this backs up your tablet and converts only updated notebooks:

### On macOS/Linux:
1. Open Terminal
2. Navigate to where you extracted these files
3. Run:
   ```bash
   ./RemarkableSync
   ```

### On Windows:
1. Open Command Prompt or PowerShell
2. Navigate to where you extracted these files
3. Run:
   ```cmd
   RemarkableSync.exe
   ```

### What happens:
- You'll be asked for your reMarkable SSH password (from step "Before You Start" above)
- The tool connects to your tablet at 10.11.99.1
- All changed files are backed up (including templates) to `./remarkable_backup`
- Only notebooks updated in this backup are converted to PDF
- PDFs are saved in `./remarkable_backup/pdfs_final`
- Folder structure from your tablet is preserved
- Template backgrounds (grids, lines, etc.) are applied to PDFs

## Alternative: Individual Commands

You can also run backup and conversion separately:

### Backup Only:
```bash
# macOS/Linux
./RemarkableSync backup -d my_backup -v

# Windows
RemarkableSync.exe backup -d my_backup -v
```

### Convert Only (from existing backup):
```bash
# macOS/Linux
./RemarkableSync convert -d my_backup -v

# Windows
RemarkableSync.exe convert -d my_backup -v
```

## Common Options

### All Commands
- `-d, --backup-dir` - Where to save/read backup (default: `./remarkable_backup`)
- `-v, --verbose` - Verbose mode (shows detailed progress)
- `--version` - Show version information

### Backup/Sync Specific
- `-p, --password` - SSH password (will prompt if not provided)
- `--skip-templates` - Don't backup template files
- `-f, --force` or `--force-backup` - Backup all files (ignore sync status)

### Convert Specific
- `-o, --output-dir` - Where to save PDFs (default: `backup_dir/pdfs_final`)
- `-s, --sample N` - Convert only first N notebooks (for testing)
- `-n, --notebook NAME` - Convert specific notebook by name or UUID
- `-f, --force-all` or `--force-convert` - Convert all notebooks (ignore sync status)

## Examples

### Force full backup and conversion (ignore what's changed):
```bash
# macOS/Linux
./RemarkableSync sync --force-backup --force-convert -v

# Windows
RemarkableSync.exe sync --force-backup --force-convert -v
```

### Convert just a few notebooks for testing:
```bash
# macOS/Linux
./RemarkableSync convert --sample 5 -v

# Windows
RemarkableSync.exe convert --sample 5 -v
```

### Convert a specific notebook:
```bash
# macOS/Linux
./RemarkableSync convert --notebook "My Journal" -v

# Windows
RemarkableSync.exe convert --notebook "My Journal" -v
```

### Skip template backup (faster, but no template backgrounds in PDFs):
```bash
# macOS/Linux
./RemarkableSync sync --skip-templates -v

# Windows
RemarkableSync.exe sync --skip-templates -v
```

## Troubleshooting

### "Cannot connect to tablet"
- Make sure tablet is connected via USB
- Check that you can ping 10.11.99.1
- Verify SSH is enabled (it's on by default)

### "Permission denied"
- Check you entered the correct SSH password
- Get password from: Settings → Help → Copyright and licenses on tablet

### macOS Security Warning
- Right-click the app and select "Open"
- Or go to System Preferences → Security & Privacy → General
- Click "Open Anyway" for the blocked app

### Windows Security Warning
- Click "More info" in the SmartScreen warning
- Then click "Run anyway"
- This is normal for unsigned executables

### "No notebooks found"
- Make sure you ran the backup first
- Check that the backup directory contains UUID folders and .metadata files
- Verify files were actually backed up

### "Template rendering issues"
- Templates are automatically backed up by default
- If PDFs lack backgrounds, run with `--force-backup` to refresh templates
- Template files are stored in `backup_dir/templates/`

## Tips

- **Incremental sync**: Just run `./RemarkableSync` again - it only syncs changed files and converts updated notebooks
- **Test first**: Use `--sample 5` to convert just 5 notebooks as a test
- **Large tablets**: First backup may take several minutes
- **Regular backups**: Run regularly to keep your data safe
- **Template backgrounds**: Templates (grids, lines, dots) are automatically applied to PDFs

## Need More Help?

- Check the full documentation at: https://github.com/JeffSteinbok/RemarkableSync
- Open an issue for bugs or questions
- See BUILD_EXECUTABLES.md for advanced build options

## Safety Notes

- Your data stays on your computer (no internet connection needed)
- SSH password is never stored (you enter it each time)
- Original tablet files are never modified
- Backups are complete copies of your tablet data

---

**Enjoy your backups! 📚✨**
