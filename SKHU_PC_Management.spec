# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)
local_product_keys = project_root / "src" / "skhu_pc_management" / "infrastructure" / "license" / "local_product_keys.py"
app_icon = project_root / "resources" / "images" / "skhu_logo.ico"
release_readme = project_root / "packaging" / "README_RELEASE.txt"

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "wmi",
    "win32com",
    "win32com.client",
    "pythoncom",
    "pywintypes",
]
if local_product_keys.exists():
    hiddenimports.append("skhu_pc_management.infrastructure.license.local_product_keys")

a = Analysis(
    [str(project_root / "src" / "skhu_pc_management" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "resources"), "resources"),
        (str(release_readme), "."),
    ],
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="SKHU_PC_Management",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=str(app_icon),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SKHU_PC_Management",
)
