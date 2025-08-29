"""
ReMarkable tablet SSH connection management.

Handles SSH and SCP connections to ReMarkable tablets for file transfer
and remote command execution.
"""

import logging
from typing import Dict, List, Tuple

import click
import paramiko
from scp import SCPClient


class ReMarkableConnection:
    """Handles SSH connection to ReMarkable tablet.

    Provides a robust connection interface with retry logic and error handling
    for connecting to ReMarkable tablets via USB networking.
    """

    def __init__(
        self, host: str = "10.11.99.1", username: str = "root",
        port: int = 22, password: str = None
    ):
        """Initialize connection parameters.

        Args:
            host: ReMarkable tablet IP address (default USB networking address)
            username: SSH username (always 'root' for ReMarkable)
            port: SSH port (default 22)
            password: SSH password (will prompt if not provided)
        """
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
                    logging.info(
                        "Connection attempt %d with timeout %ds...",
                        i+1, params['timeout']
                    )
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
