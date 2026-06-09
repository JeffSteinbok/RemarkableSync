"""Utility modules for RemarkableSync."""

import logging as _logging
from pathlib import Path
from typing import Iterable

_ILLEGAL_FS_CHARS = set('\\/:*?"<>|\x00')


def sanitize_name(name: str) -> str:
    """Return a filesystem-safe version of *name*.

    Replaces only characters that are illegal on Windows/NTFS (the most
    restrictive common filesystem): ``\\ / : * ? " < > |`` and null.
    Everything else — spaces, parentheses, ampersands, dots, etc. — is kept.
    Leading/trailing whitespace is stripped.
    """
    return "".join("-" if c in _ILLEGAL_FS_CHARS else c for c in name).strip()


def write_manifest(path: Path, items: Iterable, label: str) -> None:
    """Write *items* one-per-line to *path* and log a debug entry.

    Used by each pipeline stage to emit a diagnostic manifest of what it
    produced during the run.  Files are always overwritten.
    """
    lines = [str(i) for i in items]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        _logging.debug("Wrote %s manifest (%d entries): %s", label, len(lines), path)
    except OSError as exc:
        _logging.warning("Could not write %s manifest: %s", label, exc)
