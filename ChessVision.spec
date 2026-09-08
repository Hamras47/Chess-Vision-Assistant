# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=["keyring.backends.Windows"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torchvision", "onnx", "onnxruntime", "sklearn", "matplotlib"],
    noarchive=False,
)
# PySide 6.11 ships a newer MSVC runtime than Python 3.14. Keep the matching
# runtime at the DLL search root so Windows does not load Python's older copy.
import PySide6
pyside_dir = Path(PySide6.__file__).parent
runtime_names = (
    "VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "MSVCP140.dll", "MSVCP140_1.dll",
    "MSVCP140_2.dll", "MSVCP140_CODECvt_IDS.dll", "CONCRT140.dll",
)
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.upper() not in {name.upper() for name in runtime_names}]
# Qt uses the Windows system ICU. Codex's build host can expose an unrelated
# Poppler ICU on PATH; never collect that host-only DLL into this application.
a.binaries = [entry for entry in a.binaries if not Path(entry[0]).name.lower().startswith("icu")]
for name in runtime_names:
    source = pyside_dir / name
    if source.is_file():
        a.binaries.append((name, str(source), "BINARY"))
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ChessVision",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version=str(root / "assets" / "windows-version.txt"),
    icon=str(root / "assets" / "icons" / "chess-vision.ico"),
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=True,
    name="ChessVision",
)
