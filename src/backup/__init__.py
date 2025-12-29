"""
Backup package for ReMarkable tablet backup functionality.

This package provides modular components for backing up ReMarkable tablets,
including SSH connection management, file metadata handling, and backup orchestration.
"""

from .connection import ReMarkableConnection
from .metadata import FileMetadata
from .backup_manager import ReMarkableBackup

__all__ = ['ReMarkableConnection', 'FileMetadata', 'ReMarkableBackup']
