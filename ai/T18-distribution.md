# T18: Release Distribution (Windows Binaries + Release Automation)
**Status:** `done`
**Depends on:** T01–T17 (all code complete)

## Goal
Produce release-time Windows prebuilt binaries, generated winget manifests
(internal packaging artifacts), and source tarballs, with source-install
fallback for Python users.

## Files
- `latexmk.spec` — PyInstaller spec (commit this)
- `tools/release.py` — release build + artifact staging/renaming
- `packaging/winget/` — winget manifest templates (rendered into `dist/*.yaml`)
- `.gitignore` — add `dist/`, `build/`

## Dev dependency

```bash
uv add --dev pyinstaller
```

## latexmk.spec

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis

a = Analysis(
    ['latexmk_py/__main__.py'],
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
    name='latexmk',
    console=True,
    strip=True,
    onefile=True,
)
```

Build entry point: `uv run python tools/release.py`
On Windows, this invokes PyInstaller and emits `dist/latexmk.exe`.

## tools/release.py

Used by CI at release time to:

- run PyInstaller (`latexmk.spec`)
- produce release archive + `SHA256SUMS.txt`
- generate concrete winget manifests in `dist/` on Windows

## Packaging consumption target

Provide winget metadata/templates in `packaging/winget/` so release automation
can generate release-aligned manifests.

- Windows: generated manifests reference release artifact URL/path and checksum.
- Current user install path is direct download of prebuilt `latexmk.exe` from
  GitHub Releases (winget publication can be added later).

Exact publishing destination is out of scope for this task. Public registry
submission is optional.

## pip / uv install path (secondary)

`pyproject.toml` already has `[project.scripts] latexmk = "latexmk_py:main"`.
Users with Python 3.13:
```bash
pip install .           # installs latexmk console script
uv tool install .       # installs as isolated tool
```

Source-install remains supported and documented as the standard fallback when
binary/package-manager installs are not used.

## Checklist
- [x] `uv run python tools/release.py` builds Windows executable artifacts
- [x] Release workflow builds Windows artifacts and source tarball
- [x] Release workflow emits checksums and generated winget YAML files
- [x] `pip install .` + `latexmk --version` works
- [x] `uv tool install .` + `latexmk --version` works
- [x] CI/release uses `release.py` as build entry point
