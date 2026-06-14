"""
Auto-update checker for RemarkableSync.

Checks the GitHub Releases API for newer versions, caching the result
so the check runs at most once per day.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from src.__version__ import __repository__, __version__
from src.config import get_config_dir

# GitHub API endpoint for the latest release
_REPO_API = "https://api.github.com/repos/JeffSteinbok/RemarkableSync/releases/latest"

# Minimum seconds between automatic update checks (24 hours)
_CHECK_INTERVAL = 86400


def _cache_path() -> Path:
    """Return the path to the update-check cache file."""
    return get_config_dir() / "update_check.json"


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse a version string like '2.0.4' or 'v2.0.4' into a tuple of ints."""
    v = version_str.lstrip("v")
    try:
        return tuple(int(p) for p in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def _read_cache() -> dict:
    """Read the cached update-check result."""
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_cache(data: dict) -> None:
    """Write update-check result to the cache file."""
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def _fetch_latest_version() -> Optional[str]:
    """Query GitHub Releases API for the latest release tag.

    Returns the version string (without leading 'v') or None on failure.
    """
    try:
        req = urllib.request.Request(
            _REPO_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"RemarkableSync/{__version__}",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        return None


def check_for_update(force: bool = False) -> Optional[str]:
    """Check whether a newer version is available.

    Args:
        force: If True, ignore the cache and always query GitHub.

    Returns:
        The latest version string if an update is available, or None if
        the current version is up-to-date (or the check was skipped/failed).
    """
    cache = _read_cache()
    now = time.time()

    # Return cached result if still fresh (unless forced)
    if not force:
        last_check = cache.get("last_check", 0)
        if now - last_check < _CHECK_INTERVAL:
            cached_latest = cache.get("latest_version")
            if cached_latest and _parse_version(cached_latest) > _parse_version(__version__):
                return cached_latest
            return None

    latest = _fetch_latest_version()
    if latest is None:
        return None

    # Update cache
    _write_cache({"last_check": now, "latest_version": latest})

    if _parse_version(latest) > _parse_version(__version__):
        return latest

    return None


def format_update_message(latest_version: str) -> str:
    """Return a formatted update notification string."""
    return (
        f"⬆ Update available: v{latest_version} (you have v{__version__})\n"
        f"  pip install --upgrade remarkablesync\n"
        f"  brew upgrade remarkablesync\n"
        f"  Or download from: {__repository__}/releases/latest\n"
    )
