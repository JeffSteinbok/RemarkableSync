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

try:
    import keyring  # type: ignore

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logging.warning("keyring library not available - password saving disabled")


class ReMarkableConnection:
    """Handles SSH connection to ReMarkable tablet.

    Provides a robust connection interface with retry logic and error handling
    for connecting to ReMarkable tablets via USB networking.
    """

    KEYRING_SERVICE = "RemarkableSync"
    KEYRING_USERNAME = "remarkable_ssh"

    def __init__(
        self,
        host: str = "10.11.99.1",
        username: str = "root",
        port: int = 22,
        password: str | None = None,
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
        self.password_saved = False

    def get_saved_password(self) -> str | None:
        """Get saved password from system keyring.

        Returns:
            str: Saved password or None if not found
        """
        if not KEYRING_AVAILABLE:
            return None

        try:
            return keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME)
        except Exception as e:
            logging.debug(f"Failed to retrieve saved password: {e}")
            return None

    def save_password(self, password: str) -> bool:
        """Save password to system keyring.

        Args:
            password: Password to save

        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False

        try:
            keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME, password)
            self.password_saved = True
            return True
        except Exception as e:
            logging.warning(f"Failed to save password: {e}")
            return False

    def delete_saved_password(self) -> bool:
        """Delete saved password from system keyring.

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False

        try:
            keyring.delete_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME)
            return True
        except Exception as e:
            logging.debug(f"Failed to delete saved password: {e}")
            return False

    def get_password(self) -> str:
        """Get SSH password from user input or saved keyring.

        The ReMarkable tablet's SSH password is found in:
        Settings > Help > Copyright and licenses > GPLv3 Compliance

        Returns:
            str: The SSH password for tablet authentication
        """
        if not self.password:
            # Try to get saved password first
            saved_password = self.get_saved_password()
            if saved_password:
                print("Using saved SSH password...")
                self.password = saved_password
                return self.password

            # No saved password, prompt user
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
        Handles password retry logic if saved password fails.

        Returns:
            bool: True if connection successful, False otherwise
        """
        max_password_retries = 3
        password_attempt = 0
        used_saved_password = False

        while password_attempt < max_password_retries:
            try:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Check if we're using a saved password
                saved_password = self.get_saved_password()
                if saved_password and not self.password:
                    used_saved_password = True

                password = self.get_password()

                # Try multiple connection approaches for ReMarkable compatibility
                connection_attempts = [
                    {"timeout": 30, "banner_timeout": 30, "auth_timeout": 30},
                    {"timeout": 60, "banner_timeout": 60, "auth_timeout": 60},
                ]

                for i, params in enumerate(connection_attempts):
                    try:
                        logging.info(
                            "Connection attempt %d with timeout %ds...", i + 1, params["timeout"]
                        )
                        self.ssh_client.connect(
                            hostname=self.host,
                            username=self.username,
                            password=password,
                            port=self.port,
                            timeout=params["timeout"],
                            banner_timeout=params["banner_timeout"],
                            auth_timeout=params["auth_timeout"],
                            allow_agent=False,
                            look_for_keys=False,
                        )

                        transport = self.ssh_client.get_transport()
                        if transport is None:
                            raise ConnectionError("Failed to get SSH transport")
                        self.scp_client = SCPClient(transport)
                        logging.info("Connected to ReMarkable tablet at %s", self.host)

                        # Connection successful! Ask if user wants to save password
                        if (
                            not used_saved_password
                            and KEYRING_AVAILABLE
                            and not self.password_saved
                        ):
                            if click.confirm(
                                "\nWould you like to save this password securely for future use?",
                                default=False,
                            ):
                                if self.save_password(password):
                                    print("Password saved successfully!")
                                else:
                                    print("Failed to save password.")

                        return True

                    except paramiko.AuthenticationException as e:
                        logging.warning("Authentication failed on attempt %d: %s", i + 1, e)
                        # Authentication failed - might be wrong password
                        if used_saved_password:
                            print("\nSaved password appears to be incorrect.")
                            if click.confirm(
                                "Would you like to enter a new password?", default=True
                            ):
                                # Delete the old saved password
                                self.delete_saved_password()
                                self.password = None
                                used_saved_password = False
                                password_attempt += 1
                                break  # Break inner loop to retry with new password
                            else:
                                if click.confirm("Try saved password again?", default=False):
                                    password_attempt += 1
                                    break
                                else:
                                    return False
                        else:
                            # User-entered password was wrong
                            print("\nAuthentication failed. Please check your password.")
                            self.password = None
                            password_attempt += 1
                            break
                    except (paramiko.SSHException, OSError) as e:
                        logging.warning("Connection attempt %d failed: %s", i + 1, e)
                        if self.ssh_client:
                            try:
                                self.ssh_client.close()
                            except (paramiko.SSHException, OSError):
                                pass
                            self.ssh_client = paramiko.SSHClient()
                            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                logging.error("All connection attempts failed")
                return False

            except (paramiko.SSHException, OSError) as e:
                logging.error("Failed to connect to ReMarkable: %s", e)
                return False

        print("\nMaximum password retry attempts reached.")
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
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(" ", 2)
            if len(parts) == 3:
                files.append({"path": parts[2], "mtime": int(parts[0]), "size": int(parts[1])})

        return files
