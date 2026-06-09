"""Tests for Wi-Fi / configurable connection support."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.backup.connection import USB_HOST, ReMarkableConnection, discover_tablet_host


class TestConnectionInit:
    """Verify that ReMarkableConnection resolves the correct host."""

    def test_default_is_usb(self):
        conn = ReMarkableConnection()
        assert conn.host == USB_HOST

    def test_explicit_host_used_without_wifi(self):
        conn = ReMarkableConnection(host="192.168.1.50")
        assert conn.host == "192.168.1.50"

    def test_wifi_host_overrides_host(self):
        conn = ReMarkableConnection(use_wifi=True, wifi_host="192.168.1.100")
        assert conn.host == "192.168.1.100"

    def test_wifi_without_wifi_host_falls_back_to_usb(self):
        """When Wi-Fi is requested but wifi_host is empty and discovery fails,
        the connection should fall back to the USB address."""
        with patch("src.backup.connection.discover_tablet_host", return_value=None):
            conn = ReMarkableConnection(use_wifi=True, wifi_host="")
        assert conn.host == USB_HOST

    def test_wifi_auto_discovery_used(self):
        """When Wi-Fi is requested without a wifi_host, auto-discovery is attempted."""
        discovered = "192.168.1.42"
        with patch("src.backup.connection.discover_tablet_host", return_value=discovered):
            conn = ReMarkableConnection(use_wifi=True, wifi_host="")
        assert conn.host == discovered

    def test_wifi_flag_ignored_when_not_set(self):
        """An explicit host with use_wifi=False should not trigger discovery."""
        with patch("src.backup.connection.discover_tablet_host") as mock_discover:
            conn = ReMarkableConnection(host="10.11.99.1", use_wifi=False)
        mock_discover.assert_not_called()
        assert conn.host == "10.11.99.1"


class TestDiscoverTabletHost:
    """Unit tests for the mDNS discovery helper."""

    def test_returns_ip_when_resolution_succeeds(self):
        with patch("socket.gethostbyname", return_value="192.168.1.10"):
            result = discover_tablet_host(timeout=0.1)
        assert result == "192.168.1.10"

    def test_returns_none_when_all_fail(self):
        with patch("socket.gethostbyname", side_effect=OSError):
            result = discover_tablet_host(timeout=0.1)
        assert result is None


class TestBackupManagerHostPropagation:
    """Verify ReMarkableBackup passes connection params to ReMarkableConnection."""

    def test_host_propagated(self):
        from src.backup.backup_manager import ReMarkableBackup

        with patch("src.backup.backup_manager.ReMarkableConnection") as MockConn:
            MockConn.return_value = MagicMock()
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                ReMarkableBackup(
                    backup_dir=Path(tmp),
                    host="10.11.99.1",
                    use_wifi=False,
                    wifi_host="",
                )
            call_kwargs = MockConn.call_args.kwargs
            assert call_kwargs.get("host") == "10.11.99.1"
            assert call_kwargs.get("use_wifi") is False

    def test_wifi_propagated(self):
        from src.backup.backup_manager import ReMarkableBackup

        with patch("src.backup.backup_manager.ReMarkableConnection") as MockConn:
            MockConn.return_value = MagicMock()
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                ReMarkableBackup(
                    backup_dir=Path(tmp),
                    use_wifi=True,
                    wifi_host="192.168.1.99",
                )
            call_kwargs = MockConn.call_args.kwargs
            assert call_kwargs.get("use_wifi") is True
            assert call_kwargs.get("wifi_host") == "192.168.1.99"
