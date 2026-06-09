"""Markdown exporter for RemarkableSync.

Converts backed-up ReMarkable notebooks into Markdown files, optionally
enriched with AI-transcribed handwriting text and embedded page-image
attachments.

Output structure (inside the output directory)::

    <output_dir>/
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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .ocr.ocr_engine import OCREngine

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
# Markdown exporter
# ---------------------------------------------------------------------------

class MarkdownExporter:
    """Export ReMarkable notebooks as Markdown notes.

    Tracks which notebooks have already been exported (via a JSON state
    file) and skips notebooks whose PDF has not changed since the last
    export, enabling efficient incremental syncs.
    """

    STATE_FILE_NAME = "obsidian_export_state.json"

    def __init__(
        self,
        output_dir: Path,
        backup_dir: Path,
        ocr_engine: Optional[OCREngine] = None,
        tags: Optional[List[str]] = None,
        embed_images: bool = True,
    ):
        """Initialise the exporter.

        Args:
            output_dir: Root directory of the Markdown output (or a
                sub-folder inside it).
            backup_dir: RemarkableSync backup directory (contains
                ``Notebooks/``, ``PDF/``, etc.).
            ocr_engine: Configured :class:`~src.ocr.ocr_engine.OCREngine`
                instance. When *None* the notes will not contain extracted
                text.
            tags: List of tags to add to every note's YAML frontmatter.
                Defaults to ``["remarkable"]``.
            embed_images: When *True*, copy page images to the output directory
                and embed them using wiki-style image links.
        """
        self.output_dir = output_dir
        self.backup_dir = backup_dir
        self.ocr_engine = ocr_engine
        self.tags = tags or ["remarkable"]
        self.embed_images = embed_images

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # State file lives in the backup dir, not the output directory
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
            logging.warning("Could not load Markdown export state: %s", exc)
            return {}

    def _save_state(self) -> None:
        try:
            with open(self._state_path, "w", encoding="utf-8") as fh:
                json.dump(self._state, fh, indent=2)
        except OSError as exc:
            logging.error("Failed to save Markdown export state: %s", exc)

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
        """Rasterise PDF pages and copy them into *images_dir/_images/*.

        Returns a list of paths suitable for embedded image links.
        """
        if not self.embed_images:
            return []
        if not pdf_path.exists():
            return []

        target_dir = images_dir / "_images"
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            from pdf2image import convert_from_path  # type: ignore

            pages = convert_from_path(str(pdf_path), dpi=150)
            image_paths: List[Path] = []
            for idx, page in enumerate(pages, start=1):
                dest = target_dir / f"page_{idx:03d}.png"
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
        output_images_dir: Path,
    ) -> str:
        """Build the full Markdown content for one notebook."""
        lines: List[str] = []

        # Frontmatter
        lines.append(
            self._build_frontmatter(notebook_name, notebook_uuid, folder_path, self.tags)
        )

        # Transcribed text
        if processed_text.strip():
            lines.append(processed_text.strip())
            lines.append("\n\n")

        # Embedded page images
        if image_paths:
            lines.append("---\n\n## Pages\n\n")
            for img_path in image_paths:
                link = f"_images/{img_path.name}"
                lines.append(f"![{img_path.stem}]({link})\n\n")

        return "".join(lines)

    def _build_page_markdown(
        self,
        title: str,
        notebook_name: str,
        notebook_uuid: str,
        folder_path: str,
        page_num: int,
        page_text: str,
        page_image: Optional[Path] = None,
    ) -> str:
        """Build Markdown content for a single page."""
        lines: List[str] = []

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tag_lines = "\n".join(f"  - {t}" for t in self.tags)

        # Determine AI provider/model from OCR engine
        ai_provider = ""
        ai_model = ""
        if self.ocr_engine and self.ocr_engine.ai_provider:
            provider = self.ocr_engine.ai_provider
            ai_model = getattr(provider, "model", "")
            ai_provider = type(provider).__name__

        props = (
            "---\n"
            f"title: \"{title}\"\n"
            f"source: reMarkable\n"
            f"remarkable_id: {notebook_uuid}\n"
            f"notebook: {notebook_name}\n"
            f"folder: {folder_path or '/'}\n"
            f"page: {page_num}\n"
            f"created: {now}\n"
        )
        if ai_provider:
            props += f"ai_provider: {ai_provider}\n"
        if ai_model:
            props += f"ai_model: {ai_model}\n"
        props += f"tags:\n{tag_lines}\n---\n\n"
        lines.append(props)

        if page_text.strip():
            # Strip leading H1 if it matches the title (already in frontmatter)
            body = page_text.strip()
            first_line = body.split("\n", 1)[0].strip()
            if first_line.startswith("# ") and first_line[2:].strip().upper() == title.upper():
                body = body.split("\n", 1)[1].strip() if "\n" in body else ""
            if body:
                lines.append(body)
                lines.append("\n\n")

        if page_image and page_image.exists():
            link = f"_images/{page_image.name}"
            lines.append(f"![page {page_num}]({link})\n")

        return "".join(lines)

    @staticmethod
    def _extract_title(text: str, page_num: int) -> str:
        """Extract a title and optional date from OCR text.

        Returns format: ``YYYY-MM-DD - Title``, ``YYYY-MM-DD - Page N``,
        or ``Page N`` depending on what's found.
        """
        import re

        title = ""
        date_str = ""

        if text and text.strip():
            # Look for dates in common formats
            # Matches: 8/27/24, 08/27/2024, 2024-08-27, Aug 27, 2024, etc.
            date_patterns = [
                # YYYY-MM-DD
                (r'(\d{4})-(\d{1,2})-(\d{1,2})', lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
                # M/D/YY or MM/DD/YY
                (r'(\d{1,2})/(\d{1,2})/(\d{2})(?!\d)', lambda m: f"20{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
                # M/D/YYYY or MM/DD/YYYY
                (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"),
            ]
            for pattern, formatter in date_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        date_str = formatter(match)
                    except (ValueError, IndexError):
                        pass
                    break

            # Look for title: first heading or first short non-empty line
            for line in text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Skip lines that are just dates
                if re.match(r'^[_*]*\d{1,2}/\d{1,2}/\d{2,4}[_*]*$', line):
                    continue
                if re.match(r'^[_*]*\d{4}-\d{1,2}-\d{1,2}[_*]*$', line):
                    continue
                if line.startswith("#"):
                    candidate = line.lstrip("#").strip()
                    if candidate:
                        title = candidate
                        break
                elif len(line) < 80:
                    title = line
                    break

        # Build final title
        if date_str and title:
            return f"{date_str} - {title}"
        elif date_str:
            return f"{date_str} - Page {page_num}"
        elif title:
            return title
        else:
            return f"Page {page_num}"

    # ------------------------------------------------------------------
    # Export entry point
    # ------------------------------------------------------------------

    def export_notebook(
        self,
        notebook: Dict,
        pdf_path: Path,
        force: bool = False,
        page_pdfs: Optional[List[Path]] = None,
        on_page_done: Optional[callable] = None,
    ) -> Optional[Path]:
        """Export a notebook as a folder with one Markdown file per page.

        Args:
            notebook: Notebook metadata dict.
            pdf_path: Path to the converted PDF for this notebook.
            force: Re-export even if the notebook hasn't changed.
            page_pdfs: Optional list of cached per-page PDF paths.
            on_page_done: Callback ``(page_num, total_pages)`` called after
                each page is processed.

        Returns:
            Path to the notebook folder, or *None* on failure.
        """
        uuid = notebook["uuid"]
        name = notebook["name"]
        folder_path = notebook.get("folder_path", "")

        # Skip if nothing changed
        if not force and not self._needs_export(uuid, pdf_path):
            logging.debug("Skipping unchanged notebook: %s", name)
            return self._state.get(uuid, {}).get("md_path")

        safe = _safe_name(name) or f"notebook_{uuid[:8]}"

        # Notebook becomes a folder
        notebook_dir = self.output_dir
        if folder_path:
            for segment in folder_path.split("/"):
                notebook_dir = notebook_dir / _safe_name(segment)
        notebook_dir = notebook_dir / safe
        notebook_dir.mkdir(parents=True, exist_ok=True)

        # Determine pages to process
        pages_to_process: List[Path] = []
        if page_pdfs:
            pages_to_process = [p for p in page_pdfs if p.exists()]
        elif pdf_path.exists():
            pages_to_process = [pdf_path]

        if not pages_to_process:
            logging.warning("No PDFs found for notebook '%s'", name)
            return None

        total_pages = len(pages_to_process)


        with tempfile.TemporaryDirectory(prefix="rs_md_") as tmp_str:
            tmp_dir = Path(tmp_str)
            rate_limited = False

            for pg_idx, pg_pdf in enumerate(pages_to_process, start=1):
                # Rasterise page to image
                page_image: Optional[Path] = None
                page_images: List[Path] = []  # noqa: F841

                if self.embed_images:
                    images_dir = notebook_dir / "_images"
                    images_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        import fitz  # PyMuPDF
                        doc = fitz.open(str(pg_pdf))
                        for fitz_page in doc:
                            pix = fitz_page.get_pixmap(dpi=150)
                            dest = images_dir / f"page_{pg_idx:03d}.png"
                            pix.save(str(dest))
                            page_image = dest
                        doc.close()
                    except ImportError:
                        pass
                    except Exception as exc:
                        logging.warning("Image export failed for page %d: %s", pg_idx, exc)

                # OCR this page
                page_text = ""
                ocr_failed = False
                if self.ocr_engine and not rate_limited:
                    from src.ai.base_provider import AIProviderError, AIRateLimitError
                    from src.utils.console import print_error, print_warn

                    raster_images = self.ocr_engine.pdf_to_images(
                        pg_pdf, tmp_dir / f"ocr_page_{pg_idx:03d}"
                    )
                    if raster_images and self.ocr_engine.use_ai and self.ocr_engine.ai_provider:
                        try:
                            raw = self.ocr_engine.ai_provider.transcribe_handwriting(
                                raster_images, context=f"{name} (page {pg_idx})"
                            )
                            if raw:
                                page_text = self.ocr_engine.ai_provider.cleanup_text(
                                    raw, context=f"{name} (page {pg_idx})"
                                )
                        except AIRateLimitError as exc:
                            wait_min = (exc.retry_after + 59) // 60
                            logging.warning("Rate limited for '%s' page %d: %s", name, pg_idx, exc)
                            print_warn(
                                f"  [WARN] Rate limited — retry in ~{wait_min} min. "
                                f"Skipping OCR for remaining pages."
                            )
                            rate_limited = True
                            ocr_failed = True
                        except AIProviderError as exc:
                            logging.error("OCR failed for '%s' page %d: %s", name, pg_idx, exc)
                            print_error(f"  [ERR] OCR failed for '{name}' page {pg_idx}")
                            ocr_failed = True

                if ocr_failed:
                    if on_page_done:
                        on_page_done(pg_idx, total_pages)
                    continue

                # Derive title from OCR text
                title = self._extract_title(page_text, pg_idx)
                safe_title = _safe_name(title) or f"page_{pg_idx:03d}"

                # Build and write per-page Markdown
                md_content = self._build_page_markdown(
                    title=title,
                    notebook_name=name,
                    notebook_uuid=uuid,
                    folder_path=folder_path,
                    page_num=pg_idx,
                    page_text=page_text,
                    page_image=page_image,
                )

                md_path = notebook_dir / f"{safe_title}.md"
                try:
                    with open(md_path, "w", encoding="utf-8") as fh:
                        fh.write(md_content)
                except OSError as exc:
                    logging.error("Failed to write page %d of '%s': %s", pg_idx, name, exc)

                if on_page_done:
                    on_page_done(pg_idx, total_pages)

        logging.info("Exported notebook: %s (%d pages)", name, total_pages)
        self._record_export(uuid, pdf_path, notebook_dir)
        self._save_state()
        return notebook_dir

    def export_all(
        self,
        notebooks: List[Dict],
        pdf_output_dir: Path,
        force: bool = False,
        converted_pages: Optional[Dict[str, List[Path]]] = None,
        page_filter: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Export all notebooks to Markdown.

        Args:
            notebooks: List of notebook metadata dicts.
            pdf_output_dir: Directory containing the converted PDFs (mirrors
                the folder hierarchy).
            force: Re-export all notebooks regardless of change status.
            converted_pages: Dict mapping notebook UUID to list of per-page
                PDF paths produced by the PDF conversion step.  When provided,
                these are used directly instead of scanning the cache dir.

        Returns:
            ``(exported_count, skipped_count)`` tuple.
        """
        from .utils.console import create_progress

        exported = 0
        skipped = 0
        doc_notebooks = [nb for nb in notebooks if nb.get("type") == "DocumentType"]

        # Count total pages for progress bar
        total_pages = 0
        nb_page_counts = []
        for nb in doc_notebooks:
            count = 0
            if converted_pages and nb["uuid"] in converted_pages:
                count = len(converted_pages[nb["uuid"]])
            else:
                cache = self.backup_dir / "PagePDFs" / nb["uuid"]
                if cache.exists():
                    count = len([p for p in cache.glob("*.pdf")
                                 if not p.stem.endswith("_content")])
            count = max(count, 1)  # at least 1 so progress always advances
            nb_page_counts.append(count)
            total_pages += count

        with create_progress("Exporting") as progress:
            task = progress.add_task("Exporting", total=total_pages)

            for i, notebook in enumerate(doc_notebooks):
                nb_name = notebook["name"][:30]
                nb_pages = nb_page_counts[i]
                progress.update(
                    task,
                    description=f"{nb_name} (page 0 of {nb_pages})",
                )

                safe = _safe_name(notebook["name"]) or f"notebook_{notebook['uuid'][:8]}"
                folder_path = notebook.get("folder_path", "")

                # Locate the PDF produced by the converter
                pdf_dir = pdf_output_dir
                if folder_path:
                    for seg in folder_path.split("/"):
                        pdf_dir = pdf_dir / _safe_name(seg)
                pdf_path = pdf_dir / f"{safe}.pdf"

                # Use page PDFs from pipeline if available, else scan cache
                page_pdfs_list: Optional[List[Path]] = None
                if converted_pages and notebook["uuid"] in converted_pages:
                    page_pdfs_list = converted_pages[notebook["uuid"]]
                else:
                    page_cache_dir = self.backup_dir / "PagePDFs" / notebook["uuid"]
                    if page_cache_dir.exists():
                        pdfs = sorted(page_cache_dir.glob("*.pdf"))
                        pdfs = [p for p in pdfs if not p.stem.endswith("_content")]
                        if pdfs:
                            page_pdfs_list = pdfs

                # Filter to specific page if requested
                if page_filter and page_pdfs_list:
                    if page_filter <= len(page_pdfs_list):
                        page_pdfs_list = [page_pdfs_list[page_filter - 1]]
                    else:
                        logging.warning("Page %d not found (notebook has %d pages)",
                                        page_filter, len(page_pdfs_list))

                def _on_page(pg_num, pg_total, _nb_name=nb_name):
                    progress.update(
                        task, advance=1,
                        description=f"{_nb_name} (page {pg_num} of {pg_total})",
                    )
                    logging.info("MD: %s (page %d/%d)", _nb_name, pg_num, pg_total)

                result = self.export_notebook(
                    notebook, pdf_path, force=force, page_pdfs=page_pdfs_list,
                    on_page_done=_on_page,
                )
                # Ensure we advance the full count even if pages were fewer
                remaining = nb_pages - (nb_pages if result else 0)
                if remaining > 0:
                    progress.update(task, advance=remaining)

                if result:
                    exported += 1
                else:
                    # Advance for skipped notebooks too
                    progress.update(task, advance=nb_pages)
                    skipped += 1

        logging.info(
            "Markdown export complete: %d exported, %d skipped", exported, skipped
        )
        return exported, skipped
