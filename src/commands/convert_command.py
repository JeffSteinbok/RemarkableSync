"""Convert command implementation."""

import logging
from pathlib import Path
from typing import Optional

from ..converter import run_conversion
from ..utils.logging import setup_logging


def run_convert_command(
    backup_dir: Path,
    output_dir: Optional[Path],
    verbose: bool,
    force_all: bool,
    sample: Optional[int],
    notebook: Optional[str],
) -> int:
    """Execute the convert command.

    Args:
        backup_dir: Directory containing ReMarkable backup files
        output_dir: Directory to save PDF files
        verbose: Enable verbose logging
        force_all: Convert all notebooks (ignore sync status)
        sample: Convert only first N notebooks
        notebook: Convert only this notebook (by UUID or name)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    setup_logging(verbose)

    if not backup_dir.exists():
        print(f"[ERROR] Backup directory not found: {backup_dir}")
        return 1

    # Set default output directory
    if not output_dir:
        output_dir = backup_dir / "PDF"

    print("ReMarkable PDF Converter")
    print("=" * 40)
    print(f"Backup directory: {backup_dir}")
    print(f"Output directory: {output_dir}")

    if force_all:
        print("Force mode: Converting all notebooks")
    if sample:
        print(f"Sample mode: Converting first {sample} notebooks")
    if notebook:
        print(f"Single notebook mode: Converting {notebook}")

    try:
        # Determine updated notebooks list
        updated_only_file = None
        if not force_all and not notebook and not sample:
            # Check if there's an updated_notebooks.txt from recent backup
            updated_list = backup_dir / "updated_notebooks.txt"
            if updated_list.exists():
                updated_only_file = updated_list
                print("Converting recently updated notebooks only")

        success = run_conversion(
            backup_dir=backup_dir,
            output_dir=output_dir,
            verbose=verbose,
            sample=sample,
            notebook_filter=notebook,
            updated_only=updated_only_file,
        )

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Conversion interrupted by user")
        return 130
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        print(f"\n[ERROR] Unexpected error: {e}")
        return 1
