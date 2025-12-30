#!/bin/bash
# Build script for creating macOS executables
# This script builds self-contained executables for macOS using PyInstaller

set -e  # Exit on error

echo "=================================================="
echo "RemarkableSync - macOS Build Script"
echo "=================================================="
echo ""

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "ERROR: PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Check if dependencies are installed
echo "Installing dependencies..."
pip install -r requirements.txt

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build dist
rm -rf *.app

echo ""
echo "Building RemarkableBackup..."
pyinstaller --clean remarkable_backup.spec

echo ""
echo "Building RemarkableConverter..."
pyinstaller --clean hybrid_converter.spec

echo ""
echo "=================================================="
echo "Build Complete!"
echo "=================================================="
echo ""
echo "Executables created:"
if [ -d "dist/RemarkableBackup.app" ]; then
    echo "  - dist/RemarkableBackup.app (macOS app bundle)"
    echo "    Size: $(du -sh dist/RemarkableBackup.app | cut -f1)"
fi
if [ -f "dist/RemarkableBackup" ]; then
    echo "  - dist/RemarkableBackup (standalone executable)"
    echo "    Size: $(du -sh dist/RemarkableBackup | cut -f1)"
fi
if [ -d "dist/RemarkableConverter.app" ]; then
    echo "  - dist/RemarkableConverter.app (macOS app bundle)"
    echo "    Size: $(du -sh dist/RemarkableConverter.app | cut -f1)"
fi
if [ -f "dist/RemarkableConverter" ]; then
    echo "  - dist/RemarkableConverter (standalone executable)"
    echo "    Size: $(du -sh dist/RemarkableConverter | cut -f1)"
fi

echo ""
echo "To distribute:"
echo "  1. Test the executables: ./dist/RemarkableBackup --help"
echo "  2. Create a DMG or ZIP file with the executables"
echo "  3. Share with users"
echo ""
echo "Note: Users may need to allow the app in System Preferences > Security & Privacy"
