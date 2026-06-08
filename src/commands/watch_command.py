"""watch command – run sync (or obsidian-sync) on a periodic schedule.

Uses a file-based lock to prevent overlapping runs and implements
exponential back-off on consecutive failures.
"""

import fcntl
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ..utils.logging import setup_logging

# Back-off parameters
_INITIAL_BACKOFF = 60       # seconds
_MAX_BACKOFF = 3600         # 1 hour
_BACKOFF_FACTOR = 2


class FileLock:
    """Simple advisory file lock using ``fcntl``."""

    def __init__(self, lock_path: Path):
        self._lock_path = lock_path
        self._fh = None

    def acquire(self) -> bool:
        """Try to acquire the lock.

        Returns:
            *True* if acquired, *False* if already held by another process.
        """
        try:
            self._fh = open(self._lock_path, "w", encoding="utf-8")
            fcntl.flock(self._fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fh.write(f"{datetime.now(timezone.utc).isoformat()}\n")
            self._fh.flush()
            return True
        except OSError:
            if self._fh:
                self._fh.close()
                self._fh = None
            return False

    def release(self) -> None:
        if self._fh:
            try:
                fcntl.flock(self._fh, fcntl.LOCK_UN)
            except OSError:
                pass
            self._fh.close()
            self._fh = None
            try:
                self._lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def _format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def run_watch_command(
    interval: int,
    backup_dir: Path,
    run_once: Callable[[], int],
    verbose: bool,
    mode: str = "sync",
) -> int:
    """Run *run_once* repeatedly every *interval* seconds.

    Args:
        interval: Seconds between sync attempts.
        backup_dir: Backup directory (used for lock-file placement).
        run_once: Callable that performs one sync pass and returns an exit
                  code (0 = success, non-zero = failure).
        verbose: Enable debug logging.
        mode: Human-readable mode label shown in log messages.

    Returns:
        Exit code; only returns when interrupted with Ctrl-C (returns 0).
    """
    setup_logging(verbose)

    lock_path = backup_dir / ".remarkable_watch.lock"
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"ReMarkable Watch ({mode})")
    print("=" * 40)
    print(f"Interval   : every {_format_interval(interval)}")
    print(f"Backup dir : {backup_dir.absolute()}")
    print("Press Ctrl-C to stop.\n")

    consecutive_failures = 0
    current_backoff = 0

    try:
        while True:
            # Apply back-off if there were recent failures
            if current_backoff > 0:
                logging.warning(
                    "Backing off for %s after %d consecutive failure(s).",
                    _format_interval(current_backoff),
                    consecutive_failures,
                )
                time.sleep(current_backoff)

            # Acquire lock
            lock = FileLock(lock_path)
            if not lock.acquire():
                logging.warning(
                    "Another sync is already running (lock file exists). Skipping this cycle."
                )
                time.sleep(interval)
                continue

            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"[{ts}] Starting {mode}…")

            try:
                exit_code = run_once()
                if exit_code == 0:
                    consecutive_failures = 0
                    current_backoff = 0
                    ts2 = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    print(f"[{ts2}] ✓ {mode} succeeded. Next run in {_format_interval(interval)}.\n")
                else:
                    consecutive_failures += 1
                    current_backoff = min(
                        _INITIAL_BACKOFF * (_BACKOFF_FACTOR ** (consecutive_failures - 1)),
                        _MAX_BACKOFF,
                    )
                    logging.error(
                        "%s failed (exit code %d). Failures: %d.",
                        mode,
                        exit_code,
                        consecutive_failures,
                    )
            except Exception as exc:  # noqa: BLE001
                consecutive_failures += 1
                current_backoff = min(
                    _INITIAL_BACKOFF * (_BACKOFF_FACTOR ** (consecutive_failures - 1)),
                    _MAX_BACKOFF,
                )
                logging.error("Unexpected error during %s: %s", mode, exc)
            finally:
                lock.release()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[STOPPED] Watch mode stopped by user.")
        return 0
