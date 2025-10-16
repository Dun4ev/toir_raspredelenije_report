# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

VERSION = "1.1"

try:
    PROJECT_ROOT = Path(__file__).resolve().parent
except NameError:  # PyInstaller executes .spec via exec(), __file__ отсутствует
    PROJECT_ROOT = Path.cwd()
SRC_DIR = PROJECT_ROOT / "src"


a = Analysis(
    ['run_ui.py'],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[('Template', 'Template')],
    hiddenimports=['toir_manager', 'toir_manager.ui.desktop', 'toir_raspredelenije'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'toir_raspredelenije_{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon_toir_raspredelenije_report.ico'],
)
