"""
V5 Converter - Internal Helper Module

This is a helper module for converting v5 format ReMarkable files.
Do not run directly - use RemarkableSync.py as the entry point.

Entry Point:
    RemarkableSync.py convert [OPTIONS]

This module provides:
- Conversion of v5 format .rm files (legacy ReMarkable format)
- Integration with rmrl Python library
- SVG intermediate format processing
"""

import tempfile
from pathlib import Path

from .base_converter import BaseConverter


class V5Converter(BaseConverter):
    """Converter for ReMarkable v5 format files using rmrl library.

    The v5 format is a legacy format used by older ReMarkable tablets.
    This converter uses the 'rmrl' Python library to convert files,
    typically through SVG intermediate format.

    Conversion Process:
    1. Use rmrl to render .rm file to SVG format
    2. Use svglib/reportlab to convert SVG to PDF
    3. Clean up temporary files

    Note: rmrl library support may vary depending on the specific
    v5 file structure and content.
    """

    def __init__(self):
        """Initialize the v5 converter."""
        super().__init__("v5")

    def can_convert(self, rm_file: Path) -> bool:
        """Check if this converter can handle the given .rm file.

        Checks if the file has a v5 format header by reading the first
        few bytes of the file.

        Args:
            rm_file: Path to the .rm file to check

        Returns:
            bool: True if this is a v5 format file
        """
        version = self.detect_version(rm_file)
        return version == "5"

    def convert_to_pdf(self, rm_file: Path, output_file: Path) -> bool:
        """Convert a v5 .rm file to PDF using rmrl library.

        Uses rmrl to render the .rm file to SVG format first, then
        converts the SVG to PDF using svglib/reportlab.

        Args:
            rm_file: Path to the source v5 .rm file
            output_file: Path where the PDF should be created

        Returns:
            bool: True if conversion was successful, False otherwise
        """
        try:
            # Import rmrl on demand to handle missing dependencies gracefully
            import rmrl  # type: ignore # pylint: disable=import-outside-toplevel
        except ImportError:
            self.logger.debug("rmrl library not available for v5 conversion")
            return False

        try:
            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                svg_file = temp_path / f"{rm_file.stem}.svg"

                # Step 1: Convert .rm to SVG using rmrl
                self.logger.debug("Converting %s to SVG using rmrl", rm_file.name)

                # Try to render to SVG format
                svg_data = rmrl.render(str(rm_file))
                if not svg_data:
                    self.logger.debug("rmrl failed to render %s", rm_file.name)
                    return False

                # Write SVG data to temporary file
                with open(svg_file, "wb") as f:
                    f.write(svg_data)

                # Verify SVG file was created with reasonable content
                if not svg_file.exists() or svg_file.stat().st_size < 100:
                    self.logger.debug("rmrl SVG output too small for %s", rm_file.name)
                    return False

                # Step 2: Convert SVG to PDF
                self.logger.debug("Converting SVG to PDF for %s", rm_file.name)
                success = self.svg_to_pdf(svg_file, output_file)

                if success:
                    self.logger.debug(
                        "v5 conversion successful: %s -> %s", rm_file.name, output_file.name
                    )
                    return True

                self.logger.debug("SVG to PDF conversion failed for %s", rm_file.name)
                return False

        except (ImportError, OSError, ValueError) as e:
            self.logger.debug("v5 conversion error for %s: %s", rm_file.name, e)

            # Try alternative rmrl rendering approach
            return self._try_alternative_conversion(rm_file, output_file)

    def _try_alternative_conversion(self, rm_file: Path, output_file: Path) -> bool:
        """Try alternative rmrl conversion methods.

        Some v5 files may require different rendering approaches.
        This method attempts alternative conversion strategies.

        Args:
            rm_file: Path to the source v5 .rm file
            output_file: Path where the PDF should be created

        Returns:
            bool: True if conversion was successful, False otherwise
        """
        import importlib.util

        if importlib.util.find_spec("rmrl") is None:
            return False

        try:
            # Try direct PDF rendering if supported
            self.logger.debug("Trying alternative rmrl conversion for %s", rm_file.name)

            # Alternative approaches could include:
            # - Different rmrl rendering options
            # - Direct PDF output if supported
            # - Canvas-based rendering

            # For now, we'll log the attempt and return False
            # This can be expanded as more rmrl capabilities are discovered
            self.logger.debug(
                "Alternative conversion not yet implemented for %s -> %s",
                rm_file.name,
                output_file.name,
            )
            return False

        except (ImportError, OSError, ValueError) as e:
            self.logger.debug("Alternative v5 conversion failed for %s: %s", rm_file.name, e)
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
