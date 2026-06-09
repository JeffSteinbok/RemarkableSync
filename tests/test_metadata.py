"""Tests for the backup metadata module (FileMetadata)."""

import json

from src.backup.metadata import FileMetadata


class TestFileMetadataLoadSave:
    """Load/save round-trip and error handling."""

    def test_load_creates_empty_when_missing(self, tmp_path):
        meta = FileMetadata(tmp_path / "nonexistent.json")
        assert meta.data == {}

    def test_save_creates_file(self, tmp_path):
        meta_path = tmp_path / "meta.json"
        meta = FileMetadata(meta_path)
        meta.data["key"] = {"mtime": 123}
        meta.save()
        assert meta_path.exists()
        loaded = json.loads(meta_path.read_text())
        assert loaded["key"]["mtime"] == 123

    def test_round_trip(self, tmp_path):
        meta_path = tmp_path / "meta.json"
        meta = FileMetadata(meta_path)
        meta.data["/path/to/file"] = {"mtime": 100, "size": 200, "hash": "abc"}
        meta.save()

        meta2 = FileMetadata(meta_path)
        assert meta2.data["/path/to/file"]["hash"] == "abc"

    def test_load_handles_corrupt_json(self, tmp_path):
        meta_path = tmp_path / "bad.json"
        meta_path.write_text("not valid json {{{", encoding="utf-8")
        meta = FileMetadata(meta_path)
        assert meta.data == {}

    def test_save_creates_parent_dirs(self, tmp_path):
        meta_path = tmp_path / "a" / "b" / "meta.json"
        meta = FileMetadata(meta_path)
        meta.data["x"] = 1
        meta.save()
        assert meta_path.exists()


class TestFileHash:
    """MD5 hash computation."""

    def test_consistent_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        h1 = meta.get_file_hash(f)
        h2 = meta.get_file_hash(f)
        assert h1 == h2
        assert len(h1) == 32

    def test_different_content(self, tmp_path):
        meta = FileMetadata(tmp_path / "m.json")
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello", encoding="utf-8")
        f2.write_text("world", encoding="utf-8")
        assert meta.get_file_hash(f1) != meta.get_file_hash(f2)

    def test_missing_file_returns_empty(self, tmp_path):
        meta = FileMetadata(tmp_path / "m.json")
        assert meta.get_file_hash(tmp_path / "nope.txt") == ""


class TestShouldSyncFile:
    """Incremental sync decision logic."""

    def test_file_not_existing_locally(self, tmp_path):
        meta = FileMetadata(tmp_path / "m.json")
        remote = {"path": "/remote/file", "mtime": 100, "size": 50}
        assert meta.should_sync_file(remote, tmp_path / "missing.txt") is True

    def test_no_stored_metadata(self, tmp_path):
        local = tmp_path / "file.txt"
        local.write_text("content", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        remote = {"path": "/remote/file", "mtime": 100, "size": 50}
        assert meta.should_sync_file(remote, local) is True

    def test_mtime_changed(self, tmp_path):
        local = tmp_path / "file.txt"
        local.write_text("content", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        meta.data["/remote/file"] = {"mtime": 50, "size": 7, "hash": "x"}
        remote = {"path": "/remote/file", "mtime": 100, "size": 7}
        assert meta.should_sync_file(remote, local) is True

    def test_size_changed(self, tmp_path):
        local = tmp_path / "file.txt"
        local.write_text("content", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        meta.data["/remote/file"] = {"mtime": 100, "size": 50, "hash": "x"}
        remote = {"path": "/remote/file", "mtime": 100, "size": 999}
        assert meta.should_sync_file(remote, local) is True

    def test_hash_matches_no_sync_needed(self, tmp_path):
        local = tmp_path / "file.txt"
        local.write_text("content", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        real_hash = meta.get_file_hash(local)
        meta.data["/remote/file"] = {"mtime": 100, "size": 7, "hash": real_hash}
        remote = {"path": "/remote/file", "mtime": 100, "size": 7}
        assert meta.should_sync_file(remote, local) is False

    def test_hash_mismatch_triggers_sync(self, tmp_path):
        local = tmp_path / "file.txt"
        local.write_text("content", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        meta.data["/remote/file"] = {"mtime": 100, "size": 7, "hash": "wrong_hash"}
        remote = {"path": "/remote/file", "mtime": 100, "size": 7}
        assert meta.should_sync_file(remote, local) is True


class TestUpdateFileMetadata:
    """Metadata update after sync."""

    def test_stores_correct_fields(self, tmp_path):
        local = tmp_path / "file.txt"
        local.write_text("test content", encoding="utf-8")
        meta = FileMetadata(tmp_path / "m.json")
        remote = {"path": "/remote/file", "mtime": 12345, "size": 12}
        meta.update_file_metadata(remote, local)

        entry = meta.data["/remote/file"]
        assert entry["mtime"] == 12345
        assert entry["size"] == 12
        assert len(entry["hash"]) == 32
        assert "last_sync" in entry
