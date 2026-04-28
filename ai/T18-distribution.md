# T18: Release Distribution (Binary Artifacts + Package Manager Consumption)
**Status:** `in-progress`
**Depends on:** T01–T17 (all code complete)

## Goal
Produce self-contained executables for Windows/macOS/Linux at release time,
plus relocatable package artifacts that packaging tools can consume.
Also support install-from-source for Python users.

## Files
- `latexmk.spec` — PyInstaller spec (commit this)
- `tools/release.py` — release build + artifact staging/renaming
- `packaging/` — package-manager manifests/templates (winget/homebrew/etc.)
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

## tools/release.py

Used by CI at release time to produce platform/arch artifacts and
relocatable package payloads:

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

Minimum outputs per platform:
- Standalone binary: `dist/latexmk[.exe]`
- Renamed artifact: `dist/latexmk-<platform>-<arch>[.exe]`
- Relocatable payload (archive or equivalent) containing binary + metadata for
  packaging-tool consumption.

## Packaging consumption targets

Provide package metadata/templates in `packaging/` so release artifacts can be
consumed by package managers.

- Windows: winget local manifest workflow is first-class.
  - Expected user flow: `winget install --manifest <path-to-manifest-dir>`
  - The manifest references the release artifact URL/path and checksum.
- macOS: Homebrew tap formula template referencing release artifact + checksum.
- Linux: document generic relocatable archive consumption and include templates
  for at least one common packaging path (for example, distro package recipe or
  simple install script expectations).

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
- [ ] `uv run pyinstaller latexmk.spec` produces `dist/latexmk[.exe]`
- [ ] Release workflow builds platform binaries for Windows/macOS/Linux
- [ ] Release workflow emits relocatable package artifact(s)
- [ ] Windows: local winget manifest can install from produced artifact
- [ ] macOS: Homebrew formula/template references produced artifact + checksum
- [ ] Linux: relocatable artifact consumption path is documented and tested
- [ ] `pip install .` + `latexmk --version` works
- [ ] `uv tool install .` + `latexmk --version` works
- [ ] CI/release: `release.py` produces correct artifact name per platform
