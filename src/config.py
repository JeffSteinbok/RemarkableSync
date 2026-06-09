"""
RemarkableSync configuration management.

Handles loading, saving, and interactive editing of user configuration.
Config is stored as JSON at ~/.config/remarkablesync/config.json (Linux/macOS)
or %APPDATA%/remarkablesync/config.json (Windows).
"""

import json
import platform
from pathlib import Path
from typing import Any, Dict


def get_config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "remarkablesync"


def get_config_path() -> Path:
    """Return the full path to the config file."""
    return get_config_dir() / "config.json"


# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "connection_mode": "usb",
    "wifi_host": "",
    "password": "",
    "folders": [],
    "sync_actions": ["pdf"],
    "ocr_enabled": False,
    "ocr_output_dir": "",
    "output_dir": "",
    "ai_provider": "github",
}

# All available sync actions
SYNC_ACTIONS = [
    ("backup", "Backup tablet files"),
    ("pdf", "PDF Conversion"),
    ("ocr", "AI Handwriting OCR & MD Export"),
]


def load_config() -> Dict[str, Any]:
    """Load config from disk, returning defaults if file doesn't exist."""
    path = get_config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "output_dir" not in data and "vault_dir" in data:
            data["output_dir"] = data["vault_dir"]
        data.pop("vault_dir", None)

        # Merge with defaults so new keys are always present
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]) -> Path:
    """Save config to disk. Returns the path written."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return path
