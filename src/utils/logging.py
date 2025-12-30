"""Logging configuration utilities."""

import logging


def setup_logging(verbose: bool = False):
    """Configure logging with appropriate levels and formatting.

    Sets up console logging with timestamp formatting to track
    operations and debug issues.

    Args:
        verbose: Enable DEBUG level logging if True, INFO level if False
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Suppress verbose debug messages from third-party libraries
    logging.getLogger("svglib.svglib").setLevel(logging.WARNING)
    logging.getLogger("reportlab").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
