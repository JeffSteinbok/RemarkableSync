"""Tests for the console utility module."""

from src.utils.console import (
    console,
    create_progress,
    print_error,
    print_status,
    print_success,
    print_warn,
)


class TestConsolePrinting:
    """Verify console helpers don't crash and produce output."""

    def test_print_error(self, capsys):
        print_error("something broke")
        # Rich writes to stderr via its Console
        # Just verify no exceptions

    def test_print_warn(self):
        print_warn("careful now")

    def test_print_success(self):
        print_success("all good")

    def test_print_status(self):
        print_status("doing stuff")


class TestProgressBar:
    """Verify progress bar creation."""

    def test_create_progress_returns_progress(self):
        progress = create_progress("Testing")
        assert progress is not None

    def test_progress_context_manager(self):
        with create_progress("Test") as p:
            task = p.add_task("items", total=3)
            for _ in range(3):
                p.update(task, advance=1)
        # No crash = pass
