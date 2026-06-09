"""watch command – run sync or Markdown export on a periodic schedule.

Uses a file-based lock to prevent overlapping runs and implements
exponential back-off on consecutive failures.
"""

import fcntl
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..utils.logging import setup_logging

# Back-off parameters
_INITIAL_BACKOFF = 60       # seconds
_MAX_BACKOFF = 3600         # 1 hour
_BACKOFF_FACTOR = 2


class _WatchTray:
    """Best-effort system tray icon for watch mode."""

    def __init__(self, mode: str, enabled: bool):
        self._mode = mode
        self._enabled = enabled
        self._icon = None

    def _build_icon_image(self, color: str):
        """Create a small circular tray icon image."""
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill=color)
        draw.ellipse((20, 20, 44, 44), fill=(255, 255, 255, 190))
        return image

    def start(self) -> None:
        if not self._enabled:
            return

        try:
            import pystray
        except Exception as exc:  # noqa: BLE001
            logging.info("System tray disabled (pystray unavailable): %s", exc)
            return

        try:
            self._icon = pystray.Icon(
                "remarkablesync-watch",
                self._build_icon_image("#4A90E2"),
                title=f"RemarkableSync ({self._mode})",
            )
            if hasattr(self._icon, "run_detached"):
                self._icon.run_detached()
            else:
                thread = threading.Thread(target=self._icon.run, daemon=True)
                thread.start()
            self.set_status("Idle")
        except Exception as exc:  # noqa: BLE001
            logging.info("System tray disabled (unable to initialize): %s", exc)
            self._icon = None

    def set_status(self, status: str) -> None:
        if not self._icon:
            return

        colors = {
            "Idle": "#4A90E2",
            "Running": "#FFD166",
            "Success": "#06D6A0",
            "Failure": "#EF476F",
            "Backoff": "#F97316",
            "Stopped": "#9CA3AF",
        }
        color = colors.get(status, "#4A90E2")

        try:
            self._icon.icon = self._build_icon_image(color)
            self._icon.title = f"RemarkableSync ({self._mode}) - {status}"
        except Exception as exc:  # noqa: BLE001
            logging.debug("Unable to update tray icon: %s", exc)

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:  # noqa: BLE001
                pass
            self._icon = None


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
    log_level: str = "WRN",
    mode: str = "sync",
    use_systray: bool = True,
) -> int:
    """Run *run_once* repeatedly every *interval* seconds.

    Args:
        interval: Seconds between sync attempts.
        backup_dir: Backup directory (used for lock-file placement).
        run_once: Callable that performs one sync pass and returns an exit
                  code (0 = success, non-zero = failure).
        verbose: Enable debug logging.
        mode: Human-readable mode label shown in log messages.
        use_systray: Enable a best-effort system tray status icon.

    Returns:
        Exit code; only returns when interrupted with Ctrl-C (returns 0).
    """
    setup_logging(log_level)
    tray = _WatchTray(mode=mode, enabled=use_systray)
    tray.start()

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
                tray.set_status("Backoff")
                logging.warning(
                    "Backing off for %s after %d consecutive failure(s).",
                    _format_interval(current_backoff),
                    consecutive_failures,
                )
                time.sleep(current_backoff)

            # Acquire lock
            lock = FileLock(lock_path)
            if not lock.acquire():
                tray.set_status("Idle")
                logging.warning(
                    "Another sync is already running (lock file exists). Skipping this cycle."
                )
                time.sleep(interval)
                continue

            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"[{ts}] Starting {mode}...")
            tray.set_status("Running")

            try:
                exit_code = run_once()
                if exit_code == 0:
                    tray.set_status("Success")
                    consecutive_failures = 0
                    current_backoff = 0
                    ts2 = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    print(f"[{ts2}] [OK] {mode} succeeded. Next run in {_format_interval(interval)}.\n")
                else:
                    tray.set_status("Failure")
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
                tray.set_status("Failure")
                consecutive_failures += 1
                current_backoff = min(
                    _INITIAL_BACKOFF * (_BACKOFF_FACTOR ** (consecutive_failures - 1)),
                    _MAX_BACKOFF,
                )
                logging.error("Unexpected error during %s: %s", mode, exc)
            finally:
                lock.release()
                tray.set_status("Idle")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[STOPPED] Watch mode stopped by user.")
        tray.set_status("Stopped")
        tray.stop()
        return 0
