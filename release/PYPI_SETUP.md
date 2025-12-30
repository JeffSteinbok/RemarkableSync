# PyPI Publishing Setup Guide

This guide walks you through setting up automated PyPI publishing for RemarkableSync.

## Prerequisites

- A PyPI account
- GitHub repository with admin access
- Your package code ready to publish

## Step 1: Create PyPI Account

1. Go to [pypi.org](https://pypi.org/account/register/) and create an account
2. Verify your email address

## Step 2: Generate PyPI API Token

1. Log in to PyPI
2. Go to [Account Settings → API tokens](https://pypi.org/manage/account/token/)
3. Click "Add API token"
4. Enter a token name (e.g., "GitHub Actions - RemarkableSync")
5. Set scope to "Entire account" (or specific project after first publish)
6. Click "Add token"
7. **IMPORTANT**: Copy the token immediately (starts with `pypi-`)
   - You won't be able to see it again!
   - Format: `pypi-AgEIcHlwaS5vcmc...`

## Step 3: Add Token to GitHub Secrets

1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `PYPI_API_TOKEN`
5. Value: Paste the token you copied (including `pypi-` prefix)
6. Click "Add secret"

## Step 4: Test Locally (Optional)

Before publishing via GitHub Actions, you can test locally:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Check the build
twine check dist/*

# Test upload to TestPyPI (optional)
twine upload --repository testpypi dist/*

# Upload to PyPI (do this manually first time)
twine upload dist/*
```

## Step 5: Publish Your First Release

The GitHub Action will automatically run when you publish a release:

1. Create a new release on GitHub
2. The `publish-pypi.yml` workflow will automatically:
   - Build your package
   - Upload to PyPI
   - Make it available via `pip install remarkablesync`

## Verifying Publication

After publishing, verify your package:

1. Go to https://pypi.org/project/remarkablesync/
2. Check that the version is correct
3. Test installation:
   ```bash
   pip install remarkablesync
   ```

## Updating Versions

The version is automatically read from `src/__version__.py`. When you create a new release:

1. The `release.yml` workflow bumps the version
2. Creates a GitHub release
3. The `publish-pypi.yml` workflow publishes to PyPI

## Troubleshooting

### Error: "403 Forbidden"
- Check that your API token is correct
- Ensure the token has the right scope
- Verify the package name isn't taken

### Error: "Package already exists"
- You're trying to upload the same version twice
- Bump the version in `src/__version__.py`
- PyPI doesn't allow overwriting versions

### Error: "Invalid distribution"
- Check that `setup.py` is correct
- Run `twine check dist/*` locally
- Ensure all required fields are filled

## Package Information

- **Package name**: `remarkablesync`
- **PyPI URL**: https://pypi.org/project/remarkablesync/
- **Installation**: `pip install remarkablesync`

## Workflow Files

- `.github/workflows/publish-pypi.yml` - Automated PyPI publishing
- `setup.py` - Package configuration
- `requirements.txt` - Dependencies

## Notes

- PyPI doesn't allow deleting/overwriting versions
- Always test with TestPyPI first if unsure
- Keep your API token secret and rotate periodically
- The workflow only runs on published releases, not drafts
