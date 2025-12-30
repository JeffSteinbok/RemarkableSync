## Homebrew Setup - Quick Reference

### What I've Done For You ✅

1. **Created an improved Homebrew formula** (`release/remarkablesync.rb`):
   - Includes all Python dependencies with SHA256s
   - Installs `rmc` (Rust tool) automatically
   - Updated to version 1.0.3
   - Proper dependency management

2. **Created GitHub Actions workflow** (`.github/workflows/update-homebrew.yml`):
   - Automatically updates formula on new releases
   - Calculates SHA256 automatically
   - Pushes to tap repository

3. **Created setup script** (`release/setup-tap.sh`):
   - Automates initial tap setup
   - Calculates SHA256 for current release
   - Copies formula to tap repo

### What You Need To Do 📝

#### 1. Clone Your Tap Repository

```bash
cd ~/Documents/GitHub  # or wherever you keep repos
git clone https://github.com/jeffsteinbok/homebrew-remarkablesync.git
```

#### 2. Run the Setup Script

```bash
cd RemarkableSync
./release/setup-tap.sh ../homebrew-remarkablesync
```

This will:
- Create the `Formula/` directory
- Copy the formula file
- Calculate the SHA256 for v1.0.3
- Update the formula with the real SHA256
- Commit the changes

#### 3. Push to GitHub

```bash
cd ../homebrew-remarkablesync
git push origin main
```

#### 4. Test It Locally

```bash
# Tap your repository
brew tap jeffsteinbok/remarkablesync

# Install
brew install remarkablesync

# Test
RemarkableSync --help
rmc --version
```

#### 5. Set Up GitHub Secrets (For Auto-Updates)

Go to: https://github.com/jeffsteinbok/RemarkableSync/settings/secrets/actions

Add two secrets:
- **HOMEBREW_TAP_REPO**: `jeffsteinbok/homebrew-remarkablesync`
- **HOMEBREW_TAP_TOKEN**: [Create a personal access token with `repo` scope]
  - Go to: https://github.com/settings/tokens
  - Generate new token (classic)
  - Select `repo` scope
  - Copy and paste as secret

### Now What? 🎉

Users can install RemarkableSync with:

```bash
brew tap jeffsteinbok/remarkablesync
brew install remarkablesync
```

Or in one command:

```bash
brew install jeffsteinbok/remarkablesync/remarkablesync
```

### Future Releases

When you create a new release, the GitHub Actions workflow will automatically:
1. Download the release tarball
2. Calculate its SHA256
3. Update the formula in your tap
4. Push the changes

You don't need to do anything manually!

### Troubleshooting

If the formula doesn't work:

```bash
# Install with verbose output
brew install --verbose --debug remarkablesync

# Check Homebrew logs
cat ~/Library/Logs/Homebrew/remarkablesync/
```

Common issues:
- **rmc install fails**: Ensure Rust/Cargo is available in Homebrew's build environment
- **Python deps fail**: Check that cairo and pkg-config are installed
- **Permission errors**: Make sure your tap repo is public

### Files Created

- `release/remarkablesync.rb` - The Homebrew formula
- `release/setup-tap.sh` - One-time setup script
- `release/HOMEBREW_SETUP.md` - Detailed setup guide
- `.github/workflows/update-homebrew.yml` - Auto-update workflow
