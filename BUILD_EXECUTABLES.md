# Building Self-Contained Executables

This guide explains how to build self-contained executables for macOS and Windows that can be distributed to non-technical users.

## Overview

The RemarkableSync project provides two main tools:
1. **RemarkableBackup** - Backs up files from your reMarkable tablet via USB
2. **RemarkableConverter** - Converts backed up notebooks to PDF format

Both tools can be packaged as standalone executables that don't require Python installation.

## Prerequisites

### For Building on macOS
- macOS 10.13 or later
- Python 3.7 or higher installed
- Xcode Command Line Tools: `xcode-select --install`

### For Building on Windows
- Windows 10 or later
- Python 3.7 or higher installed from [python.org](https://www.python.org/downloads/)
- Make sure Python is added to PATH during installation

## Building Executables

### macOS Build

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/JeffSteinbok/RemarkableSync.git
   cd RemarkableSync
   ```

2. Run the build script:
   ```bash
   ./build_macos.sh
   ```

3. The executables will be created in the `dist/` directory:
   - `dist/RemarkableBackup` or `dist/RemarkableBackup.app`
   - `dist/RemarkableConverter` or `dist/RemarkableConverter.app`

### Windows Build

1. Clone the repository and navigate to the project directory:
   ```cmd
   git clone https://github.com/JeffSteinbok/RemarkableSync.git
   cd RemarkableSync
   ```

2. Run the build script:
   ```cmd
   build_windows.bat
   ```

3. The executables will be created in the `dist\` directory:
   - `dist\RemarkableBackup.exe`
   - `dist\RemarkableConverter.exe`

## Testing the Executables

### macOS
```bash
# Test the backup tool
./dist/RemarkableBackup --help

# Test the converter
./dist/RemarkableConverter --help
```

### Windows
```cmd
REM Test the backup tool
dist\RemarkableBackup.exe --help

REM Test the converter
dist\RemarkableConverter.exe --help
```

## Distributing to Users

### macOS Distribution

#### Option 1: ZIP Archive
1. Create a ZIP file with the executables:
   ```bash
   cd dist
   zip -r RemarkableSync-macOS.zip RemarkableBackup RemarkableConverter
   ```

2. Share the ZIP file with users

#### Option 2: DMG (Recommended)
1. Create a DMG using Disk Utility or `hdiutil`
2. Include both executables and a README
3. Users can drag the apps to their Applications folder

**First Run Notice for macOS Users:**
- When running the app for the first time, macOS may show a security warning
- Users should go to System Preferences > Security & Privacy
- Click "Open Anyway" to allow the application to run

### Windows Distribution

1. Create a ZIP file with the executables:
   ```cmd
   cd dist
   powershell Compress-Archive -Path RemarkableBackup.exe,RemarkableConverter.exe -DestinationPath RemarkableSync-Windows.zip
   ```

2. Share the ZIP file with users

**First Run Notice for Windows Users:**
- Windows SmartScreen may show a warning on first run
- Click "More info" then "Run anyway" to proceed
- This is normal for unsigned executables

## Usage for End Users

### Using RemarkableBackup

1. Connect your reMarkable tablet via USB
2. Run the executable:
   - **macOS**: Double-click `RemarkableBackup` or run from Terminal
   - **Windows**: Double-click `RemarkableBackup.exe` or run from Command Prompt

3. Basic usage:
   ```bash
   # macOS
   ./RemarkableBackup -d ./my_backup -v
   
   # Windows
   RemarkableBackup.exe -d .\my_backup -v
   ```

4. The tool will:
   - Prompt for your reMarkable SSH password (found in Settings > Help)
   - Connect to your tablet at 10.11.99.1
   - Back up all files to the specified directory

### Using RemarkableConverter

1. After backing up your files, run the converter:
   - **macOS**: Double-click `RemarkableConverter` or run from Terminal
   - **Windows**: Double-click `RemarkableConverter.exe` or run from Command Prompt

2. Basic usage:
   ```bash
   # macOS
   ./RemarkableConverter -d ./my_backup -o ./pdfs -v
   
   # Windows
   RemarkableConverter.exe -d .\my_backup -o .\pdfs -v
   ```

3. The tool will convert all notebooks to PDF format

## Troubleshooting Build Issues

### PyInstaller Not Found
```bash
pip install pyinstaller
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Import Errors
- Check the `.spec` files to ensure all modules are included in `hiddenimports`
- Add any missing modules to the appropriate spec file

### Large Executable Size
- The executables include Python runtime and all dependencies
- Typical size: 40-80 MB per executable
- This is normal for self-contained applications

### macOS Code Signing (Optional)
For professional distribution, consider signing the app:
```bash
codesign --deep --force --sign "Developer ID Application: Your Name" dist/RemarkableBackup.app
```

### Windows Code Signing (Optional)
For professional distribution, consider signing the executable with a code signing certificate.

## Advanced Build Options

### Building for Different Architectures

**macOS Universal Binary:**
```bash
# Build for both Intel and Apple Silicon
pyinstaller --target-arch universal2 remarkable_backup.spec
```

**Windows 32-bit:**
- Use 32-bit Python to build 32-bit executables

### Custom Icons

1. Create icon files:
   - macOS: `.icns` file (512x512 PNG converted using `iconutil`)
   - Windows: `.ico` file (256x256 PNG converted using online tools)

2. Update the spec files:
   ```python
   icon_file = 'path/to/icon.icns'  # macOS
   icon_file = 'path/to/icon.ico'   # Windows
   ```

### Debugging Build Issues

Build with debug mode:
```bash
pyinstaller --debug all remarkable_backup.spec
```

## Clean Up

Remove build artifacts:
```bash
# macOS/Linux
rm -rf build dist *.spec

# Windows
rmdir /s /q build dist
del *.spec
```

## File Size Optimization

The default builds include everything needed to run. To reduce size:

1. Use UPX compression (already enabled in spec files)
2. Exclude unnecessary modules in the spec file
3. Use `--onefile` option for a single executable (slower startup)

## Support

For issues or questions:
- Check the main README.md for usage instructions
- Review troubleshooting_guide.md for common problems
- Open an issue on GitHub: https://github.com/JeffSteinbok/RemarkableSync/issues
