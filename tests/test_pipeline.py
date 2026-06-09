"""Tests for the pipeline orchestration (commands/pipeline.py).

The pipeline function uses late (local) imports inside run_pipeline, so we
patch at the source module level rather than at pipeline module level.
"""

from unittest.mock import MagicMock, patch


class TestRunPipeline:
    """Test pipeline orchestration logic with all external calls mocked."""

    def _run(self, tmp_path, **kwargs):
        """Helper to invoke run_pipeline with defaults."""
        from src.commands.pipeline import run_pipeline

        defaults = {
            "backup_dir": tmp_path / "backup",
            "output_dir": tmp_path / "output",
            "password": "test",
            "log_level": "NONE",
            "skip_backup": True,
            "skip_convert": True,
            "ai_provider": "",
            "use_ai_ocr": False,
        }
        defaults.update(kwargs)
        defaults["backup_dir"].mkdir(parents=True, exist_ok=True)
        defaults["output_dir"].mkdir(parents=True, exist_ok=True)
        return run_pipeline(**defaults)

    @patch("src.config.load_config")
    @patch("src.hybrid_converter.find_notebooks", return_value=[])
    @patch("src.hybrid_converter.organize_notebooks_by_structure", return_value={"documents_to_convert": []})
    def test_no_notebooks_returns_zero(self, mock_org, mock_find, mock_config, tmp_path):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": []}
        (tmp_path / "pdf").mkdir()
        result = self._run(tmp_path)
        assert result == 0

    @patch("src.config.load_config")
    def test_missing_pdf_dir_returns_error(self, mock_config, tmp_path):
        mock_config.return_value = {"pdf_dir": "", "folders": []}
        result = self._run(tmp_path)
        assert result == 1

    @patch("src.config.load_config")
    @patch("src.commands.pipeline.ReMarkableBackup")
    def test_backup_failure_returns_error(self, mock_backup_cls, mock_config, tmp_path):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": []}
        (tmp_path / "pdf").mkdir()

        mock_backup = MagicMock()
        mock_backup.backup_files.return_value = (False, set(), {})
        mock_backup_cls.return_value = mock_backup

        result = self._run(tmp_path, skip_backup=False)
        assert result == 1

    @patch("src.config.load_config")
    @patch("src.commands.pipeline.ReMarkableBackup")
    @patch("src.commands.pipeline.run_conversion")
    @patch("src.hybrid_converter.find_notebooks", return_value=[])
    @patch("src.hybrid_converter.organize_notebooks_by_structure", return_value={"documents_to_convert": []})
    def test_successful_backup_proceeds(
        self, mock_org, mock_find, mock_convert, mock_backup_cls, mock_config, tmp_path
    ):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": []}
        (tmp_path / "pdf").mkdir()

        mock_backup = MagicMock()
        mock_backup.backup_files.return_value = (True, {"uuid-1"}, {})
        mock_backup_cls.return_value = mock_backup

        mock_convert.return_value = (True, {"uuid-1": []})

        result = self._run(tmp_path, skip_backup=False, skip_convert=False)
        assert result == 0

    @patch("src.config.load_config")
    @patch("src.hybrid_converter.find_notebooks")
    @patch("src.hybrid_converter.organize_notebooks_by_structure")
    @patch("src.pdf_md_converter.MarkdownExporter")
    def test_export_called_with_notebooks(
        self, mock_exporter_cls, mock_org, mock_find, mock_config, tmp_path
    ):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": []}
        (tmp_path / "pdf").mkdir()

        notebooks = [
            {"uuid": "nb-1", "name": "Note 1", "type": "DocumentType", "folder_path": ""}
        ]
        mock_find.return_value = notebooks
        mock_org.return_value = {"documents_to_convert": notebooks}

        mock_exporter = MagicMock()
        mock_exporter.export_all.return_value = (1, 0)
        mock_exporter_cls.return_value = mock_exporter

        result = self._run(tmp_path, force_export=True)
        assert result == 0
        mock_exporter.export_all.assert_called_once()

    @patch("src.config.load_config")
    @patch("src.hybrid_converter.find_notebooks")
    @patch("src.hybrid_converter.organize_notebooks_by_structure")
    @patch("src.pdf_md_converter.MarkdownExporter")
    def test_folder_filter_applied(
        self, mock_exporter_cls, mock_org, mock_find, mock_config, tmp_path
    ):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": ["Work"]}
        (tmp_path / "pdf").mkdir()

        notebooks = [
            {"uuid": "nb-1", "name": "Work Note", "type": "DocumentType", "folder_path": "Work"},
            {"uuid": "nb-2", "name": "Personal Note", "type": "DocumentType", "folder_path": "Personal"},
        ]
        mock_find.return_value = notebooks
        mock_org.return_value = {"documents_to_convert": notebooks}

        mock_exporter = MagicMock()
        mock_exporter.export_all.return_value = (1, 0)
        mock_exporter_cls.return_value = mock_exporter

        result = self._run(tmp_path, force_export=True)
        assert result == 0
        # Only the Work notebook should be passed to export
        call_args = mock_exporter.export_all.call_args
        exported_notebooks = call_args.kwargs.get("notebooks") or call_args[1].get("notebooks") or call_args[0][0]
        assert len(exported_notebooks) == 1
        assert exported_notebooks[0]["name"] == "Work Note"

    @patch("src.config.load_config")
    @patch("src.hybrid_converter.find_notebooks")
    @patch("src.hybrid_converter.organize_notebooks_by_structure")
    @patch("src.pdf_md_converter.MarkdownExporter")
    def test_notebook_filter_by_name(
        self, mock_exporter_cls, mock_org, mock_find, mock_config, tmp_path
    ):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": []}
        (tmp_path / "pdf").mkdir()

        notebooks = [
            {"uuid": "nb-1", "name": "Target", "type": "DocumentType", "folder_path": ""},
            {"uuid": "nb-2", "name": "Other", "type": "DocumentType", "folder_path": ""},
        ]
        mock_find.return_value = notebooks
        mock_org.return_value = {"documents_to_convert": notebooks}

        mock_exporter = MagicMock()
        mock_exporter.export_all.return_value = (1, 0)
        mock_exporter_cls.return_value = mock_exporter

        result = self._run(tmp_path, notebook_filter="Target", force_export=True)
        assert result == 0

    @patch("src.config.load_config")
    @patch("src.hybrid_converter.find_notebooks")
    @patch("src.hybrid_converter.organize_notebooks_by_structure")
    def test_notebook_filter_not_found_returns_error(
        self, mock_org, mock_find, mock_config, tmp_path
    ):
        mock_config.return_value = {"pdf_dir": str(tmp_path / "pdf"), "folders": []}
        (tmp_path / "pdf").mkdir()

        notebooks = [
            {"uuid": "nb-1", "name": "Only Note", "type": "DocumentType", "folder_path": ""},
        ]
        mock_find.return_value = notebooks
        mock_org.return_value = {"documents_to_convert": notebooks}

        result = self._run(tmp_path, notebook_filter="Nonexistent", force_export=True)
        assert result == 1
