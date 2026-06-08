"""Tests for the Obsidian Markdown exporter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.obsidian.exporter import ObsidianExporter, _safe_name, _file_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notebook(name: str, uuid: str, folder_path: str = "") -> dict:
    return {
        "uuid": uuid,
        "name": name,
        "type": "DocumentType",
        "folder_path": folder_path,
    }


def _write_dummy_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 dummy content for testing")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

class TestSafeName:
    def test_removes_special_chars(self):
        assert _safe_name("Hello/World!") == "HelloWorld"

    def test_preserves_spaces_hyphens_underscores(self):
        assert _safe_name("Hello World - Test_1") == "Hello World - Test_1"

    def test_empty_string(self):
        assert _safe_name("") == ""

    def test_strips_whitespace(self):
        assert _safe_name("  hello  ") == "hello"


class TestFileHash:
    def test_consistent_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        h1 = _file_hash(f)
        h2 = _file_hash(f)
        assert h1 == h2
        assert len(h1) == 32  # MD5 hex digest

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello", encoding="utf-8")
        f2.write_text("world", encoding="utf-8")
        assert _file_hash(f1) != _file_hash(f2)


# ---------------------------------------------------------------------------
# ObsidianExporter
# ---------------------------------------------------------------------------

class TestObsidianExporter:
    def _make_exporter(self, vault_dir: Path, backup_dir: Path, ocr_engine=None) -> ObsidianExporter:
        return ObsidianExporter(
            vault_dir=vault_dir,
            backup_dir=backup_dir,
            ocr_engine=ocr_engine,
            tags=["remarkable", "test"],
            embed_images=False,  # skip image export in unit tests
        )

    def test_creates_vault_dir(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()
        exp = self._make_exporter(vault, backup)
        assert vault.exists()

    def test_state_file_created_after_export(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("My Note", "uuid-1234")
        pdf = backup / "My Note.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        result = exp.export_notebook(notebook, pdf)

        assert result is not None
        state_file = backup / ObsidianExporter.STATE_FILE_NAME
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert "uuid-1234" in state

    def test_markdown_file_created(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("Shopping List", "uuid-5678")
        pdf = backup / "Shopping List.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        md_path = exp.export_notebook(notebook, pdf)

        assert md_path is not None
        assert Path(md_path).exists()
        content = Path(md_path).read_text(encoding="utf-8")
        assert "Shopping List" in content
        assert "remarkable_id: uuid-5678" in content

    def test_frontmatter_contains_tags(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("Tagged Note", "uuid-9999")
        pdf = backup / "Tagged Note.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        md_path = exp.export_notebook(notebook, pdf)

        content = Path(md_path).read_text(encoding="utf-8")
        assert "  - remarkable" in content
        assert "  - test" in content

    def test_incremental_skip_unchanged(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("Repeated Note", "uuid-repeat")
        pdf = backup / "Repeated Note.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        # First export
        md_path1 = exp.export_notebook(notebook, pdf)
        mtime1 = Path(md_path1).stat().st_mtime

        import time
        time.sleep(0.05)

        # Second export – unchanged PDF should be skipped
        exp2 = self._make_exporter(vault, backup)
        result = exp2.export_notebook(notebook, pdf)

        # File should not be recreated (or its mtime should not change)
        if result is not None:
            mtime2 = Path(result).stat().st_mtime
            # mtime should be the same since we skipped the re-export
            assert mtime2 == mtime1

    def test_force_re_exports_unchanged(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("Force Note", "uuid-force")
        pdf = backup / "Force Note.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        exp.export_notebook(notebook, pdf)

        # Force re-export
        exp2 = self._make_exporter(vault, backup)
        result = exp2.export_notebook(notebook, pdf, force=True)
        assert result is not None

    def test_folder_hierarchy_respected(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("Deep Note", "uuid-deep", folder_path="Work/Projects")
        pdf = backup / "Deep Note.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        md_path = exp.export_notebook(notebook, pdf)

        assert md_path is not None
        expected_dir = vault / "Work" / "Projects"
        assert expected_dir.exists()
        assert Path(md_path).parent == expected_dir

    def test_ocr_text_included_in_markdown(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()

        notebook = _make_notebook("OCR Note", "uuid-ocr")
        pdf = backup / "OCR Note.pdf"
        _write_dummy_pdf(pdf)

        mock_ocr = MagicMock()
        mock_ocr.extract_text.return_value = ("raw text", "## Heading\n\nProcessed text.")

        exp = ObsidianExporter(
            vault_dir=vault,
            backup_dir=backup,
            ocr_engine=mock_ocr,
            embed_images=False,
        )
        md_path = exp.export_notebook(notebook, pdf)

        content = Path(md_path).read_text(encoding="utf-8")
        assert "Processed text." in content

    def test_export_all_returns_counts(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()
        pdf_dir = backup / "PDF"

        notebooks = [
            _make_notebook("Note A", "uuid-a"),
            _make_notebook("Note B", "uuid-b"),
        ]
        for nb in notebooks:
            pdf = pdf_dir / f"{nb['name']}.pdf"
            _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        exported, skipped = exp.export_all(notebooks, pdf_dir)
        assert exported == 2
        assert skipped == 0

    def test_export_all_skips_collection_type(self, tmp_path):
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        backup.mkdir()
        pdf_dir = backup / "PDF"
        pdf_dir.mkdir()

        notebooks = [
            {"uuid": "folder-1", "name": "Work", "type": "CollectionType", "folder_path": ""},
            _make_notebook("My Note", "uuid-n"),
        ]
        pdf = pdf_dir / "My Note.pdf"
        _write_dummy_pdf(pdf)

        exp = self._make_exporter(vault, backup)
        exported, skipped = exp.export_all(notebooks, pdf_dir)
        assert exported == 1  # only the document, not the folder
