#!/usr/bin/env python3
"""Setup script for ReMarkable Backup Tool."""

from pathlib import Path
from setuptools import setup
import re

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read version from __version__.py
version_file = Path(__file__).parent / "src" / "__version__.py"
version = "1.0.0"  # default
if version_file.exists():
    version_content = version_file.read_text(encoding="utf-8")
    version_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', version_content, re.M)
    if version_match:
        version = version_match.group(1)

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="remarkable-backup-tool",
    version=version,
    description="A tool to backup ReMarkable tablet files via USB with incremental sync",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ReMarkable Backup Tool",
    python_requires=">=3.7",
    packages=["src", "src.backup", "src.converters"],
    package_dir={"src": "src"},
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "remarkable-backup=src.remarkable_backup:main",
            "remarkable-converter=src.hybrid_converter:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: Utilities",
    ],
)
