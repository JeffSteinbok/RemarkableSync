#!/bin/bash
# Script to set up the Homebrew tap repository

set -e

echo "RemarkableSync Homebrew Tap Setup"
echo "=================================="
echo ""

# Get the script directory and main repo path BEFORE changing directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_REPO="$SCRIPT_DIR/.."

# Check if tap repo directory is provided
TAP_DIR="${1:-../homebrew-remarkablesync}"

if [ ! -d "$TAP_DIR" ]; then
    echo "Error: Tap directory not found: $TAP_DIR"
    echo "Usage: $0 [path-to-tap-repo]"
    echo "Example: $0 ../homebrew-remarkablesync"
    exit 1
fi

cd "$TAP_DIR"

echo "Setting up tap repository at: $(pwd)"
echo ""

# Create Formula directory if it doesn't exist
if [ ! -d "Formula" ]; then
    echo "Creating Formula directory..."
    mkdir -p Formula
fi

# Copy the formula
echo "Copying formula file..."
cp "$MAIN_REPO/release/remarkablesync.rb" Formula/

# Calculate SHA256 for v1.0.3
echo ""
echo "Calculating SHA256 for v1.0.3 release..."
TARBALL_URL="https://github.com/JeffSteinbok/RemarkableSync/archive/refs/tags/v1.0.3.tar.gz"
curl -sL "$TARBALL_URL" -o /tmp/remarkablesync-release.tar.gz
SHA256=$(shasum -a 256 /tmp/remarkablesync-release.tar.gz | awk '{print $1}')
rm /tmp/remarkablesync-release.tar.gz

echo "SHA256: $SHA256"

# Update the formula with the real SHA256
sed -i '' "s/REPLACE_WITH_ACTUAL_SHA256/$SHA256/" Formula/remarkablesync.rb

# Git operations
echo ""
echo "Committing formula..."
git add Formula/remarkablesync.rb
git commit -m "Add RemarkableSync formula v1.0.3" || echo "Already committed"

echo ""
echo "✅ Tap repository is ready!"
echo ""
echo "Next steps:"
echo "1. Review the formula: cat Formula/remarkablesync.rb"
echo "2. Push to GitHub: git push origin main"
echo "3. Test locally: brew tap jeffsteinbok/remarkablesync $(pwd)"
echo "4. Install: brew install remarkablesync"
echo ""
