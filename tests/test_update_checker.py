"""Tests for the update_checker module."""

import time
from unittest.mock import patch

from src.update_checker import (
    _CHECK_INTERVAL,
    _parse_version,
    _read_cache,
    _write_cache,
    check_for_update,
    format_update_message,
)


class TestParseVersion:
    def test_simple_version(self):
        assert _parse_version("2.0.4") == (2, 0, 4)

    def test_version_with_v_prefix(self):
        assert _parse_version("v2.0.4") == (2, 0, 4)

    def test_major_only(self):
        assert _parse_version("3") == (3,)

    def test_invalid_version(self):
        assert _parse_version("abc") == (0,)

    def test_comparison(self):
        assert _parse_version("2.1.0") > _parse_version("2.0.4")
        assert _parse_version("2.0.4") == _parse_version("v2.0.4")
        assert _parse_version("3.0.0") > _parse_version("2.99.99")


class TestCache:
    def test_read_write_cache(self, tmp_path):
        cache_file = tmp_path / "update_check.json"
        with patch("src.update_checker._cache_path", return_value=cache_file):
            data = {"last_check": 12345, "latest_version": "2.1.0"}
            _write_cache(data)
            assert _read_cache() == data

    def test_read_missing_cache(self, tmp_path):
        cache_file = tmp_path / "nonexistent.json"
        with patch("src.update_checker._cache_path", return_value=cache_file):
            assert _read_cache() == {}

    def test_read_corrupt_cache(self, tmp_path):
        cache_file = tmp_path / "bad.json"
        cache_file.write_text("not json", encoding="utf-8")
        with patch("src.update_checker._cache_path", return_value=cache_file):
            assert _read_cache() == {}


class TestCheckForUpdate:
    @patch("src.update_checker._fetch_latest_version")
    @patch("src.update_checker._read_cache")
    @patch("src.update_checker._write_cache")
    @patch("src.update_checker.__version__", "2.0.4")
    def test_update_available(self, mock_write, mock_read, mock_fetch):
        mock_read.return_value = {}
        mock_fetch.return_value = "2.1.0"
        result = check_for_update(force=True)
        assert result == "2.1.0"

    @patch("src.update_checker._fetch_latest_version")
    @patch("src.update_checker._read_cache")
    @patch("src.update_checker._write_cache")
    @patch("src.update_checker.__version__", "2.1.0")
    def test_already_latest(self, mock_write, mock_read, mock_fetch):
        mock_read.return_value = {}
        mock_fetch.return_value = "2.1.0"
        result = check_for_update(force=True)
        assert result is None

    @patch("src.update_checker._fetch_latest_version")
    @patch("src.update_checker._read_cache")
    @patch("src.update_checker._write_cache")
    @patch("src.update_checker.__version__", "2.0.4")
    def test_uses_cache_when_fresh(self, mock_write, mock_read, mock_fetch):
        mock_read.return_value = {
            "last_check": time.time(),  # just now
            "latest_version": "2.1.0",
        }
        result = check_for_update(force=False)
        assert result == "2.1.0"
        mock_fetch.assert_not_called()

    @patch("src.update_checker._fetch_latest_version")
    @patch("src.update_checker._read_cache")
    @patch("src.update_checker._write_cache")
    @patch("src.update_checker.__version__", "2.0.4")
    def test_stale_cache_triggers_fetch(self, mock_write, mock_read, mock_fetch):
        mock_read.return_value = {
            "last_check": time.time() - _CHECK_INTERVAL - 1,
            "latest_version": "2.0.4",
        }
        mock_fetch.return_value = "2.1.0"
        result = check_for_update(force=False)
        assert result == "2.1.0"
        mock_fetch.assert_called_once()

    @patch("src.update_checker._fetch_latest_version")
    @patch("src.update_checker._read_cache")
    @patch("src.update_checker._write_cache")
    def test_fetch_failure_returns_none(self, mock_write, mock_read, mock_fetch):
        mock_read.return_value = {}
        mock_fetch.return_value = None
        result = check_for_update(force=True)
        assert result is None

    @patch("src.update_checker._fetch_latest_version")
    @patch("src.update_checker._read_cache")
    @patch("src.update_checker._write_cache")
    @patch("src.update_checker.__version__", "2.0.4")
    def test_force_ignores_cache(self, mock_write, mock_read, mock_fetch):
        mock_read.return_value = {
            "last_check": time.time(),  # fresh cache
            "latest_version": "2.0.4",  # same version cached
        }
        mock_fetch.return_value = "2.1.0"
        result = check_for_update(force=True)
        assert result == "2.1.0"
        mock_fetch.assert_called_once()


class TestFormatUpdateMessage:
    @patch("src.update_checker.__version__", "2.0.4")
    def test_message_contents(self):
        msg = format_update_message("2.1.0")
        assert "2.1.0" in msg
        assert "2.0.4" in msg
        assert "pip install --upgrade" in msg
        assert "brew upgrade" in msg
