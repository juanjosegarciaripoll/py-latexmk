# T18: Standalone Distribution (PyInstaller)
**Status:** `todo`
**Depends on:** T01–T17 (all code complete)

## Goal
Package the tool as a self-contained binary with PyInstaller and provide an
install helper script. No Python installation needed on target machines.

## Files
- `latexmk.spec` — PyInstaller spec (commit this)
- `tools/install.py` — cross-platform install helper
- `tools/release.py` — build + rename artifacts for CI
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

Build: `uv run pyinstaller latexmk.spec`
Output: `dist/latexmk` (or `dist/latexmk.exe` on Windows).

## tools/install.py

```
usage: python tools/install.py [--prefix DIR] [--system] [--uninstall] [--no-path]
```

Default install paths:
- Linux/macOS user: `~/.local/bin/latexmk`
- Windows user: `%LOCALAPPDATA%\Programs\latexmk\latexmk.exe`
- System (--system): `/usr/local/bin/latexmk` | `%ProgramFiles%\latexmk\latexmk.exe`

Steps:
1. Locate binary: `dist/latexmk[.exe]` (or accept `--binary PATH`).
2. Create prefix dir.
3. Copy binary.
4. Set executable bit on POSIX (`chmod +x`).
5. Unless `--no-path`: check if prefix is on `PATH`; warn if not.
   On Windows (user install): offer to add to `HKCU\Environment\Path`
   via `winreg` (no elevation needed).
6. Verify: run `latexmk --version` from installed path.
7. Print success message with install location.

`--uninstall`: remove binary (and PATH entry on Windows).

## tools/release.py

Used by CI to produce platform-named artifacts:

```python
import shutil, sys, platform
from pathlib import Path

src = Path('dist') / ('latexmk.exe' if sys.platform == 'win32' else 'latexmk')
arch = platform.machine().lower()
system = sys.platform  # linux, darwin, win32
name = f'latexmk-{system}-{arch}' + ('.exe' if sys.platform == 'win32' else '')
shutil.copy(src, Path('dist') / name)
print(f'Artifact: dist/{name}')
```

## pip / uv install path (secondary)

`pyproject.toml` already has `[project.scripts] latexmk = "latexmk_py:main"`.
Users with Python 3.13:
```bash
pip install .           # installs latexmk console script
uv tool install .       # installs as isolated tool
```

## Checklist
- [ ] `uv run pyinstaller latexmk.spec` produces `dist/latexmk[.exe]`
- [ ] `dist/latexmk --version` works without Python installed
- [ ] `python tools/install.py` copies binary to correct default path
- [ ] `python tools/install.py --uninstall` removes it
- [ ] `python tools/install.py --prefix /tmp/test` installs to custom path
- [ ] Windows: PATH registry write works without elevation
- [ ] `pip install .` + `latexmk --version` works
- [ ] CI: `release.py` produces correct artifact name per platform
