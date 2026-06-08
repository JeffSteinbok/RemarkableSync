"""Obsidian Markdown exporter for RemarkableSync.

Converts backed-up ReMarkable notebooks into Obsidian-compatible Markdown
files, optionally enriched with AI-transcribed handwriting text and
embedded page-image attachments.

Output structure (inside the vault)::

    <vault_dir>/
        <folder_path>/
            <notebook_name>.md          ← Markdown note
            <notebook_name>/
                page_001.png            ← page images (attachments)
                page_002.png
                ...
"""

import hashlib
import json
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..ocr.ocr_engine import OCREngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """Return a filesystem-safe version of *name*."""
    return "".join(c for c in name if c.isalnum() or c in " -_()").strip()


def _file_hash(path: Path) -> str:
    """Return the MD5 hex-digest of *path*."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Obsidian exporter
# ---------------------------------------------------------------------------

class ObsidianExporter:
    """Export ReMarkable notebooks as Obsidian Markdown notes.

    Tracks which notebooks have already been exported (via a JSON state
    file) and skips notebooks whose PDF has not changed since the last
    export, enabling efficient incremental syncs.
    """

    STATE_FILE_NAME = "obsidian_export_state.json"

    def __init__(
        self,
        vault_dir: Path,
        backup_dir: Path,
        ocr_engine: Optional[OCREngine] = None,
        tags: Optional[List[str]] = None,
        embed_images: bool = True,
    ):
        """Initialise the exporter.

        Args:
            vault_dir: Root directory of the Obsidian vault (or a
                sub-folder inside it).
            backup_dir: RemarkableSync backup directory (contains
                ``Notebooks/``, ``PDF/``, etc.).
            ocr_engine: Configured :class:`~src.ocr.ocr_engine.OCREngine`
                instance.  When *None* the notes will not contain extracted
                text.
            tags: List of tags to add to every note's YAML frontmatter.
                Defaults to ``["remarkable"]``.
            embed_images: When *True*, copy page images to the vault and
                embed them using Obsidian ``![[file]]`` syntax.
        """
        self.vault_dir = vault_dir
        self.backup_dir = backup_dir
        self.ocr_engine = ocr_engine
        self.tags = tags or ["remarkable"]
        self.embed_images = embed_images

        self.vault_dir.mkdir(parents=True, exist_ok=True)

        # State file lives in the backup dir, not the vault
        self._state_path = backup_dir / self.STATE_FILE_NAME
        self._state: Dict[str, Dict] = self._load_state()

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _load_state(self) -> Dict[str, Dict]:
        if not self._state_path.exists():
            return {}
        try:
            with open(self._state_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Could not load Obsidian export state: %s", exc)
            return {}

    def _save_state(self) -> None:
        try:
            with open(self._state_path, "w", encoding="utf-8") as fh:
                json.dump(self._state, fh, indent=2)
        except OSError as exc:
            logging.error("Failed to save Obsidian export state: %s", exc)

    def _needs_export(self, notebook_uuid: str, pdf_path: Path) -> bool:
        """Return True if the notebook has changed since the last export."""
        if notebook_uuid not in self._state:
            return True
        if not pdf_path.exists():
            return False
        current_hash = _file_hash(pdf_path)
        return current_hash != self._state[notebook_uuid].get("pdf_hash", "")

    def _record_export(self, notebook_uuid: str, pdf_path: Path, md_path: Path) -> None:
        pdf_hash = _file_hash(pdf_path) if pdf_path.exists() else ""
        self._state[notebook_uuid] = {
            "pdf_hash": pdf_hash,
            "md_path": str(md_path),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Page image export
    # ------------------------------------------------------------------

    def _export_page_images(
        self,
        pdf_path: Path,
        images_dir: Path,
    ) -> List[Path]:
        """Rasterise PDF pages and copy them into *images_dir*.

        Returns a list of relative paths suitable for Obsidian ``![[…]]``
        links (relative to the vault root).
        """
        if not self.embed_images:
            return []
        if not pdf_path.exists():
            return []

        images_dir.mkdir(parents=True, exist_ok=True)

        # Use pdf2image if available
        try:
            from pdf2image import convert_from_path  # type: ignore

            pages = convert_from_path(str(pdf_path), dpi=150)
            image_paths: List[Path] = []
            for idx, page in enumerate(pages, start=1):
                dest = images_dir / f"page_{idx:03d}.png"
                page.save(str(dest), "PNG")
                image_paths.append(dest)
            return image_paths
        except ImportError:
            logging.debug("pdf2image not available – skipping page image export")
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to export page images from %s: %s", pdf_path.name, exc)

        return []

    # ------------------------------------------------------------------
    # Markdown building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_frontmatter(
        notebook_name: str,
        notebook_uuid: str,
        folder_path: str,
        tags: List[str],
    ) -> str:
        """Return a YAML frontmatter block."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tag_lines = "\n".join(f"  - {t}" for t in tags)
        return (
            "---\n"
            f"title: {notebook_name}\n"
            f"source: reMarkable\n"
            f"remarkable_id: {notebook_uuid}\n"
            f"folder: {folder_path or '/'}\n"
            f"created: {now}\n"
            f"tags:\n"
            f"{tag_lines}\n"
            "---\n\n"
        )

    def _build_markdown(
        self,
        notebook_name: str,
        notebook_uuid: str,
        folder_path: str,
        processed_text: str,
        image_paths: List[Path],
        vault_images_dir: Path,
    ) -> str:
        """Build the full Markdown content for one notebook."""
        lines: List[str] = []

        # Frontmatter
        lines.append(
            self._build_frontmatter(notebook_name, notebook_uuid, folder_path, self.tags)
        )

        # Title heading
        lines.append(f"# {notebook_name}\n\n")

        # Transcribed text
        if processed_text.strip():
            lines.append(processed_text.strip())
            lines.append("\n\n")

        # Embedded page images
        if image_paths:
            lines.append("---\n\n## Pages\n\n")
            for img_path in image_paths:
                # Obsidian wiki-link uses just the filename when the
                # attachment folder is configured; we use the relative path
                # from the vault root for robustness.
                try:
                    rel = img_path.relative_to(self.vault_dir)
                    link = str(rel).replace("\\", "/")
                except ValueError:
                    link = img_path.name
                lines.append(f"![[{link}]]\n\n")

        return "".join(lines)

    # ------------------------------------------------------------------
    # Export entry point
    # ------------------------------------------------------------------

    def export_notebook(
        self,
        notebook: Dict,
        pdf_path: Path,
        force: bool = False,
    ) -> Optional[Path]:
        """Export a single notebook to an Obsidian Markdown file.

        Args:
            notebook: Notebook metadata dict (same structure used by
                :func:`~src.hybrid_converter.find_notebooks`).
            pdf_path: Path to the converted PDF for this notebook.
            force: Re-export even if the notebook hasn't changed.

        Returns:
            Path to the created/updated Markdown file, or *None* on failure.
        """
        uuid = notebook["uuid"]
        name = notebook["name"]
        folder_path = notebook.get("folder_path", "")

        # Skip if nothing changed
        if not force and not self._needs_export(uuid, pdf_path):
            logging.debug("Skipping unchanged notebook: %s", name)
            return self._state.get(uuid, {}).get("md_path")

        safe = _safe_name(name) or f"notebook_{uuid[:8]}"

        # Resolve output directory inside the vault
        note_dir = self.vault_dir
        if folder_path:
            for segment in folder_path.split("/"):
                note_dir = note_dir / _safe_name(segment)
        note_dir.mkdir(parents=True, exist_ok=True)

        md_path = note_dir / f"{safe}.md"

        # Directory for embedded page images (sibling folder)
        images_dir = note_dir / safe

        # --- Extract text via OCR ----------------------------------------
        processed_text = ""
        if self.ocr_engine and pdf_path.exists():
            _raw, processed_text = self.ocr_engine.extract_text(pdf_path, name)

        # --- Export page images ------------------------------------------
        image_paths = self._export_page_images(pdf_path, images_dir)

        # --- Build and write Markdown ------------------------------------
        md_content = self._build_markdown(
            name, uuid, folder_path, processed_text, image_paths, images_dir
        )

        try:
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(md_content)
            logging.info("Exported note: %s", md_path)
        except OSError as exc:
            logging.error("Failed to write Markdown for '%s': %s", name, exc)
            return None

        self._record_export(uuid, pdf_path, md_path)
        self._save_state()
        return md_path

    def export_all(
        self,
        notebooks: List[Dict],
        pdf_output_dir: Path,
        force: bool = False,
    ) -> Tuple[int, int]:
        """Export all notebooks to Obsidian Markdown.

        Args:
            notebooks: List of notebook metadata dicts.
            pdf_output_dir: Directory containing the converted PDFs (mirrors
                the folder hierarchy).
            force: Re-export all notebooks regardless of change status.

        Returns:
            ``(exported_count, skipped_count)`` tuple.
        """
        exported = 0
        skipped = 0

        for notebook in notebooks:
            if notebook.get("type") != "DocumentType":
                continue

            safe = _safe_name(notebook["name"]) or f"notebook_{notebook['uuid'][:8]}"
            folder_path = notebook.get("folder_path", "")

            # Locate the PDF produced by the converter
            pdf_dir = pdf_output_dir
            if folder_path:
                for seg in folder_path.split("/"):
                    pdf_dir = pdf_dir / _safe_name(seg)
            pdf_path = pdf_dir / f"{safe}.pdf"

            result = self.export_notebook(notebook, pdf_path, force=force)
            if result:
                exported += 1
            else:
                skipped += 1

        logging.info(
            "Obsidian export complete: %d exported, %d skipped", exported, skipped
        )
        return exported, skipped
