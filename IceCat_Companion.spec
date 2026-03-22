# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for IceCat Show Companion
# Build with: pyinstaller IceCat_Companion.spec

import sys
from pathlib import Path

block_cipher = None

# Collect all data files that need to be bundled
datas = [
    # Help guide
    ('help.html', '.'),
    # customtkinter assets (themes, fonts)
    ('venv/Lib/site-packages/customtkinter', 'customtkinter'),
]

# Hidden imports that PyInstaller misses
hidden_imports = [
    # customtkinter
    'customtkinter',
    'customtkinter.windows',
    'customtkinter.windows.widgets',
    'customtkinter.windows.widgets.theme',
    # tkinter DnD
    'tkinterdnd2',
    # audio
    'pygame',
    'pygame.mixer',
    'sounddevice',
    'numpy',
    'scipy',
    'scipy.signal',
    # pycaw / Windows audio
    'pycaw',
    'pycaw.pycaw',
    'pycaw.utils',
    'pycaw.constants',
    'comtypes',
    'comtypes.client',
    'comtypes.server',
    # pedalboard (optional FX)
    'pedalboard',
    'pedalboard.io',
    # other
    'pydub',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'requests',
    'keyboard',
    'pyperclip',
    'wave',
    'json',
    'logging',
    'logging.handlers',
    'pathlib',
    'threading',
    'webbrowser',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'tkinter.test',
        'unittest',
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
    name='IceCat_Companion_v3.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # uncomment if you add an icon
)
