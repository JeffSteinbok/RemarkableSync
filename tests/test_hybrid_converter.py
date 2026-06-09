"""Tests for the hybrid_converter module (notebook discovery and organization)."""

import json
from pathlib import Path

import pytest

from src.hybrid_converter import (
    find_notebooks,
    get_folder_hierarchy,
    organize_notebooks_by_structure,
)


def _write_metadata(files_dir: Path, uuid: str, name: str, ntype: str, parent: str = ""):
    """Helper to write a .metadata file."""
    meta = {
        "visibleName": name,
        "type": ntype,
        "parent": parent,
    }
    (files_dir / f"{uuid}.metadata").write_text(json.dumps(meta), encoding="utf-8")


def _write_rm_file(files_dir: Path, uuid: str, page: str, version: int):
    """Helper to write a fake .rm file with a version header."""
    page_dir = files_dir / uuid
    page_dir.mkdir(exist_ok=True)
    header = f"reMarkable .lines file, version={version}          "
    (page_dir / f"{page}.rm").write_bytes(header.encode("ascii"))


@pytest.fixture
def backup_dir(tmp_path):
    """Create a backup directory with fake notebook structure."""
    bd = tmp_path / "backup"
    files_dir = bd / "Notebooks"
    files_dir.mkdir(parents=True)

    # Folder
    _write_metadata(files_dir, "folder-1", "Work", "CollectionType")

    # Notebook with v6 pages
    _write_metadata(files_dir, "nb-001", "Meeting Notes", "DocumentType", parent="folder-1")
    _write_rm_file(files_dir, "nb-001", "page1", 6)
    _write_rm_file(files_dir, "nb-001", "page2", 6)

    # Notebook with v5 pages
    _write_metadata(files_dir, "nb-002", "Old Notebook", "DocumentType", parent="")
    _write_rm_file(files_dir, "nb-002", "page1", 5)

    # Notebook with mixed versions
    _write_metadata(files_dir, "nb-003", "Mixed", "DocumentType", parent="folder-1")
    _write_rm_file(files_dir, "nb-003", "page1", 5)
    _write_rm_file(files_dir, "nb-003", "page2", 6)

    # Empty document (no .rm files, no pdf) — should NOT be included
    _write_metadata(files_dir, "nb-empty", "Empty Doc", "DocumentType")

    return bd


class TestFindNotebooks:
    """Tests for discovering notebooks from backup directory."""

    def test_finds_all_notebooks(self, backup_dir):
        results = find_notebooks(backup_dir)
        names = [n["name"] for n in results]
        assert "Work" in names  # folder included
        assert "Meeting Notes" in names
        assert "Old Notebook" in names
        assert "Mixed" in names

    def test_classifies_v6_files(self, backup_dir):
        results = find_notebooks(backup_dir)
        meeting = next(n for n in results if n["name"] == "Meeting Notes")
        assert len(meeting["v6_files"]) == 2
        assert len(meeting["v5_files"]) == 0

    def test_classifies_v5_files(self, backup_dir):
        results = find_notebooks(backup_dir)
        old = next(n for n in results if n["name"] == "Old Notebook")
        assert len(old["v5_files"]) == 1
        assert len(old["v6_files"]) == 0

    def test_classifies_mixed_versions(self, backup_dir):
        results = find_notebooks(backup_dir)
        mixed = next(n for n in results if n["name"] == "Mixed")
        assert len(mixed["v5_files"]) == 1
        assert len(mixed["v6_files"]) == 1

    def test_excludes_empty_documents(self, backup_dir):
        results = find_notebooks(backup_dir)
        names = [n["name"] for n in results]
        assert "Empty Doc" not in names

    def test_returns_empty_for_missing_dir(self, tmp_path):
        results = find_notebooks(tmp_path / "nonexistent")
        assert results == []

    def test_handles_corrupt_metadata(self, backup_dir):
        files_dir = backup_dir / "Notebooks"
        (files_dir / "bad-uuid.metadata").write_text("not json!!!", encoding="utf-8")
        # Should not crash
        results = find_notebooks(backup_dir)
        assert len(results) >= 3  # originals still found

    def test_preserves_parent_uuid(self, backup_dir):
        results = find_notebooks(backup_dir)
        meeting = next(n for n in results if n["name"] == "Meeting Notes")
        assert meeting["parent"] == "folder-1"

    def test_includes_collection_type(self, backup_dir):
        results = find_notebooks(backup_dir)
        work = next(n for n in results if n["name"] == "Work")
        assert work["type"] == "CollectionType"


class TestGetFolderHierarchy:
    """Tests for resolving folder paths via parent UUIDs."""

    def test_single_level_parent(self, backup_dir):
        notebook = {"parent": "folder-1"}
        hierarchy = get_folder_hierarchy(notebook, backup_dir)
        assert hierarchy == ["Work"]

    def test_no_parent(self, backup_dir):
        notebook = {"parent": ""}
        hierarchy = get_folder_hierarchy(notebook, backup_dir)
        assert hierarchy == []

    def test_missing_parent_metadata(self, backup_dir):
        notebook = {"parent": "nonexistent-uuid"}
        hierarchy = get_folder_hierarchy(notebook, backup_dir)
        assert hierarchy == []

    def test_nested_folders(self, tmp_path):
        """Multi-level folder hierarchy."""
        bd = tmp_path / "backup"
        files_dir = bd / "Notebooks"
        files_dir.mkdir(parents=True)

        _write_metadata(files_dir, "root-folder", "Projects", "CollectionType", parent="")
        _write_metadata(files_dir, "sub-folder", "2024", "CollectionType", parent="root-folder")

        notebook = {"parent": "sub-folder"}
        hierarchy = get_folder_hierarchy(notebook, bd)
        assert hierarchy == ["Projects", "2024"]


class TestOrganizeNotebooksByStructure:
    """Tests for organizing notebooks into folder structure."""

    def test_documents_separated_from_folders(self, backup_dir):
        notebooks = find_notebooks(backup_dir)
        result = organize_notebooks_by_structure(notebooks, backup_dir)
        docs = result["documents_to_convert"]
        # Only DocumentType items should be in documents_to_convert
        for doc in docs:
            assert doc["type"] == "DocumentType"

    def test_folder_path_assigned(self, backup_dir):
        notebooks = find_notebooks(backup_dir)
        result = organize_notebooks_by_structure(notebooks, backup_dir)
        docs = result["documents_to_convert"]
        meeting = next(d for d in docs if d["name"] == "Meeting Notes")
        assert meeting["folder_path"] == "Work"

    def test_root_level_has_empty_path(self, backup_dir):
        notebooks = find_notebooks(backup_dir)
        result = organize_notebooks_by_structure(notebooks, backup_dir)
        docs = result["documents_to_convert"]
        old = next(d for d in docs if d["name"] == "Old Notebook")
        assert old["folder_path"] == ""

    def test_folder_structure_dict(self, backup_dir):
        notebooks = find_notebooks(backup_dir)
        result = organize_notebooks_by_structure(notebooks, backup_dir)
        structure = result["folder_structure"]
        assert "Work" in structure
        assert "" in structure  # root-level docs
