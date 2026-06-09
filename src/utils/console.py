"""Colored console output helpers and progress bar utilities using Rich."""


from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

# Shared console instance
console = Console(stderr=True)


def print_error(msg: str) -> None:
    """Print an error message in red."""
    console.print(f"[bold red]{msg}[/bold red]")


def print_warn(msg: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"[yellow]{msg}[/yellow]")


def print_success(msg: str) -> None:
    """Print a success message in green."""
    console.print(f"[bold green]{msg}[/bold green]")


def print_status(msg: str) -> None:
    """Print an informational status message."""
    console.print(msg)


def create_progress(description: str = "Working") -> Progress:
    """Create a Rich Progress bar that stays pinned at the bottom.

    Use as a context manager::

        with create_progress("Downloading") as progress:
            task = progress.add_task("files", total=100)
            for item in items:
                ...
                progress.update(task, advance=1, description=item.name)
    """
    from rich.table import Column

    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}",
                   table_column=Column(min_width=45)),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


def get_rich_logging_handler() -> RichHandler:
    """Return a RichHandler that coexists with Rich progress bars."""
    return RichHandler(
        console=console,
        show_path=False,
        show_time=True,
        show_level=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        omit_repeated_times=False,
    )
