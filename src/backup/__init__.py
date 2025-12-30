"""
Backup package for ReMarkable tablet backup functionality.

This package provides modular components for backing up ReMarkable tablets,
including SSH connection management, file metadata handling, and backup orchestration.
"""

from .backup_manager import ReMarkableBackup
from .connection import ReMarkableConnection
from .metadata import FileMetadata

__all__ = ["ReMarkableConnection", "FileMetadata", "ReMarkableBackup"]
