"""
Converter Module - Internal Helper

This is a helper module providing the conversion API.
Do not run directly - use RemarkableSync.py as the entry point.

Entry Point:
    RemarkableSync.py convert [OPTIONS]

This module provides:
- High-level conversion API with progress tracking
- Integration with hybrid_converter and template renderer
- Batch processing with error handling
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .hybrid_converter import convert_notebook, find_notebooks, organize_notebooks_by_structure
from .template_renderer import TemplateRenderer
from .utils.console import create_progress, print_error


def run_conversion(
    backup_dir: Path,
    output_dir: Path,
    verbose: str = "WRN",
    sample: Optional[int] = None,
    notebook_filter: Optional[str] = None,
    updated_only: Optional[Path] = None,
    updated_pages: Optional[dict] = None,
    folder_filter: Optional[list] = None,
) -> Tuple[bool, Dict[str, List[Path]]]:
    """Run PDF conversion on backed up notebooks.

    Args:
        backup_dir: Directory containing ReMarkable backup files
        output_dir: Directory to save PDF files
        verbose: Enable verbose logging
        sample: Convert only first N notebooks
        notebook_filter: Convert only this notebook (by UUID or name)
        updated_only: File containing list of updated notebook UUIDs
        updated_pages: Dict mapping notebook UUID to set of changed page IDs
        folder_filter: List of top-level folder names to include.
            When provided, only notebooks inside these folders are converted.

    Returns:
        Tuple of (success: bool, converted: dict).  ``converted`` maps
        notebook UUID to the list of per-page PDF paths that were
        generated/updated, so downstream stages (e.g. Markdown export)
        know exactly which pages to process.  When no notebooks were
        converted the dict is empty.
    """
    if not backup_dir.exists():
        logging.error(f"Backup directory not found: {backup_dir}")
        return False, {}

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load updated notebooks list if provided
    updated_uuids = None
    if updated_only and updated_only.exists():
        try:
            with open(updated_only, "r", encoding="utf-8") as f:
                updated_uuids = {line.strip() for line in f if line.strip()}
            logging.info(f"Converting only {len(updated_uuids)} updated notebooks")
        except OSError as e:
            logging.error(f"Failed to read updated notebooks file: {e}")
            return False, {}

    # Find notebooks
    all_items = find_notebooks(backup_dir)

    if not all_items:
        logging.warning("No items found in backup directory")
        return False

    # Filter by updated UUIDs if provided
    if updated_uuids is not None:
        if not updated_uuids:
            logging.info("No updated notebooks — skipping conversion")
            print("  No notebooks changed — skipping conversion")
            return True, {}
        all_items = [item for item in all_items if item["uuid"] in updated_uuids]
        if not all_items:
            logging.info("No updated notebooks found for conversion")
            return True, {}  # Not an error

    # Filter by notebook name/UUID if provided
    if notebook_filter:
        all_items = [
            item
            for item in all_items
            if item["uuid"] == notebook_filter or item["name"] == notebook_filter
        ]
        if not all_items:
            logging.error(f"Notebook not found: {notebook_filter}")
            return False

    # Organize into folder structure
    organization = organize_notebooks_by_structure(all_items, backup_dir)
    notebooks = organization["documents_to_convert"]

    # Filter by selected folders if provided
    if folder_filter:
        include_root = "(Root)" in folder_filter
        real_folders = [f for f in folder_filter if f != "(Root)"]

        def _in_selected_folders(nb):
            fp = nb.get("folder_path", "")
            if not fp:
                return include_root  # Root-level notebooks
            top_folder = fp.split("/")[0]
            return top_folder in real_folders
        before = len(notebooks)
        notebooks = [nb for nb in notebooks if _in_selected_folders(nb)]
        logging.info(
            f"Folder filter applied: {len(notebooks)}/{before} notebooks in selected folders"
        )

    if not notebooks:
        logging.warning("No convertible notebooks found")
        return False

    # Apply sample limit if specified
    if sample and sample > 0:
        notebooks = notebooks[:sample]

    # Initialize template renderer if templates directory exists
    templates_dir = backup_dir / "Templates"
    template_renderer = None
    if templates_dir.exists():
        try:
            template_renderer = TemplateRenderer(templates_dir)
            logging.info(
                f"Template rendering enabled ({len(template_renderer.templates_metadata)} templates loaded)"
            )
        except Exception as e:
            logging.warning(f"Failed to initialize template renderer: {e}")

    # Convert notebooks with per-page Rich progress bar
    successful = 0
    converted: Dict[str, List[Path]] = {}

    # Count total pages across all notebooks for the progress bar
    total_pages = 0
    for nb in notebooks:
        total_pages += len(nb.get("v5_files", []))
        total_pages += len(nb.get("v6_files", []))
        total_pages += len(nb.get("v4_files", []))
        total_pages += len(nb.get("pdf_files", []))

    print(f"  Converting {len(notebooks)} notebooks ({total_pages} pages)...")

    with create_progress("Converting") as progress:
        task = progress.add_task("Converting", total=total_pages)

        for notebook in notebooks:
            nb_name = notebook["name"][:30]
            nb_total = (len(notebook.get("v5_files", []))
                        + len(notebook.get("v6_files", []))
                        + len(notebook.get("v4_files", []))
                        + len(notebook.get("pdf_files", [])))
            page_counter = [0]  # mutable so the lambda can update it

            def _on_page_done(_pc=page_counter, _nb=nb_name, _nbt=nb_total):
                _pc[0] += 1
                progress.update(
                    task, advance=1,
                    description=f"{_nb} (page {_pc[0]} of {_nbt})",
                )

            progress.update(task, description=f"{nb_name} (page 0 of {nb_total})")

            try:
                notebook_changed_pages = None
                if updated_pages and notebook["uuid"] in updated_pages:
                    notebook_changed_pages = updated_pages[notebook["uuid"]]

                results = convert_notebook(
                    notebook, output_dir, backup_dir, template_renderer,
                    changed_page_ids=notebook_changed_pages,
                    on_page_done=_on_page_done,
                )
                if results["output_files"]:
                    successful += 1
                    # Collect per-page PDFs for downstream (MD export)
                    cache_dir = results.get("page_cache_dir")
                    if cache_dir and cache_dir.exists():
                        page_pdfs = sorted(cache_dir.glob("*.pdf"))
                        # Exclude intermediate *_content.pdf files
                        page_pdfs = [p for p in page_pdfs if not p.stem.endswith("_content")]
                        converted[notebook["uuid"]] = page_pdfs
            except Exception as e:
                print_error(f"  [ERR] Failed to convert {notebook['name']}: {e}")

    print(f"  Conversion complete: {successful}/{len(notebooks)} notebooks converted")
    return successful > 0, converted
