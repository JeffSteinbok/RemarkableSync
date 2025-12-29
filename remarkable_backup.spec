# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ReMarkable Backup Tool
This creates a standalone executable for backing up reMarkable tablet files.
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
    ['remarkable_backup.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include the src package modules
        ('src/backup', 'src/backup'),
        ('src/converters', 'src/converters'),
    ],
    hiddenimports=[
        'src',
        'src.backup',
        'src.backup.backup_manager',
        'src.backup.connection',
        'src.backup.metadata',
        'src.converters',
        'src.converters.base_converter',
        'src.converters.v4_converter',
        'src.converters.v5_converter',
        'src.converters.v6_converter',
        'src.template_renderer',
        'paramiko',
        'scp',
        'click',
        'tqdm',
        'cryptography',
        'pathlib2',
        'requests',
        'dateutil',
        # PDF conversion dependencies (used when --convert-pdf flag is used)
        'PyPDF2',
        'svglib',
        'reportlab',
        # Additional hidden imports for paramiko/cryptography
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.bindings._openssl',
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
    name='RemarkableBackup',
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
        name='RemarkableBackup.app',
        icon=icon_file,
        bundle_identifier='com.remarkablesync.backup',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
        },
    )
