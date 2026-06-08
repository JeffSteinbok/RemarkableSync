#!/usr/bin/env python3
"""
RemarkableSync - Unified command-line interface

Single entry point for backing up and converting ReMarkable tablet files.
"""

import sys
from pathlib import Path
from typing import Optional

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

# ---------------------------------------------------------------------------
# Shared connection options (reused across commands)
# ---------------------------------------------------------------------------

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
@click.pass_context
def cli(ctx):
    """RemarkableSync - Backup and convert ReMarkable tablet files.

    A unified tool to backup your ReMarkable tablet via USB or Wi-Fi and
    convert notebooks to PDF format with template support.  Notebooks can
    also be exported directly to an Obsidian vault with AI-transcribed text.
    """
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
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--skip-templates', is_flag=True, help='Skip backing up template files')
@click.option('--force', '-f', is_flag=True, help='Force backup all files (ignore sync status)')
@add_connection_options
def backup(
    backup_dir: Path,
    password: Optional[str],
    verbose: bool,
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
            verbose,
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

@cli.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory containing ReMarkable backup files')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Directory to save PDF files (default: backup_dir/pdfs_final)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--force-all', '-f', is_flag=True, help='Convert all notebooks (ignore sync status)')
@click.option('--sample', '-s', type=int, help='Convert only first N notebooks (for testing)')
@click.option('--notebook', '-n', type=str, help='Convert only this notebook (by UUID or name)')
def convert(backup_dir: Path, output_dir: Optional[Path], verbose: bool, force_all: bool,
           sample: Optional[int], notebook: Optional[str]):
    """Convert backed up notebooks to PDF format.

    Converts ReMarkable notebooks to PDF with template backgrounds.
    By default, only converts notebooks that were updated in the last backup.
    """
    from src.commands.convert_command import run_convert_command
    sys.exit(run_convert_command(backup_dir, output_dir, verbose, force_all, sample, notebook))


# ---------------------------------------------------------------------------
# sync  (backup + convert)
# ---------------------------------------------------------------------------

@cli.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--skip-templates', is_flag=True, help='Skip backing up template files')
@click.option('--force-backup', is_flag=True, help='Force backup all files')
@click.option('--force-convert', is_flag=True, help='Force convert all notebooks')
@add_connection_options
def sync(
    backup_dir: Path,
    password: Optional[str],
    verbose: bool,
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
            verbose,
            skip_templates,
            force_backup,
            force_convert,
            host=host,
            use_wifi=use_wifi,
            wifi_host=wifi_host,
        )
    )


# ---------------------------------------------------------------------------
# obsidian-sync  (backup + convert + OCR/AI + Obsidian export)
# ---------------------------------------------------------------------------

@cli.command(name='obsidian-sync')
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--vault-dir', '-V', required=True, type=click.Path(path_type=Path),
              help='Root directory of the Obsidian vault to write notes into')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--skip-backup', is_flag=True, help='Skip tablet backup stage')
@click.option('--skip-convert', is_flag=True, help='Skip PDF conversion stage')
@click.option('--force-backup', is_flag=True, help='Force full backup')
@click.option('--force-convert', is_flag=True, help='Force convert all notebooks')
@click.option('--force-export', is_flag=True, help='Re-export all notes even if unchanged')
@click.option('--ai-provider', default='',
              type=click.Choice(['', 'claude', 'anthropic', 'github', 'github_models'], case_sensitive=False),
              help='AI provider for handwriting recognition')
@click.option('--ai-model', default='', help='Override AI model (provider-specific)')
@click.option('--ai-api-key', default='', envvar='REMARKABLE_AI_KEY',
              help='AI API key (falls back to ANTHROPIC_API_KEY / GITHUB_TOKEN env-vars)')
@click.option('--use-ai-ocr', is_flag=True, default=True, show_default=True,
              help='Use AI vision for handwriting recognition (requires --ai-provider)')
@click.option('--tags', default='remarkable',
              help='Comma-separated tags to add to note frontmatter')
@click.option('--no-images', 'embed_images', is_flag=True, default=False,
              help='Do not embed page images in notes')
@add_connection_options
def obsidian_sync(
    backup_dir: Path,
    vault_dir: Path,
    password: Optional[str],
    verbose: bool,
    skip_backup: bool,
    skip_convert: bool,
    force_backup: bool,
    force_convert: bool,
    force_export: bool,
    ai_provider: str,
    ai_model: str,
    ai_api_key: str,
    use_ai_ocr: bool,
    tags: str,
    embed_images: bool,
    host: str,
    use_wifi: bool,
    wifi_host: str,
):
    """Full pipeline: backup → PDF → OCR/AI → Obsidian Markdown.

    Backs up your tablet, converts notebooks to PDF, runs AI handwriting
    recognition, and writes the results as Markdown notes in your Obsidian
    vault – preserving the original folder hierarchy.

    \b
    Examples:
      # Sync via USB using Claude for OCR
      RemarkableSync obsidian-sync --vault-dir ~/Documents/Obsidian/Brain \\
          --ai-provider claude

      # Sync via Wi-Fi using GitHub Models, force re-export all
      RemarkableSync obsidian-sync --vault-dir ~/Notes --wifi \\
          --ai-provider github --force-export
    """
    from src.commands.obsidian_sync_command import run_obsidian_sync_command
    sys.exit(
        run_obsidian_sync_command(
            backup_dir=backup_dir,
            vault_dir=vault_dir,
            verbose=verbose,
            skip_backup=skip_backup,
            skip_convert=skip_convert,
            force_backup=force_backup,
            force_convert=force_convert,
            force_export=force_export,
            ai_provider=ai_provider,
            ai_model=ai_model,
            ai_api_key=ai_api_key,
            use_ai_ocr=use_ai_ocr,
            tags=tags,
            embed_images=embed_images,
            host=host,
            use_wifi=use_wifi,
            wifi_host=wifi_host,
        )
    )


# ---------------------------------------------------------------------------
# watch  (periodic sync)
# ---------------------------------------------------------------------------

@cli.command()
@click.option('--interval', '-i', type=int, default=30, show_default=True,
              help='Minutes between sync attempts')
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--vault-dir', '-V', type=click.Path(path_type=Path), default=None,
              help='Obsidian vault directory (enables obsidian-sync mode)')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--skip-templates', is_flag=True, help='Skip template backup')
@click.option('--ai-provider', default='',
              type=click.Choice(['', 'claude', 'anthropic', 'github', 'github_models'], case_sensitive=False),
              help='AI provider (obsidian mode only)')
@click.option('--ai-model', default='', help='Override AI model')
@click.option('--ai-api-key', default='', envvar='REMARKABLE_AI_KEY', help='AI API key')
@click.option('--tags', default='remarkable', help='Comma-separated tags (obsidian mode)')
@click.option('--systray/--no-systray', default=True, show_default=True,
              help='Show a system tray icon while watch mode is running')
@add_connection_options
def watch(
    interval: int,
    backup_dir: Path,
    vault_dir: Optional[Path],
    password: Optional[str],
    verbose: bool,
    skip_templates: bool,
    ai_provider: str,
    ai_model: str,
    ai_api_key: str,
    tags: str,
    systray: bool,
    host: str,
    use_wifi: bool,
    wifi_host: str,
):
    """Periodically sync in the background (every N minutes).

    When --vault-dir is provided the full obsidian-sync pipeline is used;
    otherwise a plain backup + PDF conversion sync is performed.

    A file lock prevents overlapping runs.  Consecutive failures trigger
    exponential back-off (up to 1 hour).
    """
    from src.commands.watch_command import run_watch_command

    interval_secs = interval * 60

    if vault_dir:
        # Obsidian-sync mode
        from src.commands.obsidian_sync_command import run_obsidian_sync_command

        def run_once() -> int:
            return run_obsidian_sync_command(
                backup_dir=backup_dir,
                vault_dir=vault_dir,
                verbose=verbose,
                skip_backup=False,
                skip_convert=False,
                force_backup=False,
                force_convert=False,
                force_export=False,
                ai_provider=ai_provider,
                ai_model=ai_model,
                ai_api_key=ai_api_key,
                use_ai_ocr=bool(ai_provider),
                tags=tags,
                embed_images=True,
                host=host,
                use_wifi=use_wifi,
                wifi_host=wifi_host,
            )

        mode = "obsidian-sync"
    else:
        # Plain sync mode
        from src.commands.sync_command import run_sync_command

        def run_once() -> int:
            return run_sync_command(
                backup_dir=backup_dir,
                verbose=verbose,
                skip_templates=skip_templates,
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
            verbose=verbose,
            mode=mode,
            use_systray=systray,
        )
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the application."""
    # If no command specified, default to 'sync'
    if len(sys.argv) == 1:
        sys.argv.append('sync')
    cli()


if __name__ == "__main__":
    main()
