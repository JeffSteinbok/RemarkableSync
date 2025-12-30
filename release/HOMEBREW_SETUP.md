# Homebrew Distribution Setup Guide

This guide walks you through setting up Homebrew distribution for RemarkableSync.

## Prerequisites

- A GitHub account
- Homebrew installed locally for testing
- Write access to your GitHub repositories

## Step 1: Create the Homebrew Tap Repository

1. Go to GitHub and create a new repository named `homebrew-remarkablesync`
   - Repository should be: `https://github.com/jeffsteinbok/homebrew-remarkablesync`
   - Make it public
   - Initialize with a README

2. Create the Formula directory structure:
   ```bash
   mkdir -p Formula
   cp release/remarkablesync.rb Formula/
   git add Formula/remarkablesync.rb
   git commit -m "Add RemarkableSync formula"
   git push
   ```

## Step 2: Set Up GitHub Secrets

To enable automatic formula updates on releases, add these secrets to your main repository:

1. Go to `https://github.com/jeffsteinbok/RemarkableSync/settings/secrets/actions`
2. Add the following secrets:
   - `HOMEBREW_TAP_REPO`: Set to `jeffsteinbok/homebrew-remarkablesync`
   - `HOMEBREW_TAP_TOKEN`: Create a Personal Access Token with `repo` scope
     - Go to https://github.com/settings/tokens
     - Click "Generate new token (classic)"
     - Select `repo` scope
     - Copy the token and add it as the secret

## Step 3: Calculate SHA256 for Current Release

After creating a release, calculate the SHA256 of the tarball:

```bash
# For v1.0.3
curl -L https://github.com/jeffsteinbok/RemarkableSync/archive/refs/tags/v1.0.3.tar.gz -o release.tar.gz
shasum -a 256 release.tar.gz
```

Update the formula with this SHA256:
```ruby
sha256 "ACTUAL_SHA256_HASH_HERE"
```

## Step 4: Test the Formula Locally

Before publishing, test the formula:

```bash
# Tap your local development version
brew tap jeffsteinbok/remarkablesync /path/to/homebrew-remarkablesync

# Install
brew install remarkablesync

# Test
RemarkableSync --help

# Verify rmc is available
rmc --version

# Uninstall when done testing
brew uninstall remarkablesync
brew untap jeffsteinbok/remarkablesync
```

## Step 5: Publish Your Tap

Once the formula works:

```bash
cd /path/to/homebrew-remarkablesync
git push origin main
```

Users can now install with:
```bash
brew tap jeffsteinbok/remarkablesync
brew install remarkablesync
```

## Step 6: Automatic Updates

Once GitHub secrets are configured, the workflow will automatically:
1. Detect when you publish a release
2. Download the release tarball
3. Calculate the SHA256
4. Update the formula in your tap repository
5. Commit and push the changes

## Troubleshooting

### Formula Fails to Install rmc

If `cargo install` fails for rmc, you may need to:
- Ensure Rust is properly installed in the Homebrew environment
- Check rmc's repository for any build issues

### Python Dependencies Fail

If Python dependencies fail:
- Verify all resource URLs and SHA256s are correct
- Check that cairo and pkg-config are properly installed

### Testing Issues

To debug formula installation:
```bash
brew install --verbose --debug remarkablesync
```

## Maintenance

### Updating Python Dependencies

When you update Python dependencies in `requirements.txt`, also update the formula:

1. Get the new package versions and SHA256s:
   ```bash
   pip download <package>==<version>
   shasum -a 256 <downloaded-file>
   ```

2. Update the corresponding `resource` block in the formula

### Updating the Formula Manually

If automatic updates fail:

```bash
cd /path/to/homebrew-remarkablesync
# Edit Formula/remarkablesync.rb
git add Formula/remarkablesync.rb
git commit -m "Update to version X.Y.Z"
git push
```

## Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula Guide](https://docs.brew.sh/Python-for-Formula-Authors)
- [Creating Taps](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
