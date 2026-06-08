"""Claude AI provider using the Anthropic API.

Requires the ``anthropic`` Python package and an ``ANTHROPIC_API_KEY``
environment variable (or the ``api_key`` constructor argument).
"""

import base64
import logging
import os
from pathlib import Path
from typing import List

from .base_provider import CLEANUP_PROMPT, TRANSCRIPTION_PROMPT, BaseAIProvider


class ClaudeProvider(BaseAIProvider):
    """AI provider backed by Anthropic Claude (vision + text models)."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, api_key: str = "", model: str = ""):
        """Initialise the Claude provider.

        Args:
            api_key: Anthropic API key.  Falls back to the
                ``ANTHROPIC_API_KEY`` environment variable when empty.
            model: Claude model identifier.  Defaults to
                ``claude-3-5-sonnet-20241022``.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self._client = None
        self._init_client()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        if not self.api_key:
            return
        try:
            import anthropic  # type: ignore

            self._client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            logging.warning(
                "anthropic package not installed – run: pip install anthropic"
            )

    def is_available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def transcribe_handwriting(self, image_paths: List[Path], context: str = "") -> str:
        """Send page images to Claude for handwriting recognition."""
        if not self.is_available():
            return ""

        content: list = []
        for img_path in image_paths:
            if not img_path.exists():
                continue
            with open(img_path, "rb") as fh:
                img_b64 = base64.standard_b64encode(fh.read()).decode("utf-8")
            media_type = (
                "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            )
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    },
                }
            )

        if not content:
            return ""

        prompt = TRANSCRIPTION_PROMPT
        if context:
            prompt += f"\n\nNotebook context: {context}"
        content.append({"type": "text", "text": prompt})

        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": content}],
            )
            return message.content[0].text
        except Exception as exc:  # noqa: BLE001
            logging.error("Claude transcription API error: %s", exc)
            return ""

    def cleanup_text(self, raw_text: str, context: str = "") -> str:
        """Ask Claude to clean up and structure raw transcribed text."""
        if not self.is_available() or not raw_text.strip():
            return raw_text

        prompt = CLEANUP_PROMPT
        if context:
            prompt += f"\n\nNotebook context: {context}"

        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n---\n{raw_text}",
                    }
                ],
            )
            return message.content[0].text
        except Exception as exc:  # noqa: BLE001
            logging.error("Claude cleanup API error: %s", exc)
            return raw_text
