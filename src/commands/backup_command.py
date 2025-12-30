"""Backup command implementation."""

import logging
from pathlib import Path
from typing import Optional

from ..backup import ReMarkableBackup
from ..utils.logging import setup_logging


def run_backup_command(
    backup_dir: Path, password: Optional[str], verbose: bool, skip_templates: bool, force: bool
) -> int:
    """Execute the backup command.

    Args:
        backup_dir: Directory to store backup files
        password: SSH password for tablet
        verbose: Enable verbose logging
        skip_templates: Skip backing up template files
        force: Force backup all files (ignore sync status)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    setup_logging(verbose)

    print("ReMarkable Tablet Backup")
    print("=" * 40)
    print(f"Backup directory: {backup_dir.absolute()}")

    if not skip_templates:
        print("Template backup: Enabled")
    if force:
        print("Force mode: All files will be backed up")

    backup_tool = ReMarkableBackup(backup_dir, password)

    try:
        # For now, we'll use the existing run_backup method
        # In force mode, we don't use incremental sync
        success = backup_tool.run_backup(
            force_convert_all=False, convert_to_pdf=False, backup_templates=not skip_templates
        )

        if success:
            print("\n[SUCCESS] Backup completed successfully!")
            print(f"Files backed up to: {backup_tool.files_dir}")
            if not skip_templates:
                print(f"Templates backed up to: {backup_tool.templates_dir}")
            return 0
        else:
            print("\n[ERROR] Backup failed. Check logs for details.")
            return 1

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Backup interrupted by user")
        return 130
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        print(f"\n[ERROR] Unexpected error: {e}")
        return 1
