# py-latexmk

Python port of `latexmk` for Linux, macOS, and Windows.

## Install

### Windows (prebuilt binary)

Download `latexmk.exe` from this repository's GitHub Releases, place it in a
directory on `PATH`, then verify:

```powershell
latexmk -version
```

### Install from source (using uv)

We assume you have installed `uv` from [astral-sh](https://docs.astral.sh/uv/)
and configured Python tools to be available. On Windows you can do this with
two steps:
```powershell
winget install astral-sh.uv
uv tool update-shell
```

Then you can install the tool directly from GitHub
```powershell
uv tool install git+https://github.com/juanjosegarciaripoll/py-latexmk
latexmk -version
```

## Usage

```bash
latexmk -pdf main.tex
latexmk -pvc -pdf main.tex
latexmk -c main.tex
latexmk -C main.tex
```

See full user documentation in [docs/latexmk.md](docs/latexmk.md).
