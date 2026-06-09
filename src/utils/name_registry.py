"""Stable sanitized-name registry for RemarkableSync output paths.

Maps each item UUID to a sanitized filesystem name that is:
- Stable across runs (reuses the same name as long as the raw name is unchanged)
- Unique within its parent context (siblings that collide get ``(1)``, ``(2)`` suffixes)
- Updated when the raw name changes (rename on the tablet generates a new sanitized name;
  old output files are left as orphans to be cleaned up separately)

The registry is persisted to ``name_registry.json`` inside the backup directory and is
shared by both the PDF converter and the Markdown exporter so names are consistent.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from . import sanitize_name


class NameRegistry:
    """Persistent registry that assigns stable, unique sanitized names to items by UUID.

    Usage::

        registry = NameRegistry(backup_dir)
        safe = registry.get_or_assign(uuid, raw_name, parent_uuid)
        # ... do output work ...
        registry.save()
    """

    FILE_NAME = "name_registry.json"

    def __init__(self, backup_dir: Path) -> None:
        self._path = backup_dir / self.FILE_NAME
        # uuid → {raw_name, sanitized_name, parent_uuid}
        self._data: Dict[str, Dict[str, str]] = self._load()
        # parent_uuid → set of sanitized names already in use under that parent
        self._used: Dict[str, set] = {}
        for entry in self._data.values():
            parent = entry.get("parent_uuid", "")
            sname = entry.get("sanitized_name", "")
            if sname:
                self._used.setdefault(parent, set()).add(sname)

    def _load(self) -> Dict[str, Dict[str, str]]:
        if not self._path.exists():
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Could not load name registry: %s", exc)
            return {}

    def save(self) -> None:
        """Persist the registry to disk."""
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, sort_keys=True)
        except OSError as exc:
            logging.error("Failed to save name registry: %s", exc)

    def get_or_assign(
        self,
        uuid: str,
        raw_name: str,
        parent_uuid: str,
    ) -> str:
        """Return the stable sanitized name for *uuid*.

        If *raw_name* is unchanged since the last run the previously assigned
        sanitized name (including any ``(1)``/``(2)`` suffix) is returned as-is.
        If *raw_name* has changed a new unique sanitized name is generated.

        Args:
            uuid: The item's UUID (notebook or folder).
            raw_name: The current ``visibleName`` from the tablet metadata.
            parent_uuid: UUID of the parent folder (empty string for root-level items).

        Returns:
            A sanitized, unique-within-parent name suitable for use as a
            filesystem path component.
        """
        existing = self._data.get(uuid)
        if existing and existing.get("raw_name") == raw_name:
            return existing["sanitized_name"]

        base = sanitize_name(raw_name) or f"item-{uuid[:8]}"

        used = self._used.setdefault(parent_uuid, set())

        # Release the old name from this uuid's slot so it can be reused
        if existing:
            old_sname = existing.get("sanitized_name", "")
            old_parent = existing.get("parent_uuid", "")
            if old_sname:
                self._used.get(old_parent, set()).discard(old_sname)

        candidate = base
        n = 1
        while candidate in used:
            candidate = f"{base} ({n})"
            n += 1

        used.add(candidate)
        self._data[uuid] = {
            "raw_name": raw_name,
            "sanitized_name": candidate,
            "parent_uuid": parent_uuid,
        }
        return candidate

    def get(self, uuid: str) -> Optional[str]:
        """Return the currently registered sanitized name for *uuid*, or None."""
        entry = self._data.get(uuid)
        return entry["sanitized_name"] if entry else None
