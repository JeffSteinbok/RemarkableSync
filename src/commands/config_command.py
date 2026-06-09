"""
Interactive configuration wizard for RemarkableSync.

Uses InquirerPy to present an interactive TUI that walks the user through
setting up connection mode, credentials, folder selection, and sync actions.
"""

from typing import Any, Dict, List

import click

from src.config import SYNC_ACTIONS, load_config, save_config


def run_config_command() -> int:
    """Run the interactive configuration wizard."""
    try:
        from InquirerPy import inquirer
        from InquirerPy.separator import Separator  # noqa: F401
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
        # Offer to enable WiFi SSH via USB if not already enabled
        wifi_ready = inquirer.confirm(
            message="Is WiFi SSH already enabled on your tablet?",
            default=bool(wifi_host),
        ).execute()

        if not wifi_ready:
            click.echo()
            click.echo("  We can enable it for you! Make sure the tablet is")
            click.echo("  connected via USB cable and on the same WiFi network.")
            click.echo()

            enable_now = inquirer.confirm(
                message="Enable WiFi SSH via USB now?",
                default=True,
            ).execute()

            if enable_now:
                # Need password first to connect via USB
                tmp_password = current.get("password", "")
                if not tmp_password:
                    click.echo()
                    click.echo("  SSH password: Settings > Help > Copyright and licenses")
                    tmp_password = inquirer.secret(
                        message="SSH password:",
                        transformer=lambda _: "********" if _ else "(empty)",
                    ).execute()
                    if not tmp_password:
                        click.echo("  Skipped — no password provided.")
                    else:
                        # Save so we don't ask again below
                        password = tmp_password

                if tmp_password:
                    wifi_host = _enable_wifi_ssh(tmp_password)
                    if not wifi_host:
                        click.echo()
                        click.echo("  Could not enable WiFi SSH automatically.")
                        click.echo("  To enable it manually:")
                        click.echo("    1. Connect tablet via USB")
                        click.echo("    2. SSH into 10.11.99.1")
                        click.echo("    3. Run: rm-ssh-over-wlan on")
                        click.echo("    4. Find IP: ip addr show wlan0")
                        click.echo("    5. Re-run this wizard")
                        return 1
            else:
                click.echo()
                click.echo("  To enable WiFi SSH on your reMarkable:")
                click.echo("    1. Connect tablet to your computer via USB")
                click.echo("    2. SSH into 10.11.99.1 (password on tablet:")
                click.echo("       Settings > Help > Copyright and licenses)")
                click.echo("    3. Run: rm-ssh-over-wlan on")
                click.echo("    4. Note the WiFi IP: ip addr show wlan0")
                click.echo("    5. Re-run this wizard with the IP ready")
                return 1

        # Let user confirm/change the IP (pre-filled from device or config)
        default_ip = wifi_host or current.get("wifi_host", "") or "192.168.1."
        wifi_host = inquirer.text(
            message="Tablet WiFi IP address:",
            default=default_ip,
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

    # 4. Backup directory (internal data — defaults to AppData)
    from src.config import _default_backup_dir

    current_backup_dir = current.get("backup_dir", "")
    default_backup = current_backup_dir or _default_backup_dir()
    backup_dir = inquirer.text(
        message="Backup directory (internal sync data):",
        default=default_backup,
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

    # 6. PDF output directory (if PDF or OCR selected)
    from src.config import _default_documents_dir

    docs = _default_documents_dir()
    pdf_dir = current.get("pdf_dir", "")

    if "pdf" in sync_actions or "ocr" in sync_actions:
        default_pdf_dir = pdf_dir or str(docs / "RemarkableSync" / "PDF")
        pdf_dir = inquirer.text(
            message="PDF output directory:",
            default=default_pdf_dir,
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="PDF directory cannot be empty.",
        ).execute()

        if pdf_dir is None:
            click.echo("Configuration cancelled.")
            return 0

    # 7. Markdown export settings — OCR is implied when export is selected
    ocr_enabled = current.get("ocr_enabled", False)
    output_dir = current.get("output_dir", "")

    if "ocr" in sync_actions:
        ocr_enabled = True
        default_output_dir = output_dir or str(docs / "RemarkableSync" / "Markdown")
        output_dir = inquirer.text(
            message="Markdown output directory:",
            default=default_output_dir,
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="Output directory cannot be empty.",
        ).execute()

        if output_dir is None:
            click.echo("Configuration cancelled.")
            return 0

    # 7. AI provider selection (only if OCR is enabled)
    ai_provider = current.get("ai_provider", "github")
    if ocr_enabled:
        ai_provider = inquirer.select(
            message="AI provider for handwriting recognition:",
            choices=[
                {"name": "GitHub Models  (free with GitHub account)", "value": "github"},
                {"name": "Claude / Anthropic  (requires API key)", "value": "claude"},
            ],
            default=ai_provider,
        ).execute()

        if ai_provider is None:
            click.echo("Configuration cancelled.")
            return 0

    # 8. AI token (only if OCR enabled)
    github_token = ""
    claude_api_key = ""

    if ocr_enabled and ai_provider == "github":
        from src.keyring_store import KEY_GITHUB_TOKEN, get_secret, set_secret

        existing = get_secret(KEY_GITHUB_TOKEN)
        if existing:
            click.echo("  GitHub token: (saved in keyring)")
            change = inquirer.confirm(
                message="Re-authenticate with GitHub?",
                default=False,
            ).execute()
            if change:
                github_token = _run_device_flow()
                if github_token:
                    set_secret(KEY_GITHUB_TOKEN, github_token)
            else:
                github_token = existing
        else:
            click.echo()
            click.echo("  GitHub authentication required for AI OCR.")
            github_token = _run_device_flow()
            if github_token:
                set_secret(KEY_GITHUB_TOKEN, github_token)
            else:
                click.echo("  Authentication skipped. You can set GITHUB_TOKEN env var instead.")

    elif ocr_enabled and ai_provider == "claude":
        from src.keyring_store import KEY_CLAUDE_API_KEY, get_secret, set_secret

        existing = get_secret(KEY_CLAUDE_API_KEY)
        if existing:
            click.echo("  Claude API key: (saved in keyring)")
            change = inquirer.confirm(
                message="Change Claude API key?",
                default=False,
            ).execute()
            if change:
                claude_api_key = inquirer.secret(
                    message="Anthropic API key:",
                    transformer=lambda _: "••••••••" if _ else "(empty)",
                ).execute() or ""
                if claude_api_key:
                    set_secret(KEY_CLAUDE_API_KEY, claude_api_key)
            else:
                claude_api_key = existing
        else:
            click.echo()
            click.echo("  To use Claude for handwriting recognition you need an")
            click.echo("  Anthropic API key:")
            click.echo()
            click.echo("  1. Go to  https://console.anthropic.com/settings/keys")
            click.echo("  2. Click 'Create Key' and give it a name")
            click.echo("  3. Copy the key (starts with sk-ant-...)")
            click.echo("  4. Paste it below — it will be stored securely in")
            click.echo("     your system keyring (never written to config files)")
            click.echo()
            claude_api_key = inquirer.secret(
                message="Anthropic API key:",
                transformer=lambda _: "••••••••" if _ else "(empty)",
            ).execute() or ""
            if claude_api_key:
                set_secret(KEY_CLAUDE_API_KEY, claude_api_key)
            else:
                click.echo("  Skipped. You can set ANTHROPIC_API_KEY env var instead.")

    # 8. Connect to tablet and select folders
    click.echo()
    click.echo("  Connecting to tablet to discover folders...")
    folder_choices = _get_folder_choices_live(
        connection_mode, password, wifi_host,
    )
    folders: List[str] = []

    if folder_choices:
        saved_folders = current.get("folders", [])
        # Pre-check previously selected folders
        for choice in folder_choices:
            if isinstance(choice, dict) and choice.get("value") in saved_folders:
                choice["enabled"] = True

        folders = inquirer.checkbox(
            message="Folders to sync (empty = sync all):",
            choices=folder_choices,
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
        "pdf_dir": pdf_dir,
        "folders": folders,
        "sync_actions": sync_actions,
        "ocr_enabled": ocr_enabled,
        "output_dir": output_dir,
        "ai_provider": ai_provider,
    }

    path = save_config(config)

    click.echo()
    click.echo("=" * 50)
    click.echo("  Configuration saved!")
    click.echo("=" * 50)
    click.echo()
    click.echo(f"  File:    {path}")
    click.echo(f"  Mode:    {connection_mode.upper()}")
    if connection_mode == "wifi":
        click.echo(f"  Host:    {wifi_host}")
    click.echo(f"  Password: {'••••••••' if password else '(not set)'}")
    click.echo(f"  Backup:  {backup_dir}")
    if pdf_dir:
        click.echo(f"  PDFs:    {pdf_dir}")
    click.echo(f"  Folders: {', '.join(folders) if folders else '(all)'}")
    click.echo(f"  Actions: {', '.join(sync_actions)}")
    if ocr_enabled:
        click.echo(f"  MD:      {output_dir}")
        click.echo(f"  AI:      {ai_provider}")
        has_token = bool(github_token or claude_api_key)
        click.echo(f"  Token:   {'[OK] saved in keyring' if has_token else '(not set)'}")
    click.echo()

    return 0


def _offer_keyring_save(password: str) -> None:
    """Offer to save the SSH password to the system keyring."""
    try:
        from src.backup.connection import KEYRING_AVAILABLE, ReMarkableConnection
    except ImportError:
        return

    if not KEYRING_AVAILABLE:
        return

    try:
        from InquirerPy import inquirer
        save = inquirer.confirm(
            message="Save password to system keyring?",
            default=True,
        ).execute()
        if save:
            conn = ReMarkableConnection.__new__(ReMarkableConnection)
            conn.save_password(password)
            click.echo("  Password saved to keyring.")
    except Exception:
        pass


def _enable_wifi_ssh(password: str) -> str:
    """Connect via USB and enable WiFi SSH on the tablet.

    Runs ``rm-ssh-over-wlan on`` on the device, then reads the WiFi IP.

    Returns:
        The tablet's WiFi IP address, or empty string on failure.
    """
    import re

    try:
        from src.backup.connection import USB_HOST, ReMarkableConnection
    except ImportError:
        click.echo("  [WARN] Could not import connection module.")
        return ""

    conn = ReMarkableConnection(password=password, host=USB_HOST)
    click.echo("  Connecting via USB...")

    if not conn.connect():
        click.echo("  [WARN] Could not connect via USB. Is the tablet plugged in?")
        return ""

    try:
        # Enable WiFi SSH
        click.echo("  Enabling WiFi SSH...")
        stdout, stderr, exit_code = conn.execute_command("rm-ssh-over-wlan on")
        if exit_code != 0:
            click.echo(f"  [WARN] Command failed: {stderr.strip() or stdout.strip()}")
            return ""

        click.echo("  WiFi SSH enabled!")

        # Get the WiFi IP address
        stdout, stderr, exit_code = conn.execute_command(
            "ip -4 addr show wlan0 | awk '/inet / {split($2, a, \"/\"); print a[1]}'"
        )
        if exit_code == 0 and stdout.strip():
            ip = stdout.strip().split("\n")[0]
            # Validate it looks like an IP
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                click.echo(f"  Tablet WiFi IP: {ip}")
                return ip

        click.echo("  [WARN] Could not determine WiFi IP. Is the tablet on WiFi?")
        return ""

    except Exception as exc:
        click.echo(f"  [WARN] Error enabling WiFi SSH: {exc}")
        return ""
    finally:
        conn.disconnect()


def _get_folder_choices_live(
    connection_mode: str, password: str, wifi_host: str
) -> List[Dict[str, Any]]:
    """Connect to the tablet and discover top-level folders.

    Returns a list of choices for InquirerPy, or an empty list on failure.
    """
    import logging

    try:
        from src.backup.connection import USB_HOST, ReMarkableConnection
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
            click.echo("  [WARN] Failed to read metadata from tablet.")
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

        click.echo("  +-------------------------------------------+")
        click.echo(f"  |  Visit: {uri:<30}  |")
        click.echo(f"  |  Enter code: {code:<26}  |")
        click.echo("  +-------------------------------------------+")
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
