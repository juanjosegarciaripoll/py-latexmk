# T01: Project Scaffold
**Status:** `todo`
**Depends on:** nothing

## Goal
Set up the full project skeleton: pyproject.toml with all tool config, the
package structure, error hierarchy, and platform helpers. After this task
`uv run pytest -q` collects (and passes) even with no test bodies.

## Files to create/modify

- `pyproject.toml` — complete tool config (ruff, mypy, basedpyright, pytest)
- `latexmk_py/__init__.py` — `from latexmk_py.cli import main; __all__ = ["main"]`
- `latexmk_py/__main__.py` — `from latexmk_py import main; main()`
- `latexmk_py/errors.py` — exception hierarchy
- `latexmk_py/platform.py` — platform helpers
- `tests/conftest.py` — pytest custom flags
- `.gitignore` — dist/, .venv/, __pycache__, *.pyc

## pyproject.toml requirements

```toml
[project]
name = "latexmk"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = []

[project.scripts]
latexmk = "latexmk_py:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
# managed env

[tool.ruff]
line-length = 100
target-version = "py313"
src = ["latexmk_py", "tests", "tools"]

[tool.ruff.lint]
select = ["ALL"]
ignore = ["D203","D213","COM812","ISC001","PLR0911","PLR0912","PLR0913",
          "PLR0915","TRY003","EM101","EM102"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101","PLR2004","ANN","D"]
"tools/**" = ["T201"]

[tool.ruff.format]
docstring-code-format = true

[tool.mypy]
python_version = "3.13"
strict = true
warn_unreachable = true
enable_error_code = ["redundant-self","truthy-bool","ignore-without-code"]
files = ["latexmk_py","tests","tools"]

[tool.basedpyright]
include = ["latexmk_py","tests","tools"]
typeCheckingMode = "strict"
reportAny = "error"
reportExplicitAny = "error"
reportImplicitOverride = "error"
reportMissingTypeStubs = "warning"
pythonVersion = "3.13"

[tool.pytest.ini_options]
addopts = "-ra --strict-markers --strict-config"
testpaths = ["tests"]
markers = [
  "integration: tests requiring external TeX programs",
  "differential: tests requiring a reference Perl latexmk",
]
```

## errors.py

```python
from __future__ import annotations

class LatexmkError(Exception):
    """Base for all latexmk errors."""

class ConfigError(LatexmkError):
    """Exit 13 — bad configuration."""

class BadOptionsError(LatexmkError):
    """Exit 10 — bad CLI options."""

class FileMissingError(LatexmkError):
    """Exit 11 — required input file not found."""

class BuildError(LatexmkError):
    """Exit 12 — *latex or secondary tool failed."""

class InternalError(LatexmkError):
    """Exit 20 — unexpected internal state."""
```

## platform.py key interface

```python
from __future__ import annotations
import sys
from pathlib import Path

def is_windows() -> bool: ...
def is_macos() -> bool: ...

def default_viewer(fmt: str) -> str:
    """Return 'open %S' / 'start "" %S' / 'xdg-open %S'."""

def user_config_dir() -> Path:
    """~/.config/latexmk (XDG) or %APPDATA%\latexmk (Windows)."""

def system_config_dir() -> Path:
    """/etc/latexmk or %ProgramData%\latexmk."""
```

## conftest.py

```python
import pytest

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--runintegration", action="store_true",
                     help="Run integration tests (require TeX install)")
    parser.addoption("--rundiff", action="store_true",
                     help="Run differential tests (require LATEXMK_PERL env var)")

def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--runintegration"):
        skip = pytest.mark.skip(reason="pass --runintegration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
    if not config.getoption("--rundiff"):
        skip = pytest.mark.skip(reason="pass --rundiff")
        for item in items:
            if "differential" in item.keywords:
                item.add_marker(skip)
```

## Checklist
- [ ] `uv sync --all-extras --dev` succeeds
- [ ] `uv run ruff format && uv run ruff check --fix` clean
- [ ] `uv run basedpyright` clean
- [ ] `uv run mypy .` clean
- [ ] `uv run pytest -q` exits 0 (no tests yet, that is OK)
- [ ] `python -m latexmk_py` prints something (or exits gracefully)
