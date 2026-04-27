"""Exception hierarchy for latexmk_py."""

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
