"""OCR engine for extracting text from ReMarkable notebook PDFs.

Strategy
--------
1. Convert PDF pages to PNG images using ``pdf2image`` / Poppler.
2. If an AI provider is configured, send the images to the provider for
   vision-based handwriting transcription (much better quality).
3. Fallback: run ``pytesseract`` locally for offline OCR.

External dependencies (all optional – graceful degradation if missing):
- ``pdf2image``  + Poppler system package (``brew install poppler`` /
  ``apt install poppler-utils``)
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

        Args:
            pdf_path: Path to the source PDF.
            output_dir: Directory where page images are written.

        Returns:
            Ordered list of image paths; empty list when pdf2image / Poppler
            is not available or conversion fails.
        """
        try:
            from pdf2image import convert_from_path  # type: ignore
        except ImportError:
            logging.warning(
                "pdf2image not installed – cannot rasterise PDF. "
                "Run: pip install pdf2image  and install Poppler."
            )
            return []

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            pages = convert_from_path(str(pdf_path), dpi=self.image_dpi)
            image_paths: List[Path] = []
            for idx, page in enumerate(pages, start=1):
                img_path = output_dir / f"page_{idx:03d}.png"
                page.save(str(img_path), "PNG")
                image_paths.append(img_path)
            logging.debug("Rasterised %d pages from %s", len(image_paths), pdf_path.name)
            return image_paths
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to convert PDF to images (%s): %s", pdf_path.name, exc)
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
                    for word, conf in zip(data["text"], data["conf"])
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
    ) -> Tuple[str, str]:
        """Extract text from a notebook PDF.

        Tries AI-based handwriting recognition first (if configured), then
        falls back to pytesseract.

        Args:
            pdf_path: Path to the converted notebook PDF.
            notebook_name: Human-readable name used as context for the AI.

        Returns:
            ``(raw_text, processed_text)`` tuple.  *processed_text* has been
            cleaned and formatted by the AI when AI is available; otherwise it
            equals *raw_text*.  Both strings are empty on complete failure.
        """
        if not pdf_path.exists():
            logging.warning("PDF not found for OCR: %s", pdf_path)
            return "", ""

        with tempfile.TemporaryDirectory(prefix="rs_ocr_") as tmp_str:
            tmp_dir = Path(tmp_str)
            image_paths = self.pdf_to_images(pdf_path, tmp_dir)

            if not image_paths:
                return "", ""

            # --- AI path -------------------------------------------------
            if self.use_ai and self.ai_provider:
                logging.info(
                    "Running AI handwriting recognition for '%s'", notebook_name
                )
                raw = self.ai_provider.transcribe_handwriting(
                    image_paths, context=notebook_name
                )
                if raw:
                    processed = self.ai_provider.cleanup_text(raw, context=notebook_name)
                    return raw, processed
                logging.warning(
                    "AI transcription returned empty result for '%s', "
                    "falling back to pytesseract",
                    notebook_name,
                )

            # --- pytesseract fallback ------------------------------------
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
