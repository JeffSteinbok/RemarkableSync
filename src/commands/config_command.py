"""
Interactive configuration wizard for RemarkableSync.

Uses InquirerPy to present an interactive TUI that walks the user through
setting up connection mode, credentials, folder selection, and sync actions.
"""

import sys
from typing import Any, Dict, List

import click

from src.config import SYNC_ACTIONS, load_config, save_config
from src.utils.console import print_error, print_success, print_warn


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
    if current_password:
        click.echo("  SSH password: (saved)")
        change_pw = inquirer.confirm(
            message="Do you want to change the SSH password?",
            default=False,
        ).execute()
        if change_pw:
            password = inquirer.secret(
                message="New SSH password:",
                transformer=lambda _: "********" if _ else "(empty)",
            ).execute()
            if password is None:
                click.echo("Configuration cancelled.")
                return 0
            _offer_keyring_save(password)
        else:
            password = current_password
    else:
        click.echo("  SSH password: (not set)")
        password = inquirer.secret(
            message="SSH password (Settings > Help > Copyright and licenses):",
            transformer=lambda _: "********" if _ else "(empty)",
        ).execute()
        if password is None:
            click.echo("Configuration cancelled.")
            return 0
        if password:
            _offer_keyring_save(password)

    # 4. Backup directory
    current_backup_dir = current.get("backup_dir", "")
    backup_dir = inquirer.text(
        message="Backup directory (where tablet files are stored):",
        default=current_backup_dir or "",
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Backup directory cannot be empty.",
    ).execute()

    if backup_dir is None:
        click.echo("Configuration cancelled.")
        return 0

    # 5. Sync actions
    current_actions = current.get("sync_actions", ["backup", "pdf"])
    action_choices = [
        {"name": display, "value": value, "enabled": value in current_actions}
        for value, display in SYNC_ACTIONS
    ]

    sync_actions = inquirer.checkbox(
        message="What to do on sync:",
        choices=action_choices,
        validate=lambda result: len(result) >= 1,
        invalid_message="Select at least one sync action.",
    ).execute()

    if sync_actions is None:
        click.echo("Configuration cancelled.")
        return 0

    # 6. Markdown export settings — OCR is implied when export is selected
    ocr_enabled = current.get("ocr_enabled", False)
    output_dir = current.get("output_dir", "")

    if "ocr" in sync_actions:
        ocr_enabled = True
        default_output_dir = output_dir or ""
        output_dir = inquirer.text(
            message="Markdown output directory:",
            default=default_output_dir,
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="Output directory cannot be empty.",
        ).execute()

        if output_dir is None:
            click.echo("Configuration cancelled.")
            return 0

    # 7. GitHub authentication (only if needed and not already authenticated)
    github_token = current.get("github_token", "")
    if ocr_enabled and not github_token:
        click.echo()
        click.echo("  GitHub authentication required for AI OCR.")
        github_token = _run_device_flow()
        if not github_token:
            click.echo("  Authentication skipped. You can set GITHUB_TOKEN env var instead.")

    # 8. Connect to tablet and select folders
    click.echo()
    click.echo("  Connecting to tablet to discover folders...")
    folder_choices = _get_folder_choices_live(
        connection_mode, password, wifi_host,
    )
    folders: List[str] = []

    if folder_choices:
        folders = inquirer.checkbox(
            message="Folders to sync (empty = sync all):",
            choices=folder_choices,
            default=current.get("folders", []),
        ).execute()

        if folders is None:
            click.echo("Configuration cancelled.")
            return 0
    else:
        click.echo("  Could not connect to tablet. Folder selection skipped.")
        folders = current.get("folders", [])

    # Save configuration
    config = {
        "connection_mode": connection_mode,
        "wifi_host": wifi_host,
        "password": password,
        "backup_dir": backup_dir,
        "folders": folders,
        "sync_actions": sync_actions,
        "ocr_enabled": ocr_enabled,
        "output_dir": output_dir,
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
        click.echo(f"  OCR:     enabled -> {output_dir}")
    else:
        click.echo(f"  OCR:     disabled")
    if github_token:
        click.echo(f"  GitHub:  [OK] authenticated")
    click.echo()

    return 0


def _get_folder_choices_live(
    connection_mode: str, password: str, wifi_host: str
) -> List[Dict[str, Any]]:
    """Connect to the tablet and discover top-level folders.

    Returns a list of choices for InquirerPy, or an empty list on failure.
    """
    import json
    import logging

    try:
        from src.backup.connection import ReMarkableConnection, USB_HOST
    except ImportError:
        return []

    use_wifi = connection_mode == "wifi"
    host = wifi_host if use_wifi else USB_HOST

    conn = ReMarkableConnection(
        password=password,
        host=host,
        use_wifi=use_wifi,
        wifi_host=wifi_host,
    )

    if not conn.connect():
        click.echo("  [WARN] Could not connect to tablet.")
        return []

    try:
        xochitl = "/home/root/.local/share/remarkable/xochitl"

        # Use a single command to dump all metadata files efficiently
        # Output format: one JSON object per line, prefixed with filename
        stdout, stderr, exit_code = conn.execute_command(
            f"for f in {xochitl}/*.metadata; do "
            f"[ -f \"$f\" ] && echo \"FILE:$f\" && cat \"$f\"; "
            f"done"
        )
        if exit_code != 0:
            click.echo(f"  [WARN] Failed to read metadata from tablet.")
            return []

        # Parse the output — each metadata block starts with FILE: line
        folders: List[str] = []
        current_json = []
        for line in stdout.split("\n"):
            if line.startswith("FILE:"):
                # Process previous block
                if current_json:
                    _parse_folder_metadata("\n".join(current_json), folders)
                current_json = []
            else:
                current_json.append(line)
        # Process last block
        if current_json:
            _parse_folder_metadata("\n".join(current_json), folders)

        if not folders:
            click.echo("  No top-level folders found on tablet.")
            return []

        click.echo(f"  Found {len(folders)} folders on tablet.")
        folders.sort()
        choices = [{"name": "(Root) - notebooks not in any folder", "value": "(Root)"}]
        choices += [{"name": f, "value": f} for f in folders]
        return choices

    except Exception as exc:
        logging.debug("Failed to list folders from tablet: %s", exc)
        click.echo(f"  [WARN] Error reading folders: {exc}")
        return []
    finally:
        conn.disconnect()


def _parse_folder_metadata(json_text: str, folders: List[str]) -> None:
    """Parse a metadata JSON block and append folder name if it's a top-level collection."""
    import json

    json_text = json_text.strip()
    if not json_text:
        return
    try:
        meta = json.loads(json_text)
        if (
            meta.get("type") == "CollectionType"
            and meta.get("parent", "") == ""
        ):
            name = meta.get("visibleName", "")
            if name:
                folders.append(name)
    except (json.JSONDecodeError, ValueError):
        pass


def _run_device_flow() -> str:
    """Run GitHub device code flow and return the token, or empty string on failure."""
    try:
        from src.auth.github_device_flow import device_flow_authenticate
    except ImportError:
        click.echo("  Error: requests library required for GitHub auth.")
        return ""

    click.echo()

    def on_code(uri, code):
        # Copy code to clipboard for easy pasting
        try:
            import subprocess
            subprocess.run(
                ["clip"], input=code.encode(), check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            copied = " (copied to clipboard)"
        except Exception:
            copied = ""

        click.echo(f"  +-------------------------------------------+")
        click.echo(f"  |  Visit: {uri:<30}  |")
        click.echo(f"  |  Enter code: {code:<26}  |")
        click.echo(f"  +-------------------------------------------+")
        click.echo(f"  Code{copied}")
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
