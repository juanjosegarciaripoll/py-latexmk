"""Parser for *latex .log files.

Mirrors ``parse_log`` in ``latexmk.pl`` (lines 6119-6550).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# ── compiled patterns ─────────────────────────────────────────────────────────

_RERUN_RE = re.compile(r"Rerun to get")

_MISSING_FILE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        r"^No file\s+(.*)\.$",
        r"^No file\s+(.+)\s*$",
        r"^! LaTeX Error: File `([^']*)' not found\.",
        r"^! I can't find file `([^']*)'",
        r".*?:\d*: LaTeX Error: File `([^']*)' not found\.",
        r"^LaTeX Warning: File `([^']*)' not found",
        r"^Package .* [fF]ile `([^']*)' not found",
        r"^Package .* No file `([^']*)'",
        r"Error: pdflatex \(file ([^)]*)\): cannot find image file",
        r"cannot open\s+([^:]+): No such file or directory",
        r": File (.*) not found:\s*$",
        r"! Unable to load picture or PDF file '([^']+)'\.",
    )
)

# Each tuple: (pattern, affects_bad_references, affects_bad_citations)
_REF_UNDEF_PAT = (
    r"^LaTeX Warning: ((?:Hyper reference|Reference)"
    r" `[^']+' on page .+ undefined on input line .*)\.?$"
)
_WARNING_SPECS: tuple[tuple[re.Pattern[str], bool, bool], ...] = (
    (re.compile(_REF_UNDEF_PAT), True, False),
    (
        re.compile(r"^Package natbib Warning: (Citation[^\x01]*undefined on input line .*)\.?$"),
        False,
        True,
    ),
    (re.compile(r"^LaTeX Warning: (Label `[^']+' multiply defined.*)\.?$"), False, False),
    (
        re.compile(
            r"^LaTeX Warning: (Citation [`'][^']+' on page .* undefined on input line .*)\.?$"
        ),
        False,
        True,
    ),
)

_ERROR_RE = re.compile(r"^(?:! |[^\s].*:\d+: )")


# ── result dataclass ──────────────────────────────────────────────────────────


@dataclass(slots=True, frozen=True)
class LogResult:
    """Parsed signals from a *latex .log file."""

    rerun_needed: bool
    missing_files: frozenset[str]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    bad_references: int
    bad_citations: int


# ── helpers ───────────────────────────────────────────────────────────────────


def _match_warning(line: str) -> tuple[str, bool, bool] | None:
    """Return (text, is_ref, is_cit) if *line* matches a warning pattern."""
    for pattern, is_ref, is_cit in _WARNING_SPECS:
        if m := pattern.match(line):
            return m.group(1), is_ref, is_cit
    return None


def _match_missing(line: str) -> str | None:
    """Return the missing file name if *line* matches a missing-file pattern."""
    for pattern in _MISSING_FILE_PATTERNS:
        if m := pattern.search(line):
            return m.group(1).strip()
    return None


# ── public function ───────────────────────────────────────────────────────────


def parse_log(path: Path) -> LogResult:
    """Parse a *latex .log file for build signals.

    Mirrors ``parse_log`` in ``latexmk.pl`` (lines 6119-6550).

    Returns an empty ``LogResult`` when *path* does not exist.
    """
    if not path.exists():
        return LogResult(
            rerun_needed=False,
            missing_files=frozenset(),
            warnings=(),
            errors=(),
            bad_references=0,
            bad_citations=0,
        )

    rerun_needed = False
    missing_files: set[str] = set()
    warnings: list[str] = []
    errors: list[str] = []
    bad_references = 0
    bad_citations = 0

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if _RERUN_RE.search(line):
            rerun_needed = True

        if hit := _match_warning(line):
            text, is_ref, is_cit = hit
            warnings.append(text)
            bad_references += is_ref
            bad_citations += is_cit
            continue

        if missing := _match_missing(line):
            missing_files.add(missing)
            continue

        if _ERROR_RE.match(line):
            errors.append(line)

    return LogResult(
        rerun_needed=rerun_needed,
        missing_files=frozenset(missing_files),
        warnings=tuple(warnings),
        errors=tuple(errors),
        bad_references=bad_references,
        bad_citations=bad_citations,
    )
