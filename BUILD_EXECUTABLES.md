# Building Self-Contained Executables

This guide explains how to build self-contained executables for macOS and Windows that can be distributed to non-technical users.

## Overview

The RemarkableSync project provides a unified command-line tool:
- **RemarkableSync** - Backs up files from your reMarkable tablet via USB and converts notebooks to PDF with template support

The tool can be packaged as a standalone executable that doesn't require Python installation.

## Automated Builds (Recommended for Releases)

The project includes GitHub Actions workflows that automate the entire release process, including version bumping and building executables for all platforms.

### Automated Release with Version Bump (Easiest)

1. Go to "Actions" tab in your GitHub repository
2. Select "Create Release" workflow
3. Click "Run workflow"
4. Choose version bump type:
   - `patch` (1.0.0 → 1.0.1) for bug fixes
   - `minor` (1.0.0 → 1.1.0) for new features
   - `major` (1.0.0 → 2.0.0) for breaking changes
5. Click "Run workflow"

**What happens automatically:**
- Version in `src/__version__.py` is updated and committed
- Git tag is created
- GitHub Release is created
- Executables are built for all platforms
- Build artifacts are uploaded to the release

### Manual Release Creation with Automated Builds

If you prefer to manage versions manually:

1. Update version in `src/__version__.py`
2. Create a new tag (e.g., `v1.0.0`)
3. Push the tag: `git push origin v1.0.0`
4. Create a GitHub Release with that tag
5. The build workflow automatically triggers
6. Download the artifacts from the release page:
   - `RemarkableSync-Windows.zip`
   - `RemarkableSync-macOS.zip`
   - `RemarkableSync-Linux.tar.gz`

### Manual Build Workflow Trigger

You can also trigger just the build workflow manually:
1. Go to "Actions" tab in your repository
2. Select "Build Executables" workflow
3. Click "Run workflow"
4. Download artifacts from the workflow run

## Manual Local Builds

If you prefer to build locally or need custom modifications, follow these instructions.

### Prerequisites

#### For Building on macOS
- macOS 10.13 or later
- Python 3.7 or higher installed
- Xcode Command Line Tools: `xcode-select --install`

#### For Building on Windows
- Windows 10 or later
- Python 3.7 or higher installed from [python.org](https://www.python.org/downloads/)
- Make sure Python is added to PATH during installation

### Building Executables

#### macOS Build

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/JeffSteinbok/RemarkableSync.git
   cd RemarkableSync
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. Build the executable:
   ```bash
   pyinstaller RemarkableSync.spec
   ```

4. The executable will be created in the `dist/` directory:
   - `dist/RemarkableSync` or `dist/RemarkableSync.app`

#### Windows Build

1. Clone the repository and navigate to the project directory:
   ```cmd
   git clone https://github.com/JeffSteinbok/RemarkableSync.git
   cd RemarkableSync
   ```

2. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. Build the executable:
   ```cmd
   pyinstaller RemarkableSync.spec
   ```

4. The executable will be created in the `dist\` directory:
   - `dist\RemarkableSync.exe`

## Testing the Executables

### macOS
```bash
# Show version
./dist/RemarkableSync --version

# Show help
./dist/RemarkableSync --help

# Test individual commands
./dist/RemarkableSync backup --help
./dist/RemarkableSync convert --help
./dist/RemarkableSync sync --help
```

### Windows
```cmd
REM Show version
dist\RemarkableSync.exe --version

REM Show help
dist\RemarkableSync.exe --help

REM Test individual commands
dist\RemarkableSync.exe backup --help
dist\RemarkableSync.exe convert --help
dist\RemarkableSync.exe sync --help
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
- Typical size: 15-25 MB total (both executables combined)
  - RemarkableBackup: ~15 MB
  - RemarkableConverter: ~9 MB
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
