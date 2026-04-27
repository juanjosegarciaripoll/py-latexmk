"""Scaffold smoke tests — verify the package imports and basic platform helpers work."""

from __future__ import annotations

from pathlib import Path

from latexmk_py.errors import (
    BadOptionsError,
    BuildError,
    ConfigError,
    FileMissingError,
    InternalError,
    LatexmkError,
)
from latexmk_py.platform import default_viewer, system_config_dir, user_config_dir


def test_error_hierarchy() -> None:
    assert issubclass(ConfigError, LatexmkError)
    assert issubclass(BadOptionsError, LatexmkError)
    assert issubclass(FileMissingError, LatexmkError)
    assert issubclass(BuildError, LatexmkError)
    assert issubclass(InternalError, LatexmkError)


def test_default_viewer_returns_string() -> None:
    assert isinstance(default_viewer("pdf"), str)
    assert "%S" in default_viewer("pdf")


def test_config_dirs_return_paths() -> None:
    assert isinstance(user_config_dir(), Path)
    assert isinstance(system_config_dir(), Path)
    assert user_config_dir().name == "latexmk"
    assert system_config_dir().name == "latexmk"
