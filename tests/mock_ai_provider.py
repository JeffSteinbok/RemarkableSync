"""
Mock AI provider for testing OCR pipeline without API keys.

Returns canned transcription results so the full pipeline can be
exercised in CI or local dev without network calls.
"""

from pathlib import Path
from typing import List

from src.ai.base_provider import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Fake AI provider that returns deterministic transcription results."""

    def __init__(self, transcription: str = "", cleanup: str = ""):
        """Initialize with canned responses.

        Args:
            transcription: Text to return from transcribe_handwriting().
                If empty, returns a default sample transcription.
            cleanup: Text to return from cleanup_text().
                If empty, returns the input with minor formatting.
        """
        self._transcription = transcription or (
            "# Meeting Notes\n\n"
            "- Review Q4 results\n"
            "- Discuss new product roadmap\n"
            "- Action: Jeff to send proposal\n"
            "- Next meeting: Thursday 2pm\n"
        )
        self._cleanup = cleanup
        self._transcribe_calls: List[List[Path]] = []
        self._cleanup_calls: List[str] = []

    def is_available(self) -> bool:
        return True

    def transcribe_handwriting(self, image_paths: List[Path], context: str = "") -> str:
        """Return canned transcription. Records call for assertion."""
        self._transcribe_calls.append(list(image_paths))
        return self._transcription

    def cleanup_text(self, raw_text: str, context: str = "") -> str:
        """Return canned cleanup or passthrough. Records call for assertion."""
        self._cleanup_calls.append(raw_text)
        if self._cleanup:
            return self._cleanup
        # Default: just add a header if not present
        if not raw_text.startswith("#"):
            return f"# Notes\n\n{raw_text}"
        return raw_text

    @property
    def transcribe_call_count(self) -> int:
        return len(self._transcribe_calls)

    @property
    def cleanup_call_count(self) -> int:
        return len(self._cleanup_calls)
