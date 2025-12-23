# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ReMarkable Hybrid Converter
This creates a standalone executable for converting reMarkable notebooks to PDFs.
"""

import sys
from pathlib import Path

block_cipher = None

# Determine platform-specific settings
if sys.platform == 'darwin':
    # macOS specific settings
    icon_file = None  # Can add .icns file here
elif sys.platform == 'win32':
    # Windows specific settings
    icon_file = None  # Can add .ico file here
else:
    icon_file = None

a = Analysis(
    ['hybrid_converter.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include the converters module
        ('converters', 'converters'),
    ],
    hiddenimports=[
        'converters',
        'converters.base_converter',
        'converters.v4_converter',
        'converters.v5_converter',
        'converters.v6_converter',
        'click',
        'tqdm',
        'pathlib2',
        # PDF-related libraries
        'PyPDF2',
        'svglib',
        'reportlab',
        # Additional hidden imports
        '_cffi_backend',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RemarkableConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

# Create a macOS .app bundle (optional, only on macOS)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='RemarkableConverter.app',
        icon=icon_file,
        bundle_identifier='com.remarkablesync.converter',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
        },
    )
