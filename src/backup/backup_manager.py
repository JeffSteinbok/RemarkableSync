"""
Backup Manager - Internal Helper Module

This is a helper module providing backup orchestration functionality.
Do not run directly - use RemarkableSync.py as the entry point.

Entry Point:
    RemarkableSync.py backup [OPTIONS]
    RemarkableSync.py sync [OPTIONS]

This module provides:
- SSH connection management to ReMarkable tablet
- File synchronization with incremental updates
- Metadata management and tracking
- Optional automatic PDF conversion after backup
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import paramiko
from scp import SCPException
from tqdm import tqdm

from .connection import ReMarkableConnection
from .metadata import FileMetadata


class ReMarkableBackup:  # pylint: disable=too-many-instance-attributes
    """Main backup orchestrator for ReMarkable tablet.

    Coordinates SSH connection, file synchronization, metadata management,
    and optional PDF conversion to provide a complete backup solution.

    Key features:
    - Incremental sync based on file modification times
    - Integrity verification using MD5 checksums
    - Automatic PDF conversion integration
    - Progress tracking and detailed logging
    """

    def __init__(self, backup_dir: Path, password: Optional[str] = None):
        """Initialize backup orchestrator.

        Args:
            backup_dir: Local directory to store backup files
            password: SSH password for tablet (prompted if not provided)
        """
        self.backup_dir = backup_dir
        self.files_dir = backup_dir / "Notebooks"  # Clean folder name
        self.pdfs_dir = backup_dir / "PDF"  # Clean folder name
        self.templates_dir = backup_dir / "Templates"  # Clean folder name
        self.metadata_file = backup_dir / "sync_metadata.json"

        # Create directories
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.connection = ReMarkableConnection(password=password)
        self.metadata = FileMetadata(self.metadata_file)

        # ReMarkable paths
        self.remote_xochitl_dir = "/home/root/.local/share/remarkable/xochitl"
        self.remote_templates_dir = "/usr/share/remarkable/templates"

    def backup_files(self) -> Tuple[bool, Set[str]]:  # pylint: disable=too-many-branches
        """Backup files from ReMarkable tablet.

        Returns:
            Tuple of (success, set of notebook UUIDs that were updated)
        """
        logging.info("Starting file backup...")

        if not self.connection.connect():
            return False, set()

        try:
            # Get list of remote files
            remote_files = self.connection.list_files(self.remote_xochitl_dir)

            if not remote_files:
                logging.warning("No files found on ReMarkable tablet")
                return True, set()

            # Filter files that need syncing
            files_to_sync = []
            for remote_file in remote_files:
                relative_path = os.path.relpath(remote_file["path"], self.remote_xochitl_dir)
                local_path = self.files_dir / relative_path

                if self.metadata.should_sync_file(remote_file, local_path):
                    files_to_sync.append((remote_file, local_path))

            if not files_to_sync:
                logging.info("All files are up to date")
                return True, set()

            logging.info("Syncing %d files...", len(files_to_sync))

            # Track which notebooks have been updated
            updated_notebooks = set()

            # Download files with progress bar
            with tqdm(total=len(files_to_sync), desc="Downloading") as pbar:
                for remote_file, local_path in files_to_sync:
                    try:
                        # Create local directory if needed
                        local_path.parent.mkdir(parents=True, exist_ok=True)

                        # Download file
                        if self.connection.scp_client is None:
                            logging.error("SCP client not initialized")
                            return False, set()
                        self.connection.scp_client.get(remote_file["path"], str(local_path))

                        # Update metadata
                        self.metadata.update_file_metadata(remote_file, local_path)

                        # Track notebook UUID if this file belongs to a notebook
                        # Handle both top-level files and files in subdirectories
                        relative_path = os.path.relpath(
                            remote_file["path"], self.remote_xochitl_dir
                        )
                        path_parts = relative_path.split(os.sep)

                        # Check if this is a notebook-related file
                        notebook_uuid = None
                        if len(path_parts) >= 1:
                            # Top-level files like uuid.metadata, uuid.content
                            first_part = path_parts[0].split(".")[0]
                            if len(first_part) == 36 and first_part not in [  # UUID length
                                "templates",
                                "version",
                            ]:
                                notebook_uuid = first_part

                        if len(path_parts) >= 2:
                            # Files in subdirectories like uuid/page.rm
                            if len(path_parts[0]) == 36 and path_parts[0] not in [
                                "templates",
                                "version",
                            ]:
                                notebook_uuid = path_parts[0]

                        if notebook_uuid:
                            updated_notebooks.add(notebook_uuid)

                        pbar.set_postfix_str(f"Downloaded {local_path.name}")

                    except (OSError, SCPException) as e:
                        logging.error("Failed to download %s: %s", remote_file["path"], e)

                    pbar.update(1)

            # Save metadata
            self.metadata.save()

            if updated_notebooks:
                logging.debug("Updated notebook UUIDs: %s", sorted(updated_notebooks))

            logging.info(
                "File backup completed successfully. Updated %d notebooks.", len(updated_notebooks)
            )
            return True, updated_notebooks

        except (paramiko.SSHException, OSError) as e:
            logging.error("Backup failed: %s", e)
            return False, set()

        finally:
            self.connection.disconnect()

    def backup_templates(self) -> bool:
        """Backup template files from ReMarkable tablet.

        Templates are stored in /usr/share/remarkable/templates/ and include
        PNG/SVG template images and a templates.json configuration file.

        Returns:
            bool: True if successful, False otherwise
        """
        logging.info("Starting template backup...")

        if not self.connection.connect():
            return False

        try:
            # Get list of template files
            remote_files = self.connection.list_files(self.remote_templates_dir)

            if not remote_files:
                logging.warning("No template files found on ReMarkable tablet")
                return True

            # Filter templates that need syncing
            files_to_sync = []
            for remote_file in remote_files:
                relative_path = os.path.relpath(remote_file["path"], self.remote_templates_dir)
                local_path = self.templates_dir / relative_path

                if self.metadata.should_sync_file(remote_file, local_path):
                    files_to_sync.append((remote_file, local_path))

            if not files_to_sync:
                logging.info("All template files are up to date")
                return True

            logging.info("Syncing %d template files...", len(files_to_sync))

            # Download template files with progress bar
            with tqdm(total=len(files_to_sync), desc="Downloading templates") as pbar:
                for remote_file, local_path in files_to_sync:
                    try:
                        # Create local directory if needed
                        local_path.parent.mkdir(parents=True, exist_ok=True)

                        # Download file
                        if self.connection.scp_client is None:
                            logging.error("SCP client not initialized")
                            return False
                        self.connection.scp_client.get(remote_file["path"], str(local_path))

                        # Update metadata
                        self.metadata.update_file_metadata(remote_file, local_path)

                        pbar.set_postfix_str(f"Downloaded {local_path.name}")

                    except (OSError, SCPException) as e:
                        logging.error("Failed to download %s: %s", remote_file["path"], e)

                    pbar.update(1)

            # Save metadata
            self.metadata.save()

            logging.info("Template backup completed successfully")
            return True

        except (paramiko.SSHException, OSError) as e:
            logging.error("Template backup failed: %s", e)
            return False

        finally:
            self.connection.disconnect()

    def find_notebooks(self) -> List[Dict]:
        """Find and parse notebook metadata.

        Scans the backup directory for .metadata files and extracts
        notebook information including name, type, and associated files.

        Returns:
            List of dictionaries containing notebook information
        """
        notebooks = []

        # Look for .metadata files which indicate notebooks/documents
        for metadata_file in self.files_dir.glob("*.metadata"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                uuid = metadata_file.stem
                notebook_info = {
                    "uuid": uuid,
                    "name": metadata.get("visibleName", "Untitled"),
                    "type": metadata.get("type", "unknown"),
                    "parent": metadata.get("parent", ""),
                    "metadata_file": metadata_file,
                    "content_file": self.files_dir / f"{uuid}.content",
                    "rm_files": list(self.files_dir.glob(f"{uuid}/*.rm")),
                    "pagedata_files": list(self.files_dir.glob(f"{uuid}/*.json")),
                }

                if notebook_info["content_file"].exists():
                    notebooks.append(notebook_info)

            except (OSError, json.JSONDecodeError) as e:
                logging.warning("Failed to parse %s: %s", metadata_file, e)

        return notebooks

    def convert_to_pdf(self, notebook: Dict) -> Optional[Path]:
        """Convert notebook to PDF using available tools.

        Creates a placeholder metadata file for the notebook.
        In a full implementation, this would integrate with PDF conversion tools.

        Args:
            notebook: Dictionary containing notebook information

        Returns:
            Optional[Path]: Path to created file, None on error
        """
        output_path = self.pdfs_dir / f"{notebook['name']}.pdf"

        # For now, create a placeholder PDF indicating conversion is needed
        # In a real implementation, you would integrate with rm2pdf or rmc
        try:
            with open(output_path.with_suffix(".txt"), "w", encoding="utf-8") as f:
                f.write(f"Notebook: {notebook['name']}\n")
                f.write(f"UUID: {notebook['uuid']}\n")
                f.write(f"Type: {notebook['type']}\n")
                f.write(f"RM Files: {len(notebook['rm_files'])}\n")
                f.write(f"Pages: {len(notebook['pagedata_files'])}\n")
                f.write("\nTo convert to PDF, you'll need to install rmc or rm2pdf tools\n")
                f.write("See: https://github.com/ricklupton/rmc\n")

            logging.info("Created metadata for %s", notebook["name"])
            return output_path.with_suffix(".txt")

        except OSError as e:
            logging.error("Failed to create PDF metadata for %s: %s", notebook["name"], e)
            return None

    def run_backup(
        self,
        force_convert_all: bool = False,
        convert_to_pdf: bool = False,
        backup_templates: bool = True,
    ) -> bool:
        """Run complete backup process with optional PDF conversion.

        Args:
            force_convert_all: If True, convert all notebooks to PDF regardless of sync status
            convert_to_pdf: If True, automatically convert notebooks to PDF using hybrid converter
            backup_templates: If True, backup template files from the tablet (default: True)

        Returns:
            bool: True if backup successful, False otherwise
        """
        logging.info("Starting ReMarkable backup process")

        # Backup files and get list of updated notebooks
        success, updated_notebook_uuids = self.backup_files()
        if not success:
            return False

        # Backup templates if requested
        if backup_templates:
            templates_success = self.backup_templates()
            if not templates_success:
                logging.warning("Template backup failed, but continuing with main backup")

        # Automatic PDF conversion using hybrid converter
        if convert_to_pdf:
            return self.run_pdf_conversion(updated_notebook_uuids, force_convert_all)

        logging.info("Backup process completed successfully")
        return True

    def run_pdf_conversion(
        self, updated_notebook_uuids: Set[str], force_convert_all: bool = False
    ) -> bool:
        """Run PDF conversion using the converter module.

        Args:
            updated_notebook_uuids: Set of notebook UUIDs that were updated during sync
            force_convert_all: If True, convert all notebooks regardless of sync status

        Returns:
            bool: True if conversion successful, False otherwise
        """
        from ..converter import run_conversion

        logging.info("Starting PDF conversion...")

        # Set output directory
        output_dir = self.backup_dir / "PDF"

        # Determine conversion strategy
        updated_only_file = None
        if force_convert_all:
            logging.info("Force conversion enabled - converting all notebooks to PDF")
        elif updated_notebook_uuids:
            # Create a temporary file list of updated notebooks for selective conversion
            updated_list_file = self.backup_dir / "updated_notebooks.txt"
            try:
                with open(updated_list_file, "w", encoding="utf-8") as f:
                    for uuid in sorted(updated_notebook_uuids):
                        f.write(f"{uuid}\n")

                updated_only_file = updated_list_file
                logging.info("Converting %d updated notebooks to PDF", len(updated_notebook_uuids))
            except OSError as e:
                logging.error("Failed to create updated notebooks list: %s", e)
                return False
        else:
            logging.info("No notebooks were updated - skipping PDF conversion")
            return True

        # Run conversion
        try:
            success = run_conversion(
                backup_dir=self.backup_dir,
                output_dir=output_dir,
                verbose=True,
                sample=None,
                notebook_filter=None,
                updated_only=updated_only_file,
            )

            # Clean up temporary file if created
            if updated_only_file and updated_only_file.exists():
                try:
                    updated_only_file.unlink()
                except OSError:
                    pass  # Ignore cleanup errors

            if success:
                logging.info("PDF conversion completed successfully")
            else:
                logging.error("PDF conversion failed")

            return success

        except Exception as e:  # pylint: disable=broad-except
            logging.error("Failed to execute PDF conversion: %s", e)
            return False
