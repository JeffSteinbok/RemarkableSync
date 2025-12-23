# Release Checklist

Use this checklist when creating a new release of RemarkableSync.

## Pre-Release Steps

- [ ] Test backup functionality with a real reMarkable tablet
- [ ] Test PDF conversion on sample notebooks
- [ ] Update version numbers in relevant files
- [ ] Update CHANGELOG.md with new features and fixes
- [ ] Review and update documentation if needed

## Creating the Release

1. **Create a Git Tag**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

2. **Create GitHub Release**
   - Go to: https://github.com/JeffSteinbok/RemarkableSync/releases/new
   - Select the tag you just created
   - Release title: `RemarkableSync v1.0.0`
   - Add release notes (see template below)
   - Click "Publish release"

3. **Wait for Automated Builds**
   - GitHub Actions will automatically build executables
   - Check the "Actions" tab to monitor progress
   - Builds typically complete in 5-10 minutes

4. **Verify Release Artifacts**
   - Download each platform package
   - Test at least one executable per platform
   - Verify QUICK_START.md and README.md are included

## Release Notes Template

```markdown
## RemarkableSync v1.0.0

### What's New
- New feature 1
- New feature 2
- Improvement to existing feature

### Bug Fixes
- Fixed issue #123
- Fixed problem with...

### Platform Support
This release includes pre-built executables for:
- ✅ Windows 10/11 (64-bit)
- ✅ macOS 10.13+ (Intel and Apple Silicon)
- ✅ Linux (Ubuntu 20.04+)

### Installation

**For Non-Technical Users:**
1. Download the appropriate package for your platform:
   - Windows: `RemarkableSync-Windows.zip`
   - macOS: `RemarkableSync-macOS.zip`
   - Linux: `RemarkableSync-Linux.tar.gz`
2. Extract the archive
3. Follow the instructions in `QUICK_START.md`

**For Developers:**
See [BUILD_EXECUTABLES.md](BUILD_EXECUTABLES.md) for build instructions.

### Requirements
- reMarkable tablet (v1 or v2)
- USB connection to computer
- SSH password from tablet (Settings → Help)

### Known Issues
- List any known limitations or issues

### Support
- [Documentation](https://github.com/JeffSteinbok/RemarkableSync)
- [Report Issues](https://github.com/JeffSteinbok/RemarkableSync/issues)
```

## Post-Release Steps

- [ ] Announce release on relevant platforms
- [ ] Monitor issue tracker for bug reports
- [ ] Update project documentation if needed

## Troubleshooting Failed Builds

If automated builds fail:

1. Check GitHub Actions logs for error messages
2. Common issues:
   - Missing dependencies in requirements.txt
   - Import errors in spec files
   - Platform-specific path issues
3. Fix issues and create a new patch release

## Manual Build Release (Fallback)

If automated builds are unavailable:

1. Build on each platform manually:
   ```bash
   # macOS
   ./build_macos.sh
   
   # Windows
   build_windows.bat
   
   # Linux
   ./build_macos.sh  # Same script works
   ```

2. Create distribution packages:
   ```bash
   # Package for distribution
   zip -r RemarkableSync-macOS.zip dist/ QUICK_START.md README.md
   ```

3. Upload manually to GitHub release

## Version Numbering

Follow semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

Examples:
- `v1.0.0` - Initial stable release
- `v1.1.0` - Added new converter support
- `v1.1.1` - Fixed connection bug
