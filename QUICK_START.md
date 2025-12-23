# RemarkableSync - Quick Start Guide

Welcome! This package contains easy-to-use tools for backing up your reMarkable tablet and converting notebooks to PDF.

## What's Included

- **RemarkableBackup** (or RemarkableBackup.exe on Windows) - Backs up your tablet files
- **RemarkableConverter** (or RemarkableConverter.exe on Windows) - Converts notebooks to PDF

## Before You Start

1. **Connect your reMarkable tablet** to your computer via USB cable
2. **Get your SSH password** from your tablet:
   - Tap Settings → Help → Copyright and licenses
   - Look for "GPLv3 Compliance" section - your password is shown there

## Step 1: Backup Your Tablet

### On macOS:
1. Open Terminal (Applications → Utilities → Terminal)
2. Navigate to where you extracted these files
3. Run:
   ```bash
   ./RemarkableBackup -d my_backup -v
   ```

### On Windows:
1. Open Command Prompt or PowerShell
2. Navigate to where you extracted these files
3. Run:
   ```cmd
   RemarkableBackup.exe -d my_backup -v
   ```

### What happens:
- You'll be asked for your reMarkable SSH password (from step 2 above)
- The tool connects to your tablet at 10.11.99.1
- All files are backed up to the `my_backup` folder
- Progress is shown in the terminal

## Step 2: Convert to PDFs

After backing up, convert your notebooks to PDF:

### On macOS:
```bash
./RemarkableConverter -d my_backup -o pdfs -v
```

### On Windows:
```cmd
RemarkableConverter.exe -d my_backup -o pdfs -v
```

### What happens:
- Reads notebooks from your backup
- Converts each notebook to a single PDF file
- PDFs are saved in the `pdfs` folder
- Folder structure from your tablet is preserved

## Common Options

### Backup Options
- `-d` - Where to save backup (default: `./remarkable_backup`)
- `-v` - Verbose mode (shows detailed progress)
- `-c` - Auto-convert to PDF after backup

### Converter Options
- `-d` - Where backup files are located
- `-o` - Where to save PDF files
- `-v` - Verbose mode (shows detailed progress)
- `-s 10` - Convert only first 10 notebooks (for testing)

## Examples

### Full backup and auto-convert:
```bash
# macOS
./RemarkableBackup -d my_backup -c -v

# Windows
RemarkableBackup.exe -d my_backup -c -v
```

### Convert just a few notebooks for testing:
```bash
# macOS
./RemarkableConverter -d my_backup -o test_pdfs -s 5 -v

# Windows
RemarkableConverter.exe -d my_backup -o test_pdfs -s 5 -v
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
- Check that the backup directory contains a `files` folder
- Verify files were actually backed up

## Tips

- **Incremental backups**: Run backup again to sync only changed files
- **Test first**: Use `-s 5` to convert just 5 notebooks as a test
- **Large tablets**: First backup may take several minutes
- **Regular backups**: Run backup regularly to keep your data safe

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
