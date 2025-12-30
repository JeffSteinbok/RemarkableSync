# Setting Up Homebrew Distribution

This guide explains how to set up automated Homebrew distribution for RemarkableSync.

## Prerequisites

- A GitHub account
- Admin access to the RemarkableSync repository

## One-Time Setup (3 Simple Steps)

### Step 1: Create a Homebrew Tap Repository

1. Go to GitHub and create a new repository named `homebrew-remarkablesync`
   - Repository name MUST start with `homebrew-`
   - Make it public
   - Initialize with a README

2. Clone and set up the repository structure:
   ```bash
   git clone https://github.com/JeffSteinbok/homebrew-remarkablesync.git
   cd homebrew-remarkablesync
   mkdir Formula
   git add Formula
   git commit -m "Add Formula directory"
   git push
   ```

### Step 2: Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "Homebrew Tap Update"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
5. Click "Generate token" and **copy the token**

### Step 3: Add Token to Repository Secrets

1. Go to RemarkableSync repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `HOMEBREW_TAP_TOKEN`
4. Value: [paste your token from Step 2]
5. Click "Add secret"

## That's It! 🎉

Once you complete the above setup, everything is automated:

### What Happens Automatically

When you trigger a release workflow:

1. **Version bump** - Updates version in code
2. **Run tests** - Ensures everything works
3. **Build executables** - Creates Windows and macOS binaries
4. **Create GitHub release** - Publishes release with executables
5. **Update Homebrew formula** ⭐ NEW ⭐
   - Downloads the release tarball
   - Calculates SHA256 hash
   - Updates formula version and hash
   - Commits and pushes to `homebrew-remarkablesync`

No manual steps required!

## Installation for Users

Once set up, users can install RemarkableSync with:

```bash
# Add your tap
brew tap jeffsteinbok/remarkablesync

# Install RemarkableSync
brew install remarkablesync

# Or in one command
brew install jeffsteinbok/remarkablesync/remarkablesync
```

## Testing the Formula

Before your first release, you can test the formula locally:

```bash
brew install --build-from-source ./release/remarkablesync.rb
brew test remarkablesync
brew audit --strict remarkablesync
```

## Troubleshooting

### "Formula not found" error
- Make sure the `homebrew-remarkablesync` repository exists and is public
- Check that the Formula directory exists
- Verify the formula file is at `Formula/remarkablesync.rb`

### Homebrew update fails in workflow
- Verify `HOMEBREW_TAP_TOKEN` secret is set correctly
- Check token has `repo` scope permissions
- Ensure token hasn't expired

### Formula installation fails for users
- Test the formula locally first
- Check that all dependencies are correct
- Verify the SHA256 hash matches the tarball

## Benefits of This Setup

1. ✅ **Fully Automated** - No manual formula updates
2. ✅ **No Gatekeeper Issues** - Homebrew is trusted by macOS
3. ✅ **Dependency Management** - Homebrew handles Python, Cairo, etc.
4. ✅ **Easy Updates** - Users run `brew upgrade`
5. ✅ **No Apple Developer Account** - No $99/year fee or code signing

## Alternative: Submit to homebrew-core

Once RemarkableSync gains popularity, you can submit to the official homebrew-core repository:
- Must have 75+ GitHub stars or 30+ forks
- Follow homebrew-core guidelines
- Submit PR to https://github.com/Homebrew/homebrew-core

Users would then install with just: `brew install remarkablesync`
