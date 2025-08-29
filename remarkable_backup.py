#!/usr/bin/env python3
"""
ReMarkable Tablet Backup Tool

This tool connects to your ReMarkable tablet via USB, backs up files,
and creates PDF versions with incremental sync support.
"""

import os
import json
import hashlib
import logging
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import click
import paramiko
from scp import SCPClient, SCPException
from tqdm import tqdm


class ReMarkableConnection:
    """Handles SSH connection to ReMarkable tablet."""

    def __init__(self, host: str = "10.11.99.1", username: str = "root", port: int = 22, password: str = None):
        self.host = host
        self.username = username
        self.port = port
        self.ssh_client = None
        self.scp_client = None
        self.password = password

    def get_password(self) -> str:
        """Get SSH password from user input.
        
        The ReMarkable tablet's SSH password is found in:
        Settings > Help > Copyright and licenses > GPLv3 Compliance
        
        Returns:
            str: The SSH password for tablet authentication
        """
        if not self.password:
            print("To get your ReMarkable SSH password:")
            print("1. Connect your tablet via USB")
            print("2. Go to Settings > Help > Copyright and licenses")
            print("3. Find the password under 'GPLv3 Compliance'")
            self.password = click.prompt("Enter SSH password", hide_input=True)
        return self.password

    def connect(self) -> bool:
        """Establish SSH connection to ReMarkable tablet.
        
        Attempts multiple connection strategies with different timeout values
        to handle various network conditions and tablet responsiveness.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            password = self.get_password()

            # Try multiple connection approaches for ReMarkable compatibility
            connection_attempts = [
                {'timeout': 30, 'banner_timeout': 30, 'auth_timeout': 30},
                {'timeout': 60, 'banner_timeout': 60, 'auth_timeout': 60},
            ]

            for i, params in enumerate(connection_attempts):
                try:
                    logging.info("Connection attempt %d with timeout %ds...", i+1, params['timeout'])
                    self.ssh_client.connect(
                        hostname=self.host,
                        username=self.username,
                        password=password,
                        port=self.port,
                        timeout=params['timeout'],
                        banner_timeout=params['banner_timeout'],
                        auth_timeout=params['auth_timeout'],
                        allow_agent=False,
                        look_for_keys=False
                    )

                    self.scp_client = SCPClient(self.ssh_client.get_transport())
                    logging.info("Connected to ReMarkable tablet at %s", self.host)
                    return True

                except (paramiko.AuthenticationException, paramiko.SSHException, OSError) as e:
                    logging.warning("Connection attempt %d failed: %s", i+1, e)
                    if self.ssh_client:
                        try:
                            self.ssh_client.close()
                        except (paramiko.SSHException, OSError):
                            pass
                        self.ssh_client = paramiko.SSHClient()
                        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            logging.error("All connection attempts failed")
            return False

        except (paramiko.AuthenticationException, paramiko.SSHException, OSError) as e:
            logging.error("Failed to connect to ReMarkable: %s", e)
            return False

    def disconnect(self):
        """Close SSH and SCP connections to ReMarkable tablet.
        
        Safely closes both SCP and SSH client connections,
        ensuring clean disconnection from the tablet.
        """
        if self.scp_client:
            self.scp_client.close()
        if self.ssh_client:
            self.ssh_client.close()
        logging.info("Disconnected from ReMarkable tablet")

    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Execute command on ReMarkable tablet via SSH.
        
        Args:
            command: Shell command to execute on the tablet
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
            
        Raises:
            ConnectionError: If not connected to tablet
        """
        if not self.ssh_client:
            raise ConnectionError("Not connected to ReMarkable tablet")

        _, stdout, stderr = self.ssh_client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()

        return stdout.read().decode(), stderr.read().decode(), exit_code

    def list_files(self, remote_path: str) -> List[Dict]:
        """List files in remote directory with metadata.
        
        Uses the 'find' and 'stat' commands to get file modification times,
        sizes, and paths for incremental sync comparison.
        
        Args:
            remote_path: Remote directory path to scan
            
        Returns:
            List of dictionaries containing file metadata:
            - path: Full file path on tablet
            - mtime: Unix timestamp of last modification
            - size: File size in bytes
        """
        command = f"find {remote_path} -type f -exec stat -c '%Y %s %n' {{}} \\;"
        stdout, stderr, exit_code = self.execute_command(command)

        if exit_code != 0:
            logging.error("Failed to list files: %s", stderr)
            return []

        files = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(' ', 2)
            if len(parts) == 3:
                files.append({
                    'path': parts[2],
                    'mtime': int(parts[0]),
                    'size': int(parts[1])
                })

        return files


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
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
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
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
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
            with open(file_path, 'rb') as f:
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
        remote_path = remote_file['path']

        # File doesn't exist locally
        if not local_path.exists():
            return True

        # Check if we have metadata for this file
        if remote_path not in self.data:
            return True

        stored_mtime = self.data[remote_path].get('mtime', 0)
        stored_size = self.data[remote_path].get('size', 0)

        # Check if remote file has changed
        if (remote_file['mtime'] != stored_mtime or
            remote_file['size'] != stored_size):
            return True

        # Verify local file integrity
        current_hash = self.get_file_hash(local_path)
        stored_hash = self.data[remote_path].get('hash', '')

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
        self.data[remote_file['path']] = {
            'mtime': remote_file['mtime'],
            'size': remote_file['size'],
            'hash': file_hash,
            'last_sync': datetime.now(timezone.utc).isoformat()
        }


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

    def __init__(self, backup_dir: Path, password: str = None):
        """Initialize backup orchestrator.
        
        Args:
            backup_dir: Local directory to store backup files
            password: SSH password for tablet (prompted if not provided)
        """
        self.backup_dir = backup_dir
        self.files_dir = backup_dir / "files"
        self.pdfs_dir = backup_dir / "pdfs"
        self.metadata_file = backup_dir / "sync_metadata.json"

        # Create directories
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)

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
                relative_path = os.path.relpath(remote_file['path'], self.remote_xochitl_dir)
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
                        self.connection.scp_client.get(
                            remote_file['path'],
                            str(local_path)
                        )

                        # Update metadata
                        self.metadata.update_file_metadata(remote_file, local_path)

                        # Track notebook UUID if this file belongs to a notebook
                        # Handle both top-level files and files in subdirectories
                        relative_path = os.path.relpath(remote_file['path'], self.remote_xochitl_dir)
                        path_parts = relative_path.split(os.sep)

                        # Check if this is a notebook-related file
                        notebook_uuid = None
                        if len(path_parts) >= 1:
                            # Top-level files like uuid.metadata, uuid.content
                            first_part = path_parts[0].split('.')[0]
                            if (len(first_part) == 36 and  # UUID length
                                first_part not in ['templates', 'version']):
                                notebook_uuid = first_part

                        if len(path_parts) >= 2:
                            # Files in subdirectories like uuid/page.rm
                            if (len(path_parts[0]) == 36 and
                                path_parts[0] not in ['templates', 'version']):
                                notebook_uuid = path_parts[0]

                        if notebook_uuid:
                            updated_notebooks.add(notebook_uuid)

                        pbar.set_postfix_str(f"Downloaded {local_path.name}")

                    except (OSError, SCPException) as e:
                        logging.error("Failed to download %s: %s", remote_file['path'], e)

                    pbar.update(1)

            # Save metadata
            self.metadata.save()

            if updated_notebooks:
                logging.debug("Updated notebook UUIDs: %s", sorted(updated_notebooks))

            logging.info("File backup completed successfully. Updated %d notebooks.", len(updated_notebooks))
            return True, updated_notebooks

        except (paramiko.SSHException, OSError) as e:
            logging.error("Backup failed: %s", e)
            return False, set()

        finally:
            self.connection.disconnect()

    def find_notebooks(self) -> List[Dict]:
        """Find and parse notebook metadata."""
        notebooks = []

        # Look for .metadata files which indicate notebooks/documents
        for metadata_file in self.files_dir.glob("*.metadata"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                uuid = metadata_file.stem
                notebook_info = {
                    'uuid': uuid,
                    'name': metadata.get('visibleName', 'Untitled'),
                    'type': metadata.get('type', 'unknown'),
                    'parent': metadata.get('parent', ''),
                    'metadata_file': metadata_file,
                    'content_file': self.files_dir / f"{uuid}.content",
                    'rm_files': list(self.files_dir.glob(f"{uuid}/*.rm")),
                    'pagedata_files': list(self.files_dir.glob(f"{uuid}/*.json"))
                }

                if notebook_info['content_file'].exists():
                    notebooks.append(notebook_info)

            except (OSError, json.JSONDecodeError) as e:
                logging.warning("Failed to parse %s: %s", metadata_file, e)

        return notebooks

    def convert_to_pdf(self, notebook: Dict) -> Optional[Path]:
        """Convert notebook to PDF using available tools."""
        output_path = self.pdfs_dir / f"{notebook['name']}.pdf"

        # For now, create a placeholder PDF indicating conversion is needed
        # In a real implementation, you would integrate with rm2pdf or rmc
        try:
            with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
                f.write(f"Notebook: {notebook['name']}\n")
                f.write(f"UUID: {notebook['uuid']}\n")
                f.write(f"Type: {notebook['type']}\n")
                f.write(f"RM Files: {len(notebook['rm_files'])}\n")
                f.write(f"Pages: {len(notebook['pagedata_files'])}\n")
                f.write("\nTo convert to PDF, you'll need to install rmc or rm2pdf tools\n")
                f.write("See: https://github.com/ricklupton/rmc\n")

            logging.info("Created metadata for %s", notebook['name'])
            return output_path.with_suffix('.txt')

        except OSError as e:
            logging.error("Failed to create PDF metadata for %s: %s", notebook['name'], e)
            return None

    def run_backup(self, force_convert_all: bool = False, convert_to_pdf: bool = False) -> bool:
        """Run complete backup process with optional PDF conversion.

        Args:
            force_convert_all: If True, convert all notebooks to PDF regardless of sync status
            convert_to_pdf: If True, automatically convert notebooks to PDF using hybrid converter
        """
        logging.info("Starting ReMarkable backup process")

        # Backup files and get list of updated notebooks
        success, updated_notebook_uuids = self.backup_files()
        if not success:
            return False

        # Automatic PDF conversion using hybrid converter
        if convert_to_pdf:
            return self.run_pdf_conversion(updated_notebook_uuids, force_convert_all)

        logging.info("Backup process completed successfully")
        return True

    def run_pdf_conversion(self, updated_notebook_uuids: Set[str], force_convert_all: bool = False) -> bool:  # pylint: disable=too-many-return-statements
        """Run PDF conversion using hybrid_converter.py.

        Args:
            updated_notebook_uuids: Set of notebook UUIDs that were updated during sync
            force_convert_all: If True, convert all notebooks regardless of sync status
        """
        logging.info("Starting PDF conversion...")

        # Path to hybrid_converter.py (assume it's in the same directory)
        script_dir = Path(__file__).parent
        converter_script = script_dir / "hybrid_converter.py"

        if not converter_script.exists():
            logging.error("hybrid_converter.py not found at %s", converter_script)
            return False

        # Build command line arguments for hybrid converter
        cmd_args = [
            sys.executable,  # Use the same Python interpreter
            str(converter_script),
            "-d", str(self.backup_dir),
            "--verbose"
        ]

        # Determine conversion strategy
        if force_convert_all:
            logging.info("Force conversion enabled - converting all notebooks to PDF")
        elif updated_notebook_uuids:
            # Create a temporary file list of updated notebooks for selective conversion
            updated_list_file = self.backup_dir / "updated_notebooks.txt"
            try:
                with open(updated_list_file, 'w', encoding='utf-8') as f:
                    for uuid in sorted(updated_notebook_uuids):
                        f.write(f"{uuid}\n")

                cmd_args.extend(["--updated-only", str(updated_list_file)])
                logging.info("Converting %d updated notebooks to PDF", len(updated_notebook_uuids))
            except OSError as e:
                logging.error("Failed to create updated notebooks list: %s", e)
                return False
        else:
            logging.info("No notebooks were updated - skipping PDF conversion")
            return True

        # Execute hybrid converter
        try:
            logging.info("Executing: %s", " ".join(cmd_args))
            result = subprocess.run(
                cmd_args,
                cwd=script_dir,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                check=False
            )

            if result.returncode == 0:
                logging.info("PDF conversion completed successfully")

                # Clean up temporary file if created
                updated_list_file = self.backup_dir / "updated_notebooks.txt"
                if updated_list_file.exists():
                    try:
                        updated_list_file.unlink()
                    except OSError:
                        pass  # Ignore cleanup errors

                return True

            logging.error("PDF conversion failed with exit code %d", result.returncode)
            logging.error("Error output: %s", result.stderr)
            return False

        except subprocess.TimeoutExpired:
            logging.error("PDF conversion timed out after 1 hour")
            return False
        except (OSError, subprocess.SubprocessError) as e:
            logging.error("Failed to execute PDF converter: %s", e)
            return False

        logging.info("Backup process completed successfully")
        return True


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


@click.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path),
              default=Path('./remarkable_backup'),
              help='Directory to store backup files')
@click.option('--password', '-p', type=str, help='ReMarkable SSH password')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--force-convert-all', '-f', is_flag=True,
              help='Convert all notebooks to PDF regardless of sync status')
@click.option('--convert-pdf', '-c', is_flag=True,
              help='Automatically convert notebooks to PDF using hybrid converter')
def cli(backup_dir: Path, password: Optional[str], verbose: bool, force_convert_all: bool, convert_pdf: bool) -> None:
    """ReMarkable Tablet Backup Tool"""

    setup_logging(verbose)

    print("ReMarkable Tablet Backup Tool")
    print("=" * 40)
    print(f"Backup directory: {backup_dir.absolute()}")

    if convert_pdf:
        print("PDF conversion enabled: Using hybrid converter")

    if force_convert_all:
        print("Force conversion mode: All notebooks will be converted to PDF")

    backup_tool = ReMarkableBackup(backup_dir, password)

    try:
        success = backup_tool.run_backup(force_convert_all=force_convert_all, convert_to_pdf=convert_pdf)
        if success:
            print("\n[SUCCESS] Backup completed successfully!")
            print(f"Files backed up to: {backup_tool.files_dir}")
            if convert_pdf:
                pdfs_final_dir = backup_dir / "pdfs_final"
                if pdfs_final_dir.exists():
                    print(f"PDFs generated in: {pdfs_final_dir}")
                else:
                    print(f"PDF metadata created in: {backup_tool.pdfs_dir}")
        else:
            print("\n[ERROR] Backup failed. Check logs for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Backup interrupted by user")
        sys.exit(130)
    except (OSError, paramiko.SSHException) as e:
        logging.error("Unexpected error: %s", e)
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for the application."""
    # Note: Click decorators handle argument parsing automatically
    # Pylance doesn't understand this, but the code is correct
    cli()  # type: ignore  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
