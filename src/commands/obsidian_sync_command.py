"""obsidian-sync command implementation.

Chains the full pipeline:
  1. Backup from tablet (optional)
  2. Convert notebooks to PDF (optional)
  3. OCR / AI handwriting transcription
  4. Export Markdown notes to an Obsidian vault
"""

import logging
from pathlib import Path
from typing import Optional

from ..backup import ReMarkableBackup
from ..backup.connection import USB_HOST
from ..converter import run_conversion
from ..utils.logging import setup_logging


def run_obsidian_sync_command(
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
    host: str = USB_HOST,
    use_wifi: bool = False,
    wifi_host: str = "",
) -> int:
    """Run the full pipeline: backup → PDF → OCR/AI → Obsidian Markdown.

    Args:
        backup_dir: RemarkableSync backup directory.
        vault_dir: Root of the Obsidian vault to write notes into.
        password: SSH password for tablet.
        verbose: Enable debug logging.
        skip_backup: Skip the tablet backup stage.
        skip_convert: Skip the PDF conversion stage.
        force_backup: Force full backup (ignore incremental state).
        force_convert: Force convert all notebooks.
        force_export: Re-export all notes even if unchanged.
        ai_provider: AI provider name (``"claude"`` / ``"github"``).
        ai_model: Override the default model for the chosen provider.
        ai_api_key: API key (falls back to env-vars when empty).
        use_ai_ocr: Use AI vision for handwriting recognition.
        tags: Comma-separated tags to add to every note's frontmatter.
        embed_images: Embed page image attachments in notes.
        host: Tablet USB IP/hostname.
        use_wifi: Use Wi-Fi connection.
        wifi_host: Wi-Fi IP/hostname.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    setup_logging(verbose)

    print("ReMarkable → Obsidian Sync")
    print("=" * 40)
    print(f"Backup directory : {backup_dir.absolute()}")
    print(f"Obsidian vault   : {vault_dir.absolute()}")

    # ------------------------------------------------------------------
    # Stage 1: Backup
    # ------------------------------------------------------------------
    updated_uuids: set = set()

    if not skip_backup:
        print("\n[1/3] Backing up tablet…")
        if use_wifi:
            print(f"      Connection: Wi-Fi ({wifi_host or 'auto-discover'})")
        else:
            print(f"      Connection: USB ({host})")

        backup_tool = ReMarkableBackup(
            backup_dir,
            password=password,
            host=host,
            use_wifi=use_wifi,
            wifi_host=wifi_host,
        )
        try:
            success, updated_uuids = backup_tool.backup_files()
            if not success:
                print("[ERROR] Backup failed.")
                return 1
            backup_tool.backup_templates()
            print(f"      ✓ Backed up ({len(updated_uuids)} notebooks updated)")
        except Exception as exc:  # noqa: BLE001
            logging.error("Backup error: %s", exc)
            print(f"[ERROR] Backup failed: {exc}")
            return 1
    else:
        print("\n[1/3] Backup skipped (--skip-backup)")

    # ------------------------------------------------------------------
    # Stage 2: PDF conversion
    # ------------------------------------------------------------------
    pdf_output_dir = backup_dir / "PDF"

    if not skip_convert:
        print("\n[2/3] Converting notebooks to PDF…")
        updated_list_file: Optional[Path] = None

        if not force_convert and updated_uuids and not skip_backup:
            updated_list_file = backup_dir / "updated_notebooks.txt"
            try:
                updated_list_file.write_text(
                    "\n".join(sorted(updated_uuids)), encoding="utf-8"
                )
            except OSError as exc:
                logging.warning("Could not write updated notebooks list: %s", exc)
                updated_list_file = None

        try:
            run_conversion(
                backup_dir=backup_dir,
                output_dir=pdf_output_dir,
                verbose=verbose,
                updated_only=updated_list_file,
            )
            print("      ✓ PDF conversion done")
        except Exception as exc:  # noqa: BLE001
            logging.error("Conversion error: %s", exc)
            print(f"[ERROR] PDF conversion failed: {exc}")
            return 1
    else:
        print("\n[2/3] PDF conversion skipped (--skip-convert)")

    # ------------------------------------------------------------------
    # Stage 3: OCR + Obsidian export
    # ------------------------------------------------------------------
    print("\n[3/3] Exporting to Obsidian…")

    # Build OCR engine
    from ..ai import get_provider as get_ai_provider
    from ..ocr import OCREngine
    from ..obsidian import ObsidianExporter
    from ..hybrid_converter import find_notebooks, organize_notebooks_by_structure

    ocr_engine: Optional[OCREngine] = None
    if use_ai_ocr and ai_provider:
        try:
            kwargs: dict = {}
            if ai_model:
                kwargs["model"] = ai_model
            if ai_api_key:
                kwargs["api_key"] = ai_api_key
            provider = get_ai_provider(ai_provider, **kwargs)
            if provider.is_available():
                ocr_engine = OCREngine(ai_provider=provider, use_ai=True)
                print(f"      AI OCR provider: {ai_provider} ({ai_model or 'default model'})")
            else:
                print(
                    f"      [WARN] AI provider '{ai_provider}' not available "
                    "(missing API key or package). Falling back to pytesseract."
                )
                ocr_engine = OCREngine(ai_provider=None, use_ai=False)
        except (ValueError, ImportError) as exc:
            logging.warning("Could not initialise AI provider: %s", exc)
            ocr_engine = OCREngine(ai_provider=None, use_ai=False)
    elif use_ai_ocr:
        print("      [WARN] --use-ai-ocr set but no --ai-provider given. Using pytesseract.")
        ocr_engine = OCREngine(ai_provider=None, use_ai=False)
    else:
        ocr_engine = OCREngine(ai_provider=None, use_ai=False)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else ["remarkable"]

    exporter = ObsidianExporter(
        vault_dir=vault_dir,
        backup_dir=backup_dir,
        ocr_engine=ocr_engine,
        tags=tag_list,
        embed_images=embed_images,
    )

    # Discover notebooks and their folder paths
    all_items = find_notebooks(backup_dir)
    if not all_items:
        print("      No notebooks found in backup directory.")
        return 0

    org = organize_notebooks_by_structure(all_items, backup_dir)
    notebooks = org["documents_to_convert"]

    # Filter to only updated notebooks (unless force export)
    if not force_export and updated_uuids and not skip_backup:
        notebooks = [n for n in notebooks if n["uuid"] in updated_uuids]

    exported, skipped = exporter.export_all(
        notebooks=notebooks,
        pdf_output_dir=pdf_output_dir,
        force=force_export,
    )

    print(f"      ✓ Exported {exported} notes, {skipped} skipped")
    print(f"\n[SUCCESS] Obsidian sync complete → {vault_dir}")
    return 0
