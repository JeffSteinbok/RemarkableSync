"""
V4 Converter - Internal Helper Module

This is a helper module for converting v4 format ReMarkable files.
Do not run directly - use RemarkableSync.py as the entry point.

Entry Point:
    RemarkableSync.py convert [OPTIONS]

This module provides:
- Conversion of v4 format .rm files (older legacy ReMarkable format)
- Integration with rmrl Python library (limited support)
- SVG intermediate format processing
"""

import tempfile
from pathlib import Path

from .base_converter import BaseConverter


class V4Converter(BaseConverter):
    """Converter for ReMarkable v4 format files using rmrl library.

    The v4 format is an older legacy format used by early ReMarkable tablets.
    Support for v4 files is limited and may not work for all file variants.
    This converter uses the 'rmrl' Python library as a fallback method.

    Conversion Process:
    1. Attempt to use rmrl to render .rm file to SVG format
    2. Use svglib/reportlab to convert SVG to PDF
    3. Clean up temporary files

    Note: v4 format support is experimental and may fail for many files.
    Consider upgrading old v4 files to newer formats when possible.
    """

    def __init__(self):
        """Initialize the v4 converter."""
        super().__init__("v4")

    def can_convert(self, rm_file: Path) -> bool:
        """Check if this converter can handle the given .rm file.

        Checks if the file has a v4 format header by reading the first
        few bytes of the file.

        Args:
            rm_file: Path to the .rm file to check

        Returns:
            bool: True if this is a v4 format file
        """
        version = self.detect_version(rm_file)
        return version == "4"

    def convert_to_pdf(self, rm_file: Path, output_file: Path) -> bool:
        """Convert a v4 .rm file to PDF using rmrl library.

        Uses rmrl to attempt rendering the .rm file to SVG format first,
        then converts the SVG to PDF using svglib/reportlab.

        Note: v4 format support is limited and this conversion may fail
        for many v4 files due to format differences.

        Args:
            rm_file: Path to the source v4 .rm file
            output_file: Path where the PDF should be created

        Returns:
            bool: True if conversion was successful, False otherwise
        """
        try:
            # Import rmrl on demand to handle missing dependencies gracefully
            import rmrl  # type: ignore # pylint: disable=import-outside-toplevel
        except ImportError:
            self.logger.debug("rmrl library not available for v4 conversion")
            return False

        try:
            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                svg_file = temp_path / f"{rm_file.stem}.svg"

                # Step 1: Attempt to convert .rm to SVG using rmrl
                self.logger.debug("Attempting v4 conversion for %s using rmrl", rm_file.name)

                # Try to render to SVG format (may fail for v4 files)
                svg_data = rmrl.render(str(rm_file))
                if not svg_data:
                    self.logger.debug("rmrl failed to render v4 file %s", rm_file.name)
                    return False

                # Write SVG data to temporary file
                with open(svg_file, "wb") as f:
                    f.write(svg_data)

                # Verify SVG file was created with reasonable content
                if not svg_file.exists() or svg_file.stat().st_size < 100:
                    self.logger.debug("rmrl SVG output too small for v4 file %s", rm_file.name)
                    return False

                # Step 2: Convert SVG to PDF
                self.logger.debug("Converting SVG to PDF for v4 file %s", rm_file.name)
                success = self.svg_to_pdf(svg_file, output_file)

                if success:
                    self.logger.debug(
                        "v4 conversion successful: %s -> %s", rm_file.name, output_file.name
                    )
                    return True

                self.logger.debug("SVG to PDF conversion failed for v4 file %s", rm_file.name)
                return False

        except (ImportError, OSError, ValueError) as e:
            self.logger.debug("v4 conversion error for %s: %s", rm_file.name, e)
            return False

    def is_rmrl_available(self) -> bool:
        """Check if the rmrl library is available.

        Returns:
            bool: True if rmrl library can be imported, False otherwise
        """
        import importlib.util

        return importlib.util.find_spec("rmrl") is not None

    def get_requirements(self) -> list[str]:
        """Get the external requirements for this converter.

        Returns:
            list[str]: List of required external tools/libraries
        """
        return ["rmrl Python library", "svglib Python library", "reportlab Python library"]

    def get_conversion_info(self) -> dict:
        """Get information about v4 conversion capabilities and limitations.

        Returns:
            dict: Information about v4 format support
        """
        return {
            "format": "v4",
            "support_level": "limited",
            "reliability": "experimental",
            "notes": [
                "v4 is an old legacy format with limited support",
                "Many v4 files may fail to convert due to format differences",
                "Consider upgrading v4 files to newer formats when possible",
                "rmrl library may not fully support all v4 file variants",
            ],
            "recommended_action": "upgrade to newer format or manual conversion",
        }
