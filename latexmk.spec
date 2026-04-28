# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building standalone latexmk binaries."""

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis

a = Analysis(
    ["src/latexmk_py/__main__.py"],
    pathex=[],
    hiddenimports=[],
    datas=[],
    hookspath=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="latexmk",
    console=True,
    strip=True,
    onefile=True,
)
