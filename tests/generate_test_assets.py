#!/usr/bin/env python3
"""
Generate test assets for ReMarkable PDF conversion testing.

Creates mock ReMarkable files for different format versions to test
the PDF conversion functionality.
"""

import struct
from pathlib import Path


def create_v3_test_file(output_path: Path):
    """Create a mock v3 ReMarkable file for testing.

    Args:
        output_path: Path where the test file should be created
    """
    # V3 format typically has a simple binary structure
    # Create a minimal valid v3 file
    with open(output_path, "wb") as f:
        # V3 header (simplified)
        f.write(b"reMarkable lines with selections and layers\n")
        f.write(struct.pack("<I", 3))  # Version number
        f.write(struct.pack("<I", 1))  # Number of layers

        # Layer data
        f.write(struct.pack("<I", 1))  # Number of strokes

        # Stroke data (pen type, color, unknown, width)
        f.write(struct.pack("<I", 2))  # Pen type (ballpoint)
        f.write(struct.pack("<I", 0))  # Color (black)
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 2.0))  # Width
        f.write(struct.pack("<I", 0))  # Unknown

        # Points data
        f.write(struct.pack("<I", 3))  # Number of points

        # Sample points (x, y, speed, direction, width, pressure)
        points = [
            (100.0, 100.0, 0.0, 0.0, 2.0, 1.0),
            (200.0, 200.0, 0.0, 0.0, 2.0, 1.0),
            (300.0, 100.0, 0.0, 0.0, 2.0, 1.0),
        ]

        for x, y, speed, direction, width, pressure in points:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))


def create_v4_test_file(output_path: Path):
    """Create a mock v4 ReMarkable file for testing.

    Args:
        output_path: Path where the test file should be created
    """
    # V4 format is similar to v3 but with slight differences
    with open(output_path, "wb") as f:
        # V4 header
        f.write(b"reMarkable lines with selections and layers\n")
        f.write(struct.pack("<I", 4))  # Version number
        f.write(struct.pack("<I", 1))  # Number of layers

        # Layer data
        f.write(struct.pack("<I", 1))  # Number of strokes

        # Stroke data
        f.write(struct.pack("<I", 2))  # Pen type
        f.write(struct.pack("<I", 0))  # Color
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 2.0))  # Width
        f.write(struct.pack("<I", 0))  # Unknown

        # Points data
        f.write(struct.pack("<I", 4))  # Number of points

        # Sample points with slightly different format
        points = [
            (50.0, 50.0, 0.0, 0.0, 2.0, 1.0),
            (150.0, 150.0, 0.0, 0.0, 2.0, 1.0),
            (250.0, 50.0, 0.0, 0.0, 2.0, 1.0),
            (350.0, 150.0, 0.0, 0.0, 2.0, 1.0),
        ]

        for x, y, speed, direction, width, pressure in points:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))


def create_v5_test_file(output_path: Path):
    """Create a mock v5 ReMarkable file for testing.

    Args:
        output_path: Path where the test file should be created
    """
    # V5 format has a more complex structure
    with open(output_path, "wb") as f:
        # V5 header
        f.write(b"reMarkable .lines file, version=5          ")
        f.write(struct.pack("<I", 1))  # Number of layers

        # Layer data
        f.write(struct.pack("<I", 2))  # Number of strokes

        # First stroke
        f.write(struct.pack("<I", 2))  # Pen type
        f.write(struct.pack("<I", 0))  # Color
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 1.5))  # Width
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<I", 3))  # Number of points

        # Points for first stroke
        points1 = [
            (75.0, 75.0, 0.0, 0.0, 1.5, 0.8),
            (175.0, 175.0, 0.0, 0.0, 1.5, 1.0),
            (275.0, 75.0, 0.0, 0.0, 1.5, 0.8),
        ]

        for x, y, speed, direction, width, pressure in points1:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))

        # Second stroke
        f.write(struct.pack("<I", 3))  # Pen type (marker)
        f.write(struct.pack("<I", 1))  # Color (gray)
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 3.0))  # Width
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<I", 2))  # Number of points

        # Points for second stroke
        points2 = [
            (100.0, 200.0, 0.0, 0.0, 3.0, 1.0),
            (250.0, 200.0, 0.0, 0.0, 3.0, 1.0),
        ]

        for x, y, speed, direction, width, pressure in points2:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))


def create_v6_test_file(output_path: Path):
    """Create a mock v6 ReMarkable file for testing.

    Args:
        output_path: Path where the test file should be created
    """
    # V6 format (current format) - more sophisticated structure
    with open(output_path, "wb") as f:
        # V6 header
        f.write(b"reMarkable .lines file, version=6          ")
        f.write(struct.pack("<I", 1))  # Number of layers

        # Layer data
        f.write(struct.pack("<I", 3))  # Number of strokes

        # First stroke - pen
        f.write(struct.pack("<I", 2))  # Pen type (ballpoint)
        f.write(struct.pack("<I", 0))  # Color (black)
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 1.875))  # Width
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<I", 5))  # Number of points

        # Points for pen stroke (curved line)
        pen_points = [
            (50.0, 300.0, 0.0, 0.0, 1.875, 0.5),
            (100.0, 250.0, 0.0, 0.0, 1.875, 0.8),
            (150.0, 200.0, 0.0, 0.0, 1.875, 1.0),
            (200.0, 250.0, 0.0, 0.0, 1.875, 0.8),
            (250.0, 300.0, 0.0, 0.0, 1.875, 0.5),
        ]

        for x, y, speed, direction, width, pressure in pen_points:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))

        # Second stroke - marker
        f.write(struct.pack("<I", 3))  # Pen type (marker)
        f.write(struct.pack("<I", 1))  # Color (gray)
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 5.0))  # Width
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<I", 3))  # Number of points

        # Points for marker stroke (thick line)
        marker_points = [
            (75.0, 400.0, 0.0, 0.0, 5.0, 1.0),
            (150.0, 350.0, 0.0, 0.0, 5.0, 1.0),
            (225.0, 400.0, 0.0, 0.0, 5.0, 1.0),
        ]

        for x, y, speed, direction, width, pressure in marker_points:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))

        # Third stroke - pencil
        f.write(struct.pack("<I", 1))  # Pen type (pencil)
        f.write(struct.pack("<I", 0))  # Color (black)
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<f", 1.0))  # Width
        f.write(struct.pack("<I", 0))  # Unknown
        f.write(struct.pack("<I", 4))  # Number of points

        # Points for pencil stroke (light sketch)
        pencil_points = [
            (300.0, 150.0, 0.0, 0.0, 1.0, 0.3),
            (350.0, 200.0, 0.0, 0.0, 1.0, 0.6),
            (400.0, 150.0, 0.0, 0.0, 1.0, 0.4),
            (450.0, 200.0, 0.0, 0.0, 1.0, 0.5),
        ]

        for x, y, speed, direction, width, pressure in pencil_points:
            f.write(struct.pack("<ffffff", x, y, speed, direction, width, pressure))


def main():
    """Generate all test assets."""
    # Get the assets directory
    assets_dir = Path(__file__).parent / "assets"

    # Create test files for each version
    create_v3_test_file(assets_dir / "v3" / "test_v3_simple.rm")
    create_v3_test_file(assets_dir / "v3" / "test_v3_complex.rm")

    create_v4_test_file(assets_dir / "v4" / "test_v4_simple.rm")
    create_v4_test_file(assets_dir / "v4" / "test_v4_complex.rm")

    create_v5_test_file(assets_dir / "v5" / "test_v5_simple.rm")
    create_v5_test_file(assets_dir / "v5" / "test_v5_complex.rm")

    create_v6_test_file(assets_dir / "v6" / "test_v6_simple.rm")
    create_v6_test_file(assets_dir / "v6" / "test_v6_complex.rm")

    print("Test assets generated successfully!")
    print(f"Assets directory: {assets_dir.absolute()}")


if __name__ == "__main__":
    main()
