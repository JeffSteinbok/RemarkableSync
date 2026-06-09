"""Utility modules for RemarkableSync."""

import logging as _logging
import subprocess as _subprocess
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


def run_shell_command(cmd: str) -> int:
    """Run *cmd* as a shell command and return its exit code.

    Output (stdout/stderr) is streamed to the console so the user can see
    progress from long-running pre/post-sync scripts.  The command is run
    via the system shell (``shell=True``) so shell features like ``&&``,
    environment variable expansion, and quoting are supported.

    Args:
        cmd: Shell command string to execute.

    Returns:
        Exit code of the command (0 = success).
    """
    _logging.debug("Running shell command: %s", cmd)
    try:
        result = _subprocess.run(cmd, shell=True)  # noqa: S602
        return result.returncode
    except Exception as exc:  # noqa: BLE001
        _logging.error("Shell command failed: %s", exc)
        return 1
