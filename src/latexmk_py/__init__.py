"""latexmk_py — Python port of latexmk."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from latexmk_py.cli import main

try:
    __version__ = version("latexmk")
except PackageNotFoundError:
    # Fallback for local runs where package metadata is not installed.
    __version__ = "0.0.0+local"

__all__ = ["__version__", "main"]
