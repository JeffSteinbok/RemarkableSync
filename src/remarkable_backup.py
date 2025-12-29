#!/usr/bin/env python3
"""
ReMarkable Tablet Backup Tool

This tool connects to your ReMarkable tablet via USB, backs up files,
and creates PDF versions with incremental sync support.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
import paramiko

# Import modular backup components
from .backup import ReMarkableBackup


def setup_logging(verbose: bool = False):
    """Configure logging with appropriate levels and formatting.

    Sets up console logging with timestamp formatting to track
    backup progress and debug any connection or sync issues.

    Args:
        verbose: Enable DEBUG level logging if True, INFO level if False
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


@click.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--force-convert-all', '-f', is_flag=True,
              help='Convert all notebooks to PDF regardless of sync status')
@click.option('--convert-pdf', '-c', is_flag=True,
              help='Automatically convert notebooks to PDF using hybrid converter')
@click.option('--skip-templates', is_flag=True,
              help='Skip backing up template files')
def cli(backup_dir: Path, password: Optional[str], verbose: bool, force_convert_all: bool, convert_pdf: bool, skip_templates: bool) -> None:
    """ReMarkable Tablet Backup Tool

    Connects to your ReMarkable tablet via USB and backs up files with
    incremental sync support. Optionally converts notebooks to PDF format.
    """

    setup_logging(verbose)

    print("ReMarkable Tablet Backup Tool")
    print("=" * 40)
    print(f"Backup directory: {backup_dir.absolute()}")

    if convert_pdf:
        print("PDF conversion enabled: Using hybrid converter")

    if force_convert_all:
        print("Force conversion mode: All notebooks will be converted to PDF")

    backup_tool = ReMarkableBackup(backup_dir, password)

    try:
        success = backup_tool.run_backup(force_convert_all=force_convert_all, convert_to_pdf=convert_pdf, backup_templates=not skip_templates)
        if success:
            print("\n[SUCCESS] Backup completed successfully!")
            print(f"Files backed up to: {backup_tool.files_dir}")
            if not skip_templates:
                print(f"Templates backed up to: {backup_tool.templates_dir}")
            if convert_pdf:
                pdfs_final_dir = backup_dir / "pdfs_final"
                if pdfs_final_dir.exists():
                    print(f"PDFs generated in: {pdfs_final_dir}")
                else:
                    print(f"PDF metadata created in: {backup_tool.pdfs_dir}")
        else:
            print("\n[ERROR] Backup failed. Check logs for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Backup interrupted by user")
        sys.exit(130)
    except (OSError, paramiko.SSHException) as e:
        logging.error("Unexpected error: %s", e)
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for the application."""
    # Note: Click decorators handle argument parsing automatically
    # Pylance doesn't understand this, but the code is correct
    cli()  # type: ignore  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
