"""
File metadata management for incremental sync.

Manages file modification times, sizes, and checksums to enable
efficient incremental backups by only copying changed files.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


class FileMetadata:
    """Manages file metadata for incremental sync.

    Stores and manages file modification times, sizes, and checksums
    to enable efficient incremental backups by only copying changed files.
    """

    def __init__(self, metadata_file: Path):
        """Initialize metadata manager.

        Args:
            metadata_file: Path to JSON file storing sync metadata
        """
        self.metadata_file = metadata_file
        self.data = {}
        self.load()

    def load(self):
        """Load metadata from JSON file.

        Handles missing files and JSON parsing errors gracefully
        by initializing empty metadata dictionary.
        """
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logging.warning("Failed to load metadata: %s", e)
                self.data = {}

    def save(self):
        """Save metadata to JSON file.

        Creates parent directories if needed and writes metadata
        with proper formatting and error handling.
        """
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except (OSError, TypeError) as e:
            logging.error("Failed to save metadata: %s", e)

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for integrity verification.

        Reads file in chunks to handle large files efficiently
        and avoid loading entire file into memory.

        Args:
            file_path: Path to file to hash

        Returns:
            str: MD5 hash hexdigest, empty string on error
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except OSError:
            return ""
        return hash_md5.hexdigest()

    def should_sync_file(self, remote_file: Dict, local_path: Path) -> bool:
        """Determine if file needs to be synced based on metadata comparison.

        Compares remote file metadata with stored local metadata to decide
        if the file has changed and needs to be re-downloaded.

        Args:
            remote_file: Dictionary with remote file metadata (path, mtime, size)
            local_path: Local path where file would be stored

        Returns:
            bool: True if file should be synced, False if up-to-date
        """
        remote_path = remote_file["path"]

        # File doesn't exist locally
        if not local_path.exists():
            return True

        # Check if we have metadata for this file
        if remote_path not in self.data:
            return True

        stored_mtime = self.data[remote_path].get("mtime", 0)
        stored_size = self.data[remote_path].get("size", 0)

        # Check if remote file has changed
        if remote_file["mtime"] != stored_mtime or remote_file["size"] != stored_size:
            return True

        # Verify local file integrity
        current_hash = self.get_file_hash(local_path)
        stored_hash = self.data[remote_path].get("hash", "")

        return current_hash != stored_hash

    def update_file_metadata(self, remote_file: Dict, local_path: Path):
        """Update metadata for synced file with current information.

        Stores file metadata including modification time, size, hash,
        and sync timestamp for future incremental sync operations.

        Args:
            remote_file: Dictionary with remote file metadata
            local_path: Local path of the synced file
        """
        file_hash = self.get_file_hash(local_path)
        self.data[remote_file["path"]] = {
            "mtime": remote_file["mtime"],
            "size": remote_file["size"],
            "hash": file_hash,
            "last_sync": datetime.now(timezone.utc).isoformat(),
        }
