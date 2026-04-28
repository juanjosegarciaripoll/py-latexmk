"""Parser for *.fls* recorder files produced by *latex -recorder.

Mirrors ``parse_fls`` in ``latexmk.pl`` (lines 7153-7384).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PWD_RE = re.compile(r"^\s*PWD\s+(.*)$")
_INPUT_RE = re.compile(r"^\s*INPUT\s+(.*)$")
_OUTPUT_RE = re.compile(r"^\s*OUTPUT\s+(.*)$")


@dataclass(slots=True, frozen=True)
class FlsResult:
    """Parsed contents of a .fls recorder file."""

    pwd: str  # PWD line value; empty when absent
    inputs: frozenset[Path]  # INPUT paths, pwd prefix stripped when present
    outputs: frozenset[Path]  # OUTPUT paths, pwd prefix stripped when present


def parse_fls(path: Path) -> FlsResult:
    """Parse a .fls recorder file.

    Mirrors ``parse_fls`` in ``latexmk.pl`` (lines 7153-7384).

    Returns an empty ``FlsResult`` when *path* does not exist.
    """
    if not path.exists():
        return FlsResult(pwd="", inputs=frozenset(), outputs=frozenset())

    pwd = ""
    pwd_prefix = ""
    inputs: set[Path] = set()
    outputs: set[Path] = set()

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        # Normalise line endings and path separators (MiKTeX uses backslash).
        line = raw.rstrip("\r\n").replace("\\", "/")

        if m := _PWD_RE.match(line):
            pwd = m.group(1)
            pwd_prefix = pwd if pwd.endswith("/") else pwd + "/"
        elif m := _INPUT_RE.match(line):
            file_str = m.group(1)
            if pwd_prefix and file_str.startswith(pwd_prefix):
                file_str = file_str[len(pwd_prefix) :]
            inputs.add(Path(file_str))
        elif m := _OUTPUT_RE.match(line):
            file_str = m.group(1)
            if pwd_prefix and file_str.startswith(pwd_prefix):
                file_str = file_str[len(pwd_prefix) :]
            outputs.add(Path(file_str))

    return FlsResult(pwd=pwd, inputs=frozenset(inputs), outputs=frozenset(outputs))
