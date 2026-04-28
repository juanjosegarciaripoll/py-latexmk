# py-latexmk

Python port of `latexmk` for Linux, macOS, and Windows.

## Install

### Windows (prebuilt binary)

Download `latexmk.exe` from this repository's GitHub Releases, place it in a
directory on `PATH`, then verify:

```powershell
latexmk --version
```

### Install from source (Python 3.13+)

```bash
pip install .
latexmk --version
```

Or:

```bash
uv tool install .
latexmk --version
```

## Usage

```bash
latexmk -pdf main.tex
latexmk -pvc -pdf main.tex
latexmk -c main.tex
latexmk -C main.tex
```

See full user documentation in [docs/latexmk.md](docs/latexmk.md).
