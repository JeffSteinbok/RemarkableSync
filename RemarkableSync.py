#!/usr/bin/env python3
"""
RemarkableSync - Unified command-line interface

Single entry point for backing up and converting ReMarkable tablet files.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Check Python version before importing anything else
if sys.version_info < (3, 11):
    print("Error: RemarkableSync requires Python 3.11 or higher.")
    print(f"You are using Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("\nPlease upgrade your Python installation:")
    print("  - Download from: https://www.python.org/downloads/")
    print("  - Or use a package manager (brew, apt, etc.)")
    sys.exit(1)

import click

from src.__version__ import __repository__, __version__
from src.backup.connection import USB_HOST
from src.utils.logging import LogLevel

# ---------------------------------------------------------------------------
# Shared connection options (reused across commands)
# ---------------------------------------------------------------------------

_LOG_LEVELS = [e.value for e in LogLevel]

_connection_options = [
    click.option(
        '--host',
        default=USB_HOST,
        show_default=True,
        help='Tablet USB IP address or hostname.',
    ),
    click.option(
        '--wifi',
        'use_wifi',
        is_flag=True,
        help='Connect via Wi-Fi instead of USB.',
    ),
    click.option(
        '--wifi-host',
        default='',
        help='Tablet Wi-Fi IP address or hostname (auto-discovered when empty).',
    ),
]


def add_connection_options(func):
    """Decorator that adds the three shared connection options to a command."""
    for option in reversed(_connection_options):
        func = option(func)
    return func


def add_log_level_option(func):
    """Decorator that adds --log-level option to a command."""
    func = click.option(
        '--log-level', '-l',
        type=click.Choice(_LOG_LEVELS, case_sensitive=False),
        default='NONE', show_default=True,
        help='Console log verbosity.',
    )(func)
    return func


def print_header():
    """Print the application header."""
    click.echo(f"RemarkableSync v{__version__} by Jeff Steinbok")
    click.echo(f"Repository: {__repository__}")
    click.echo()


def version_callback(ctx, param, value):
    """Display version information."""
    if not value or ctx.resilient_parsing:
        return
    print_header()
    ctx.exit()


@click.group(invoke_without_command=False)
@click.option('--version', is_flag=True, callback=version_callback,
              expose_value=False, is_eager=True,
              help='Show version and repository information')
@click.option('--log-level', '-l',
              type=click.Choice(_LOG_LEVELS, case_sensitive=False),
              default='NONE', show_default=True,
              help='Log verbosity: DBG, INF, WRN, ERR.')
@click.pass_context
def cli(ctx, log_level):
    """RemarkableSync - Backup and convert ReMarkable tablet files.

    A unified tool to backup your ReMarkable tablet via USB or Wi-Fi and
    convert notebooks to PDF format with template support. Notebooks can
    also be exported directly to a Markdown output directory with
    AI-transcribed text.
    """
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    # Print header for all commands (unless it's --version which handles it itself)
    if ctx.invoked_subcommand and not ctx.resilient_parsing:
        print_header()


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------

@cli.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@add_log_level_option
@click.option('--skip-templates', is_flag=True, help='Skip backing up template files')
@click.option('--force', '-f', is_flag=True, help='Force backup all files (ignore sync status)')
@add_connection_options
def backup(
    backup_dir: Path,
    password: Optional[str],
    log_level: str,
    skip_templates: bool,
    force: bool,
    host: str,
    use_wifi: bool,
    wifi_host: str,
):
    """Backup files from ReMarkable tablet via USB or Wi-Fi.

    Connects to your ReMarkable tablet and backs up all files with incremental
    sync.  Template files are backed up by default unless --skip-templates is
    specified.
    """
    from src.commands.backup_command import run_backup_command
    sys.exit(
        run_backup_command(
            backup_dir,
            password,
            log_level,
            skip_templates,
            force,
            host=host,
            use_wifi=use_wifi,
            wifi_host=wifi_host,
        )
    )


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------

@cli.command(name='pdf')
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory containing ReMarkable backup files')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Directory to save PDF files (default: backup_dir/pdfs_final)')
@add_log_level_option
@click.option('--force-all', '-f', is_flag=True, help='Convert all notebooks (ignore sync status)')
@click.option('--sample', '-s', type=int, help='Convert only first N notebooks (for testing)')
@click.option('--notebook', '-n', type=str, help='Convert only this notebook (by UUID or name)')
def pdf(backup_dir: Path, output_dir: Optional[Path], log_level: str, force_all: bool,
        sample: Optional[int], notebook: Optional[str]):
    """Convert backed up notebooks to PDF format.

    Converts ReMarkable notebooks to PDF with template backgrounds.
    By default, only converts notebooks that were updated in the last backup.
    """
    from src.commands.convert_command import run_convert_command
    sys.exit(run_convert_command(backup_dir, output_dir, log_level, force_all, sample, notebook))


# ---------------------------------------------------------------------------
# sync  (backup + convert)
# ---------------------------------------------------------------------------

@cli.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@add_log_level_option
@click.option('--skip-templates', is_flag=True, help='Skip backing up template files')
@click.option('--force-backup', is_flag=True, help='Force backup all files')
@click.option('--force-convert', is_flag=True, help='Force convert all notebooks')
@add_connection_options
def sync(
    backup_dir: Path,
    password: Optional[str],
    log_level: str,
    skip_templates: bool,
    force_backup: bool,
    force_convert: bool,
    host: str,
    use_wifi: bool,
    wifi_host: str,
):
    """Backup and convert in one command (default workflow).

    This is the most common use case: backup your tablet and then convert
    any notebooks that were updated during the backup.
    """
    from src.commands.sync_command import run_sync_command
    sys.exit(
        run_sync_command(
            backup_dir,
            password,
            log_level,
            skip_templates,
            force_backup,
            force_convert,
            host=host,
            use_wifi=use_wifi,
            wifi_host=wifi_host,
        )
    )


# ---------------------------------------------------------------------------
# md  (backup + convert + OCR/AI + Markdown export)
# ---------------------------------------------------------------------------

@cli.command(name='md')
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=None,
              help='Directory to store backup files (default: from config)')
@click.option('--vault-dir', '-V', type=click.Path(path_type=Path),
              default=None,
              help='Markdown output directory (default: from config)')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@add_log_level_option
@click.option('--with-backup', is_flag=True, help='Also run tablet backup before export')
@click.option('--with-pdf', is_flag=True, help='Also run PDF conversion before export')
@click.option('--force-backup', is_flag=True, help='Force full backup')
@click.option('--force-convert', is_flag=True, help='Force convert all notebooks')
@click.option('--force-export', is_flag=True, help='Re-export all notes even if unchanged')
@click.option('--ai-provider', default=None,
              type=click.Choice(['', 'claude', 'anthropic', 'github', 'github_models'], case_sensitive=False),
              help='AI provider for handwriting recognition')
@click.option('--ai-model', default='', help='Override AI model (provider-specific)')
@click.option('--ai-api-key', default='', envvar='REMARKABLE_AI_KEY',
              help='AI API key (falls back to config / env-vars)')
@click.option('--use-ai-ocr', is_flag=True, default=True, show_default=True,
              help='Use AI vision for handwriting recognition (requires --ai-provider)')
@click.option('--notebook', '-n', type=str, help='Export only this notebook (by name or UUID)')
@click.option('--page', type=int, help='Export only this page number (requires --notebook)')
@click.option('--tags', default='remarkable',
              help='Comma-separated tags to add to note frontmatter')
@click.option('--no-images', 'embed_images', is_flag=True, default=False,
              help='Do not embed page images in notes')
@add_connection_options
def md(
    backup_dir: Optional[Path],
    vault_dir: Optional[Path],
    password: Optional[str],
    log_level: str,
    with_backup: bool,
    with_pdf: bool,
    force_backup: bool,
    force_convert: bool,
    force_export: bool,
    ai_provider: Optional[str],
    ai_model: str,
    ai_api_key: str,
    use_ai_ocr: bool,
    notebook: Optional[str],
    page: Optional[int],
    tags: str,
    embed_images: bool,
    host: str,
    use_wifi: bool,
    wifi_host: str,
):
    """Export existing PDFs to Markdown with optional AI OCR.

    By default only runs the Markdown export step.  Use --with-backup
    and/or --with-pdf to include earlier pipeline stages.

    Reads saved config for defaults (backup dir, output dir, AI provider,
    connection mode).  CLI flags override config values.

    \b
    Examples:
      # Export from existing PDFs (using saved config)
      RemarkableSync md

      # Full pipeline: backup + pdf + md
      RemarkableSync md --with-backup --with-pdf
    """
    from src.commands.pipeline import run_pipeline
    from src.config import load_config

    cfg = load_config()

    # Apply config defaults where CLI didn't provide a value
    if backup_dir is None:
        backup_dir = Path(cfg.get("backup_dir", "./remarkable_backup"))
    output_dir = vault_dir or Path(cfg.get("output_dir", ""))
    if not str(output_dir):
        click.echo("[ERROR] No output directory specified. Use -V or run: python RemarkableSync.py config")
        sys.exit(1)

    if ai_provider is None:
        ai_provider = cfg.get("ai_provider", "github")
    if not ai_api_key:
        from src.keyring_store import KEY_CLAUDE_API_KEY, KEY_GITHUB_TOKEN, get_secret
        if ai_provider == "claude":
            ai_api_key = get_secret(KEY_CLAUDE_API_KEY)
        else:
            ai_api_key = get_secret(KEY_GITHUB_TOKEN)

    # Connection defaults from config
    cfg_conn = cfg.get("connection_mode", "usb")
    if not use_wifi and cfg_conn == "wifi":
        use_wifi = True
    if not wifi_host:
        wifi_host = cfg.get("wifi_host", "")
    sys.exit(
        run_pipeline(
            backup_dir=backup_dir,
            output_dir=output_dir,
            password=password,
            log_level=log_level,
            skip_backup=not with_backup,
            skip_convert=not with_pdf,
            force_backup=force_backup,
            force_convert=force_convert,
            force_export=force_export or (not with_backup and not with_pdf),
            ai_provider=ai_provider,
            ai_model=ai_model,
            ai_api_key=ai_api_key,
            use_ai_ocr=use_ai_ocr,
            notebook_filter=notebook,
            page_filter=page,
            tags=tags,
            embed_images=embed_images,
            host=host,
            use_wifi=use_wifi,
            wifi_host=wifi_host,
        )
    )


# ---------------------------------------------------------------------------
# config  (interactive configuration wizard)
# ---------------------------------------------------------------------------

@cli.command()
def config():
    """Interactive configuration wizard.

    Walks through connection mode, credentials, folder selection, and
    sync actions using an interactive terminal UI.
    """
    from src.commands.config_command import run_config_command
    sys.exit(run_config_command())


# ---------------------------------------------------------------------------
# watch  (periodic sync)
# ---------------------------------------------------------------------------

@cli.command()
@click.option('--interval', '-i', type=int, default=None,
              help='Minutes between sync attempts (overrides config)')
@click.option('--systray/--no-systray', default=True, show_default=True,
              help='Show a system tray icon while watch mode is running')
@click.option('--foreground', is_flag=True, default=False,
              help='Run in the foreground instead of detaching')
@add_log_level_option
@add_connection_options
def watch(
    interval: Optional[int],
    systray: bool,
    foreground: bool,
    log_level: str,
    host: str,
    use_wifi: bool,
    wifi_host: str,
):
    """Run periodic sync in the background with a system tray icon.

    Reads all settings from the config file (run ``config`` first).
    The tray menu lets you change the interval, trigger an immediate sync,
    pause/resume, toggle run-at-startup, and open output folders.

    By default, detaches from the terminal and runs in the background.
    Use --foreground to keep it attached.
    """
    from src.commands.watch_command import INTERVAL_CHOICES, run_watch_command
    from src.config import load_config, save_config

    cfg = load_config()

    # Determine interval: CLI flag > config > prompt on first run
    saved_interval = cfg.get("watch_interval")  # minutes, or None
    if interval is not None:
        interval_secs = interval * 60
    elif saved_interval is not None:
        interval_secs = saved_interval * 60
    else:
        # First time — ask with InquirerPy like the config wizard
        try:
            from InquirerPy import inquirer

            choices = [
                {"name": label, "value": secs}
                for label, secs in INTERVAL_CHOICES
            ]
            interval_secs = inquirer.select(
                message="Sync interval:",
                choices=choices,
                default=30 * 60,
            ).execute()

            if interval_secs is None:
                click.echo("Cancelled.")
                sys.exit(0)
        except ImportError:
            click.echo("Pick a sync interval:\n")
            for i, (label, _secs) in enumerate(INTERVAL_CHOICES, 1):
                click.echo(f"  {i}. {label}")
            click.echo()
            choice = click.prompt(
                "Choice", type=click.IntRange(1, len(INTERVAL_CHOICES)), default=2,
            )
            _, interval_secs = INTERVAL_CHOICES[choice - 1]

        cfg["watch_interval"] = interval_secs // 60 if interval_secs else 0
        save_config(cfg)
        click.echo()

    # Detach to background unless --foreground
    if not foreground:
        _detach_watch()
        return

    # --- foreground mode (child process lands here) ---

    backup_dir = Path(cfg.get("backup_dir", "./remarkable_backup"))
    output_dir_str = cfg.get("output_dir", "")
    output_dir = Path(output_dir_str) if output_dir_str else None
    sync_actions = cfg.get("sync_actions", ["backup", "pdf"])

    conn_mode = cfg.get("connection_mode", "usb")
    if not use_wifi and conn_mode == "wifi":
        use_wifi = True
    if not wifi_host:
        wifi_host = cfg.get("wifi_host", "")

    ai_provider = cfg.get("ai_provider", "")
    from src.keyring_store import KEY_CLAUDE_API_KEY, KEY_GITHUB_TOKEN, get_secret
    if ai_provider == "claude":
        ai_api_key = get_secret(KEY_CLAUDE_API_KEY)
    else:
        ai_api_key = get_secret(KEY_GITHUB_TOKEN)
    tags = cfg.get("tags", "remarkable")

    has_md = "ocr" in sync_actions

    if has_md and output_dir:
        from src.commands.pipeline import run_pipeline

        def run_once() -> int:
            return run_pipeline(
                backup_dir=backup_dir,
                output_dir=output_dir,
                log_level=log_level,
                skip_backup=False,
                skip_convert=False,
                force_backup=False,
                force_convert=False,
                force_export=False,
                ai_provider=ai_provider or "github",
                ai_model="",
                ai_api_key=ai_api_key,
                use_ai_ocr=True,
                tags=tags,
                embed_images=True,
                host=host,
                use_wifi=use_wifi,
                wifi_host=wifi_host,
            )

        mode = "md"
    else:
        from src.commands.sync_command import run_sync_command

        def run_once() -> int:
            return run_sync_command(
                backup_dir=backup_dir,
                log_level=log_level,
                skip_templates=False,
                force_backup=False,
                force_convert=False,
                host=host,
                use_wifi=use_wifi,
                wifi_host=wifi_host,
            )

        mode = "sync"

    sys.exit(
        run_watch_command(
            interval=interval_secs,
            backup_dir=backup_dir,
            run_once=run_once,
            log_level=log_level,
            mode=mode,
            use_systray=systray,
            output_dir=output_dir,
        )
    )


def _detach_watch():
    """Re-launch this script as a detached background process."""
    import subprocess as sp

    script = Path(sys.argv[0]).resolve()

    if sys.platform == "win32":
        # Use pythonw.exe to avoid any console windows
        exe = Path(sys.executable)
        pythonw = exe.parent / "pythonw.exe"
        if not pythonw.exists():
            pythonw = exe  # fallback

        args = [str(pythonw), str(script), "watch", "--foreground"]
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        sp.Popen(
            args,
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
            close_fds=True,
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
        )
    else:
        args = [sys.executable, str(script), "watch", "--foreground"]
        sp.Popen(
            args,
            start_new_session=True,
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
        )

    click.echo("  RemarkableSync watch started in the background.")
    click.echo("  Use the system tray icon to control it.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the application.

    When no subcommand is given, reads saved config to determine what to run:
    - If 'ocr' is in sync_actions -> obsidian-sync
    - Otherwise -> sync (backup + convert)

    Config-based defaults (backup_dir, output_dir, connection, etc.) are
    injected as CLI args so the subcommand sees them.
    """
    known_commands = {'backup', 'pdf', 'sync', 'md', 'config', 'watch'}
    has_command = any(arg in known_commands for arg in sys.argv[1:])

    if not has_command and '--version' not in sys.argv and '--help' not in sys.argv:
        # Load config to decide which pipeline to run
        from src.config import load_config

        cfg = load_config()
        actions = cfg.get("sync_actions", [])
        extra_args: list[str] = []

        # Connection settings
        conn = cfg.get("connection_mode", "usb")
        if conn == "wifi":
            extra_args.append("--wifi")
            wifi_host = cfg.get("wifi_host", "")
            if wifi_host:
                extra_args.extend(["--wifi-host", wifi_host])

        # Backup directory
        backup_dir = cfg.get("backup_dir", "")
        if backup_dir:
            extra_args.extend(["-d", backup_dir])

        if "ocr" in actions:
            # Full pipeline: backup -> convert -> OCR -> Markdown export
            output_dir = cfg.get("output_dir", "")
            if not output_dir:
                print("[ERROR] Markdown export is enabled but no output directory is configured.")
                print("Run: python RemarkableSync.py config")
                sys.exit(1)
            extra_args.extend(["-V", output_dir])

            ai_provider = cfg.get("ai_provider", "github")
            if ai_provider:
                extra_args.extend(["--ai-provider", ai_provider])
            from src.keyring_store import KEY_CLAUDE_API_KEY, KEY_GITHUB_TOKEN, get_secret
            if ai_provider == "claude":
                ai_token = get_secret(KEY_CLAUDE_API_KEY)
            else:
                ai_token = get_secret(KEY_GITHUB_TOKEN)
            if ai_token:
                extra_args.extend(["--ai-api-key", ai_token])

            sys.argv[1:1] = ["md", "--with-backup", "--with-pdf"] + extra_args
        else:
            sys.argv[1:1] = ["sync"] + extra_args

    cli()


if __name__ == "__main__":
    main()

