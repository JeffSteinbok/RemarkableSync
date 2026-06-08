"""
Interactive configuration wizard for RemarkableSync.

Uses InquirerPy to present an interactive TUI that walks the user through
setting up connection mode, credentials, folder selection, and sync actions.
"""

import sys
from typing import Any, Dict, List

import click

from src.config import SYNC_ACTIONS, load_config, save_config


def run_config_command() -> int:
    """Run the interactive configuration wizard."""
    try:
        from InquirerPy import inquirer
        from InquirerPy.separator import Separator
    except ImportError:
        click.echo("Error: InquirerPy is required for the config wizard.")
        click.echo("Install it with:  pip install InquirerPy")
        return 1

    current = load_config()

    click.echo("=" * 50)
    click.echo("  RemarkableSync Configuration Wizard")
    click.echo("=" * 50)
    click.echo()

    # 1. Connection Mode
    connection_mode = inquirer.select(
        message="Connection mode:",
        choices=[
            {"name": "USB  (direct cable connection)", "value": "usb"},
            {"name": "WiFi (wireless network connection)", "value": "wifi"},
        ],
        default=current.get("connection_mode", "usb"),
    ).execute()

    if connection_mode is None:
        click.echo("Configuration cancelled.")
        return 0

    # 2. WiFi Host (only if WiFi mode selected)
    wifi_host = current.get("wifi_host", "")
    if connection_mode == "wifi":
        wifi_host = inquirer.text(
            message="Tablet WiFi IP address:",
            default=wifi_host or "192.168.1.",
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="IP address cannot be empty.",
        ).execute()

        if wifi_host is None:
            click.echo("Configuration cancelled.")
            return 0

    # 3. Password
    current_password = current.get("password", "")
    password_hint = " (leave blank to keep current)" if current_password else ""
    password = inquirer.secret(
        message=f"SSH password{password_hint}:",
        default="",
        transformer=lambda _: "••••••••" if _ else "(unchanged)" if current_password else "(empty)",
    ).execute()

    if password is None:
        click.echo("Configuration cancelled.")
        return 0

    # Keep current password if user left it blank
    if not password and current_password:
        password = current_password

    # 4. Folders to sync
    click.echo()
    click.echo("  Select top-level folders to sync (empty = sync all):")
    folder_choices = _get_folder_choices(current)
    folders: List[str] = []

    if folder_choices:
        folders = inquirer.checkbox(
            message="Folders to sync:",
            choices=folder_choices,
            default=current.get("folders", []),
        ).execute()

        if folders is None:
            click.echo("Configuration cancelled.")
            return 0
    else:
        click.echo("  (Connect to tablet to select folders, or configure manually later)")
        folders = current.get("folders", [])

    # 5. Sync actions
    action_choices = [
        {"name": display, "value": value}
        for value, display in SYNC_ACTIONS
    ]
    current_actions = current.get("sync_actions", ["pdf"])

    sync_actions = inquirer.checkbox(
        message="What to do on sync:",
        choices=action_choices,
        default=current_actions,
        validate=lambda result: len(result) >= 1,
        invalid_message="Select at least one sync action.",
    ).execute()

    if sync_actions is None:
        click.echo("Configuration cancelled.")
        return 0

    # 6. OCR settings (if handwriting or obsidian selected)
    ocr_enabled = current.get("ocr_enabled", False)
    vault_dir = current.get("vault_dir", "")

    if "handwriting" in sync_actions or "obsidian" in sync_actions:
        ocr_enabled = inquirer.confirm(
            message="Enable AI handwriting OCR?",
            default=ocr_enabled or True,
        ).execute()

        if ocr_enabled is None:
            click.echo("Configuration cancelled.")
            return 0

        if ocr_enabled:
            default_vault = vault_dir or ""
            vault_dir = inquirer.text(
                message="Vault directory (where to save Markdown files):",
                default=default_vault,
                validate=lambda x: len(x.strip()) > 0,
                invalid_message="Vault directory cannot be empty.",
            ).execute()

            if vault_dir is None:
                click.echo("Configuration cancelled.")
                return 0

    # 7. GitHub authentication (for AI OCR)
    github_token = current.get("github_token", "")
    if ocr_enabled:
        has_token = bool(github_token)
        token_status = " (currently authenticated)" if has_token else ""
        do_auth = inquirer.confirm(
            message=f"Authenticate with GitHub for AI OCR?{token_status}",
            default=not has_token,
        ).execute()

        if do_auth:
            github_token = _run_device_flow()
            if not github_token:
                click.echo("  Authentication skipped. You can set GITHUB_TOKEN env var instead.")
                github_token = current.get("github_token", "")

    # Save configuration
    config = {
        "connection_mode": connection_mode,
        "wifi_host": wifi_host,
        "password": password,
        "folders": folders,
        "sync_actions": sync_actions,
        "ocr_enabled": ocr_enabled,
        "vault_dir": vault_dir,
        "github_token": github_token,
    }

    path = save_config(config)

    click.echo()
    click.echo("=" * 50)
    click.echo("  Configuration saved!")
    click.echo("=" * 50)
    click.echo()
    click.echo(f"  File: {path}")
    click.echo(f"  Mode: {connection_mode.upper()}")
    if connection_mode == "wifi":
        click.echo(f"  Host: {wifi_host}")
    click.echo(f"  Password: {'••••••••' if password else '(not set)'}")
    click.echo(f"  Folders: {', '.join(folders) if folders else '(all)'}")
    click.echo(f"  Actions: {', '.join(sync_actions)}")
    if ocr_enabled:
        click.echo(f"  OCR:     enabled → {vault_dir}")
    else:
        click.echo(f"  OCR:     disabled")
    if github_token:
        click.echo(f"  GitHub:  [OK] authenticated")
    click.echo()

    return 0


def _get_folder_choices(current_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Try to get top-level folder list from the tablet or a previous backup.

    Returns a list of choices for InquirerPy, or an empty list if unavailable.
    """
    # Try to read folder names from a local backup metadata cache
    from pathlib import Path

    # Check common backup directory locations for cached metadata
    backup_dirs = [
        Path("./remarkable_backup"),
        Path.home() / "remarkable_backup",
    ]

    folders: List[str] = []
    for backup_dir in backup_dirs:
        metadata_dir = backup_dir / "metadata"
        if not metadata_dir.exists():
            continue
        # Parse .metadata files to find top-level collection names
        try:
            for meta_file in metadata_dir.glob("*.metadata"):
                import json

                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                # Top-level folders are CollectionType with parent=""
                if (
                    meta.get("type") == "CollectionType"
                    and meta.get("parent", "") == ""
                ):
                    name = meta.get("visibleName", "")
                    if name:
                        folders.append(name)
            break  # Found a valid backup dir
        except (OSError, json.JSONDecodeError):
            continue

    if not folders:
        return []

    folders.sort()
    previously_selected = current_config.get("folders", [])
    return [
        {"name": f, "value": f, "enabled": f in previously_selected}
        for f in folders
    ]


def _run_device_flow() -> str:
    """Run GitHub device code flow and return the token, or empty string on failure."""
    try:
        from src.auth.github_device_flow import device_flow_authenticate
    except ImportError:
        click.echo("  Error: requests library required for GitHub auth.")
        return ""

    click.echo()

    def on_code(uri, code):
        click.echo(f"  +-------------------------------------------+")
        click.echo(f"  |  Visit: {uri:<30}  |")
        click.echo(f"  |  Enter code: {code:<26}  |")
        click.echo(f"  +-------------------------------------------+")
        click.echo()
        click.echo("  Waiting for authorization...", nl=False)

    try:
        token, error = device_flow_authenticate(on_code_received=on_code)
    except Exception as e:
        click.echo(f"\n  Error during authentication: {e}")
        return ""

    if token:
        click.echo(" OK")
        click.echo("  Authenticated successfully!")
        return token
    else:
        click.echo(f"\n  {error}")
        return ""
