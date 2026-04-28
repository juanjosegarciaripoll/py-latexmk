"""Parser for LaTeX .aux files.

Mirrors ``parse_aux`` / ``parse_aux1`` in ``latexmk.pl`` (lines 7570-7725).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_BIBDATA_RE = re.compile(r"^\\bibdata\{([^}]+)\}")
_BIBSTYLE_RE = re.compile(r"^\\bibstyle\{([^}]+)\}")
_INPUT_RE = re.compile(r"^\\\@input\{([^}]+)\}")


@dataclass(slots=True, frozen=True)
class AuxResult:
    """Parsed bibliography info from a .aux file tree."""

    bib_files: frozenset[str]  # from \\bibdata{...}, extension .bib appended if absent
    bst_files: frozenset[str]  # from \\bibstyle{...}
    aux_inputs: frozenset[str]  # from \\@input{...} (all visited aux files)


def parse_aux(path: Path) -> AuxResult:
    """Parse .aux file(s) recursively for bibliography info.

    Mirrors ``parse_aux`` / ``parse_aux1`` in ``latexmk.pl`` (lines 7570-7725).

    Missing included .aux files are silently skipped.
    Returns an empty ``AuxResult`` when *path* does not exist.
    """
    bib_files: set[str] = set()
    bst_files: set[str] = set()
    aux_inputs: set[str] = set()

    base_dir = path.parent
    _parse_aux1(path, base_dir, bib_files, bst_files, aux_inputs)

    return AuxResult(
        bib_files=frozenset(bib_files),
        bst_files=frozenset(bst_files),
        aux_inputs=frozenset(aux_inputs),
    )


def _parse_aux1(
    path: Path,
    base_dir: Path,
    bib_files: set[str],
    bst_files: set[str],
    aux_inputs: set[str],
) -> None:
    """Recursively parse a single .aux file; mutates the provided sets."""
    if not path.exists():
        return

    aux_inputs.add(str(path))

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip()

        if m := _BIBDATA_RE.match(line):
            for raw_entry in m.group(1).split(","):
                entry = raw_entry.strip()
                if entry:
                    bib_files.add(entry if entry.endswith(".bib") else entry + ".bib")

        elif m := _BIBSTYLE_RE.match(line):
            bst_files.add(m.group(1).strip())

        elif m := _INPUT_RE.match(line):
            child = base_dir / m.group(1)
            if str(child) not in aux_inputs:
                _parse_aux1(child, base_dir, bib_files, bst_files, aux_inputs)
