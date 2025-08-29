"""
ReMarkable v6 format converter using rmc library.

Handles conversion of ReMarkable v6 format .rm files to PDF using the rmc tool.
This is the current format used by ReMarkable tablets.
"""

import subprocess
import tempfile
from pathlib import Path

from .base_converter import BaseConverter


class V6Converter(BaseConverter):
    """Converter for ReMarkable v6 format files using rmc library.
    
    The v6 format is the current format used by ReMarkable tablets.
    This converter uses the 'rmc' command-line tool to convert files
    through an SVG intermediate format.
    
    Conversion Process:
    1. Use rmc to convert .rm file to SVG
    2. Use svglib/reportlab to convert SVG to PDF
    3. Clean up temporary files
    """
    
    def __init__(self):
        """Initialize the v6 converter."""
        super().__init__("v6")
    
    def can_convert(self, rm_file: Path) -> bool:
        """Check if this converter can handle the given .rm file.
        
        Checks if the file has a v6 format header by reading the first
        few bytes of the file.
        
        Args:
            rm_file: Path to the .rm file to check
            
        Returns:
            bool: True if this is a v6 format file
        """
        version = self.detect_version(rm_file)
        return version == "6"
    
    def convert_to_pdf(self, rm_file: Path, output_file: Path) -> bool:
        """Convert a v6 .rm file to PDF using rmc tool.
        
        Uses rmc to convert the .rm file to SVG format first, then
        converts the SVG to PDF using svglib/reportlab.
        
        Args:
            rm_file: Path to the source v6 .rm file
            output_file: Path where the PDF should be created
            
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        try:
            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                svg_file = temp_path / f"{rm_file.stem}.svg"
                
                # Step 1: Convert .rm to SVG using rmc
                self.logger.debug("Converting %s to SVG using rmc", rm_file.name)
                result = subprocess.run([
                    'rmc', '-t', 'svg', '-o', str(svg_file), str(rm_file)
                ], capture_output=True, text=True, timeout=30, check=False)
                
                if result.returncode != 0:
                    self.logger.debug("rmc conversion failed for %s: %s", 
                                    rm_file.name, result.stderr)
                    return False
                
                if not svg_file.exists():
                    self.logger.debug("rmc did not create SVG file for %s", rm_file.name)
                    return False
                
                # Check if SVG file has reasonable content
                if svg_file.stat().st_size < 100:
                    self.logger.debug("SVG file too small for %s", rm_file.name)
                    return False
                
                # Step 2: Convert SVG to PDF
                self.logger.debug("Converting SVG to PDF for %s", rm_file.name)
                success = self.svg_to_pdf(svg_file, output_file)
                
                if success:
                    self.logger.debug("v6 conversion successful: %s -> %s", 
                                    rm_file.name, output_file.name)
                    return True
                else:
                    self.logger.debug("SVG to PDF conversion failed for %s", rm_file.name)
                    return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning("rmc conversion timeout for %s", rm_file.name)
            return False
        except Exception as e:  # noqa: BLE001
            self.logger.debug("v6 conversion error for %s: %s", rm_file.name, e)
            return False
    
    def is_rmc_available(self) -> bool:
        """Check if the rmc tool is available on the system.
        
        Returns:
            bool: True if rmc command is available, False otherwise
        """
        try:
            result = subprocess.run(['rmc', '--version'], 
                                  capture_output=True, text=True, timeout=5, check=False)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_requirements(self) -> list[str]:
        """Get the external requirements for this converter.
        
        Returns:
            list[str]: List of required external tools/libraries
        """
        return [
            "rmc command-line tool",
            "svglib Python library", 
            "reportlab Python library"
        ]
