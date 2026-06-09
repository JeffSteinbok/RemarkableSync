"""OCR engine for extracting text from ReMarkable notebook PDFs.

Strategy
--------
1. Convert PDF pages to PNG images using PyMuPDF (preferred) or pdf2image/Poppler.
2. If an AI provider is configured, send the images to the provider for
   vision-based handwriting transcription (much better quality).
3. Fallback: run ``pytesseract`` locally for offline OCR.

External dependencies (all optional – graceful degradation if missing):
- ``PyMuPDF`` (``pip install pymupdf``) – recommended, no system deps
- ``pdf2image``  + Poppler system package (legacy fallback)
- ``pytesseract``  + Tesseract system package
- ``Pillow``
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from ..ai.base_provider import BaseAIProvider


class OCREngine:
    """Extract text from notebook PDF files using AI or local OCR."""

    def __init__(
        self,
        ai_provider: Optional[BaseAIProvider] = None,
        use_ai: bool = True,
        image_dpi: int = 150,
        min_confidence: float = 0.3,
    ):
        """Initialise the OCR engine.

        Args:
            ai_provider: Configured AI provider instance.  When *None* or not
                available the engine falls back to pytesseract.
            use_ai: When *False* skip AI even if a provider is configured and
                always use pytesseract.
            image_dpi: Resolution used when rasterising PDF pages.  Higher
                values improve OCR quality at the cost of memory / speed.
            min_confidence: Minimum pytesseract confidence (0–1) to include a
                word in the output.  Words below this threshold are discarded.
        """
        self.ai_provider = ai_provider
        self.use_ai = use_ai and ai_provider is not None and ai_provider.is_available()
        self.image_dpi = image_dpi
        self.min_confidence = min_confidence

    # ------------------------------------------------------------------
    # PDF → images
    # ------------------------------------------------------------------

    def pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """Rasterise every page of *pdf_path* to a PNG file.

        Tries PyMuPDF first (pure pip, no system deps), then falls back to
        pdf2image + Poppler.

        Args:
            pdf_path: Path to the source PDF.
            output_dir: Directory where page images are written.

        Returns:
            Ordered list of image paths; empty list when neither renderer
            is available or conversion fails.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try PyMuPDF first (preferred — no system dependencies)
        images = self._pdf_to_images_pymupdf(pdf_path, output_dir)
        if images:
            return images

        # Fallback to pdf2image + Poppler
        return self._pdf_to_images_pdf2image(pdf_path, output_dir)

    def _pdf_to_images_pymupdf(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """Rasterise PDF using PyMuPDF (fitz)."""
        try:
            import fitz  # type: ignore  # PyMuPDF
        except ImportError:
            logging.debug("PyMuPDF not installed, trying pdf2image fallback.")
            return []

        try:
            doc = fitz.open(str(pdf_path))
            image_paths: List[Path] = []
            zoom = self.image_dpi / 72.0  # PDF default is 72 DPI
            matrix = fitz.Matrix(zoom, zoom)

            for idx, page in enumerate(doc, start=1):
                pix = page.get_pixmap(matrix=matrix)
                img_path = output_dir / f"page_{idx:03d}.png"
                pix.save(str(img_path))
                image_paths.append(img_path)

            doc.close()
            logging.debug("PyMuPDF rasterised %d pages from %s", len(image_paths), pdf_path.name)
            return image_paths
        except Exception as exc:  # noqa: BLE001
            logging.error("PyMuPDF failed for %s: %s", pdf_path.name, exc)
            return []

    def _pdf_to_images_pdf2image(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """Rasterise PDF using pdf2image + Poppler (legacy fallback)."""
        try:
            from pdf2image import convert_from_path  # type: ignore
        except ImportError:
            logging.warning(
                "Neither PyMuPDF nor pdf2image is installed – cannot rasterise PDF. "
                "Run: pip install pymupdf  (recommended)"
            )
            return []

        try:
            pages = convert_from_path(str(pdf_path), dpi=self.image_dpi)
            image_paths: List[Path] = []
            for idx, page in enumerate(pages, start=1):
                img_path = output_dir / f"page_{idx:03d}.png"
                page.save(str(img_path), "PNG")
                image_paths.append(img_path)
            logging.debug("pdf2image rasterised %d pages from %s", len(image_paths), pdf_path.name)
            return image_paths
        except Exception as exc:  # noqa: BLE001
            logging.error("pdf2image failed for %s: %s", pdf_path.name, exc)
            return []

    # ------------------------------------------------------------------
    # pytesseract fallback
    # ------------------------------------------------------------------

    def _ocr_with_pytesseract(self, image_paths: List[Path]) -> Tuple[str, float]:
        """Run pytesseract on *image_paths*.

        Returns:
            Tuple of ``(combined_text, average_confidence)`` where confidence
            is in the range 0–1.  Returns ``("", 0.0)`` when pytesseract is
            not available.
        """
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError:
            logging.debug("pytesseract or Pillow not available")
            return "", 0.0

        pages_text: List[str] = []
        confidence_values: List[float] = []

        for img_path in image_paths:
            if not img_path.exists():
                continue
            try:
                img = Image.open(img_path)
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                words = [
                    word
                    for word, conf in zip(data["text"], data["conf"], strict=False)
                    if word.strip() and int(conf) / 100.0 >= self.min_confidence
                ]
                confs = [
                    int(conf) / 100.0
                    for conf in data["conf"]
                    if int(conf) / 100.0 >= self.min_confidence
                ]
                pages_text.append(" ".join(words))
                confidence_values.extend(confs)
            except Exception as exc:  # noqa: BLE001
                logging.debug("pytesseract error on %s: %s", img_path.name, exc)

        combined = "\n\n".join(p for p in pages_text if p)
        avg_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        return combined, avg_conf

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(
        self,
        pdf_path: Path,
        notebook_name: str = "",
        page_pdfs: Optional[List[Path]] = None,
        on_page_done: Optional[callable] = None,
    ) -> Tuple[str, str]:
        """Extract text from a notebook PDF.

        Args:
            pdf_path: Path to the converted notebook PDF.
            notebook_name: Human-readable name used as context for the AI.
            page_pdfs: Optional list of individual per-page PDF paths.
            on_page_done: Callback ``(page_num, total_pages)`` called after
                each page is rasterised.

        Returns:
            ``(raw_text, processed_text)`` tuple.
        """
        if not page_pdfs and not pdf_path.exists():
            logging.warning("PDF not found for OCR: %s", pdf_path)
            return "", ""

        with tempfile.TemporaryDirectory(prefix="rs_ocr_") as tmp_str:
            tmp_dir = Path(tmp_str)

            if page_pdfs:
                total = len(page_pdfs)
            else:
                # Rasterise the merged PDF once to find page count
                page_pdfs = None  # will use merged path below
                total = 1

            # --- AI path (per-page) --------------------------------------
            if self.use_ai and self.ai_provider:
                logging.info(
                    "Running AI handwriting recognition for '%s'", notebook_name
                )
                all_raw_parts: List[str] = []

                if page_pdfs:
                    for idx, pp in enumerate(page_pdfs, start=1):
                        if not pp.exists():
                            continue
                        page_images = self.pdf_to_images(pp, tmp_dir / f"page_{idx:03d}")
                        if page_images:
                            raw_part = self.ai_provider.transcribe_handwriting(
                                page_images, context=f"{notebook_name} (page {idx})"
                            )
                            if raw_part:
                                all_raw_parts.append(raw_part)
                        if on_page_done:
                            on_page_done(idx, total)
                else:
                    all_images = self.pdf_to_images(pdf_path, tmp_dir)
                    if all_images:
                        raw_part = self.ai_provider.transcribe_handwriting(
                            all_images, context=notebook_name
                        )
                        if raw_part:
                            all_raw_parts.append(raw_part)
                    if on_page_done:
                        on_page_done(1, 1)

                if all_raw_parts:
                    raw = "\n\n".join(all_raw_parts)
                    processed = self.ai_provider.cleanup_text(raw, context=notebook_name)
                    return raw, processed

                logging.warning(
                    "AI transcription returned empty result for '%s'",
                    notebook_name,
                )
                return "", ""

            # --- Non-AI path: rasterise all then pytesseract -------------
            image_paths: List[Path] = []
            if page_pdfs:
                for idx, pp in enumerate(page_pdfs, start=1):
                    if not pp.exists():
                        continue
                    page_images = self.pdf_to_images(pp, tmp_dir / f"page_{idx:03d}")
                    image_paths.extend(page_images)
                    if on_page_done:
                        on_page_done(idx, total)
            else:
                image_paths = self.pdf_to_images(pdf_path, tmp_dir)
                if on_page_done:
                    on_page_done(1, 1)

            if not image_paths:
                return "", ""

            logging.info(
                "Running pytesseract OCR for '%s'", notebook_name
            )
            raw, confidence = self._ocr_with_pytesseract(image_paths)
            logging.info(
                "pytesseract confidence for '%s': %.0f%%",
                notebook_name,
                confidence * 100,
            )
            return raw, raw
