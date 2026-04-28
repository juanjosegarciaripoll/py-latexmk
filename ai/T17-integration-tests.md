# T17: Integration Tests
**Status:** `done`
**Depends on:** T08–T16 (run as individual tasks complete)

## Goal
Build out the integration test suite. Tests require a working TeX installation
and are gated behind `--runintegration`. Differential tests compare Python
output against Perl latexmk and are gated behind `--rundiff`.

## Files
- `tests/integration/test_simple.py`
- `tests/integration/test_bibtex.py`
- `tests/integration/test_biber.py`
- `tests/integration/test_makeindex.py`
- `tests/integration/test_glossaries.py`
- `tests/integration/test_pvc.py`
- `tests/integration/known_divergences.py`
- `tests/fixtures/simple/hello.tex` (created in T08)
- `tests/fixtures/bibtex/main.tex` + `refs.bib` (created in T09)
- `tests/fixtures/biblatex/main.tex` + `refs.bib` (created in T09)
- `tests/fixtures/makeindex/main.tex` (created in T10)
- `tests/fixtures/glossaries/main.tex` (created in T10)
- `tests/fixtures/multichapter/main.tex` + chapters

## multichapter fixture

```latex
% tests/fixtures/multichapter/main.tex
\documentclass{book}
\begin{document}
\include{ch1}
\include{ch2}
\end{document}
```
```latex
% tests/fixtures/multichapter/ch1.tex
\chapter{Chapter One} Hello from chapter one.
```
```latex
% tests/fixtures/multichapter/ch2.tex
\chapter{Chapter Two} Hello from chapter two.
```

## Test patterns

All integration tests follow this pattern:

```python
import pytest, shutil, subprocess, sys
from pathlib import Path

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'simple'

@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path / 'src')
    return tmp_path / 'src'

def test_simple_build(workdir: Path) -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'latexmk_py', '-pdf', '-norc', 'hello.tex'],
        cwd=workdir, capture_output=True, text=True
    )
    assert result.returncode == 0
    assert (workdir / 'hello.pdf').exists()

def test_incremental_no_rerun(workdir: Path) -> None:
    # First build
    subprocess.run([sys.executable, '-m', 'latexmk_py', '-pdf', '-norc', 'hello.tex'],
                   cwd=workdir, check=True)
    # Second build: output should say "nothing to do"
    result = subprocess.run(
        [sys.executable, '-m', 'latexmk_py', '-pdf', '-norc', 'hello.tex'],
        cwd=workdir, capture_output=True, text=True
    )
    assert result.returncode == 0
    assert 'nothing to do' in result.stdout.lower() or 'up to date' in result.stdout.lower()
```

## Differential test pattern

```python
import os, pytest, shutil, subprocess, sys
from pathlib import Path

pytestmark = pytest.mark.differential

PERL_LATEXMK = os.environ.get('LATEXMK_PERL', '')

@pytest.fixture()
def workdir_pair(tmp_path: Path):
    py_dir = tmp_path / 'python'
    pl_dir = tmp_path / 'perl'
    src = Path(__file__).parent.parent / 'fixtures' / 'simple'
    shutil.copytree(src, py_dir)
    shutil.copytree(src, pl_dir)
    return py_dir, pl_dir

def test_pdf_matches_perl(workdir_pair):
    py_dir, pl_dir = workdir_pair
    subprocess.run([sys.executable, '-m', 'latexmk_py', '-pdf', '-norc', 'hello.tex'],
                   cwd=py_dir, check=True)
    subprocess.run([PERL_LATEXMK, '-pdf', '-norc', 'hello.tex'],
                   cwd=pl_dir, check=True)
    # PDFs may differ in metadata; compare text content or file sizes
    py_size = (py_dir / 'hello.pdf').stat().st_size
    pl_size = (pl_dir / 'hello.pdf').stat().st_size
    # Allow 5% size difference (timestamp metadata differs)
    assert abs(py_size - pl_size) / max(py_size, pl_size) < 0.05
```

## known_divergences.py

Document intentional differences from Perl latexmk:

```python
"""
Known intentional divergences from Perl latexmk.

Each entry: (description, reason)
"""

DIVERGENCES: list[tuple[str, str]] = [
    (
        "No programmable .latexmkrc",
        "Security risk; replaced by TOML config",
    ),
    (
        "No -e CODE / -r PERL_FILE options",
        "Code execution removed; -r now loads TOML",
    ),
    (
        "No banner overlay (-bm -bi -bs -d)",
        "Obsolete PS feature; use external tools",
    ),
]
```

## Coverage

```bash
uv run pytest -q --cov=latexmk_py --cov-fail-under=85 --cov-report=term-missing
```

Target ≥ 90% line coverage on `latexmk_py/` excluding `__main__.py` and CLI
dispatch in `cli.py`.

## Checklist
- [x] All fixture .tex files created and compile with pdflatex
- [x] `test_simple.py`: build, incremental, force, cleanup
- [x] `test_bibtex.py`: bibtex triggered, .bbl produced, PDF has bibliography
- [x] `test_biber.py`: biber triggered, .bbl produced
- [x] `test_makeindex.py`: makeindex triggered, .ind produced
- [x] `test_glossaries.py`: makeglossaries triggered
- [x] `test_pvc.py`: file change triggers rebuild (use threading or subprocess)
- [x] Coverage ≥ 85%
- [x] Differential test infrastructure in place (passes if LATEXMK_PERL set)

