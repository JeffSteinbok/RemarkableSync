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

    A unified tool to backup your ReMarkable tablet via USB and convert
    notebooks to PDF format with template support.
    """
    # Print header for all commands (unless it's --version which handles it itself)
    if ctx.invoked_subcommand and not ctx.resilient_parsing:
        print_header()


@cli.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--skip-templates', is_flag=True, help='Skip backing up template files')
@click.option('--force', '-f', is_flag=True, help='Force backup all files (ignore sync status)')
def backup(backup_dir: Path, password: Optional[str], verbose: bool, skip_templates: bool, force: bool):
    """Backup files from ReMarkable tablet via USB.

    Connects to your ReMarkable tablet and backs up all files with incremental sync.
    Template files are backed up by default unless --skip-templates is specified.
    """
    from src.commands.backup_command import run_backup_command
    sys.exit(run_backup_command(backup_dir, password, verbose, skip_templates, force))


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


@cli.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--skip-templates', is_flag=True, help='Skip backing up template files')
@click.option('--force-backup', is_flag=True, help='Force backup all files')
@click.option('--force-convert', is_flag=True, help='Force convert all notebooks')
def sync(backup_dir: Path, password: Optional[str], verbose: bool, skip_templates: bool,
        force_backup: bool, force_convert: bool):
    """Backup and convert in one command (default workflow).

    This is the most common use case: backup your tablet and then convert
    any notebooks that were updated during the backup.
    """
    from src.commands.sync_command import run_sync_command
    sys.exit(run_sync_command(backup_dir, password, verbose, skip_templates,
                             force_backup, force_convert))


def main():
    """Entry point for the application."""
    # If no command specified, default to 'sync'
    if len(sys.argv) == 1:
        sys.argv.append('sync')
    cli()


if __name__ == "__main__":
    main()
