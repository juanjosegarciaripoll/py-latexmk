"""Read and write .fdb_latexmk files.

Mirrors ``rdb_read`` / ``rdb_write`` in ``latexmk.pl`` (lines 8009-8354).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

_FDB_VERSION = 4
_HEADER = f"# Fdb version {_FDB_VERSION}"

# Parser states
_SOURCES = 1
_GENERATED = 2
_REWRITTEN = 3

# ["rule_name"] rest-of-line
_RE_RULE_NAME = re.compile(r'^\["([^"]+)"\](.*)$')
# run_time "source" "dest" "base" check_time last_result
_RE_RULE_TAIL = re.compile(r'^\s*(\S+)\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+(\S+)\s+(\S+)')
# "file" mtime size md5 "from_rule"
_RE_FILE_ENTRY = re.compile(r'^"([^"]*)"\s+(\S+)\s+(\S+)\s+(\S+)\s+"([^"]*)"')
# "file"  (generated / rewritten sections)
_RE_SIMPLE_FILE = re.compile(r'^"([^"]*)"')


@dataclass(slots=True)
class FdbFileEntry:
    """One source-file record inside an .fdb_latexmk rule."""

    path: Path
    mtime: float
    size: int
    md5: str
    from_rule: str  # empty string if not produced by another rule


@dataclass(slots=True)
class FdbRule:
    """One rule block from an .fdb_latexmk file."""

    name: str
    run_time: float
    source: Path
    dest: Path
    base: Path
    check_time: float
    last_result: int
    files: list[FdbFileEntry] = field(default_factory=list)
    generated: list[Path] = field(default_factory=list)
    rewritten_before_read: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_version(first_line: str, path: Path) -> bool:
    """Validate the .fdb_latexmk header line; log and return False on error."""
    header = first_line.strip()
    if not header.startswith("# Fdb version "):
        logger.warning("latexmk: %s: not a valid .fdb_latexmk file", path)
        return False
    try:
        version = int(header.split()[-1])
    except (ValueError, IndexError):
        logger.warning("latexmk: %s: cannot parse version", path)
        return False
    if version != _FDB_VERSION:
        logger.warning(
            "latexmk: %s: incompatible version %d (expected %d)",
            path,
            version,
            _FDB_VERSION,
        )
        return False
    return True


def _parse_rule_header(line: str) -> FdbRule | None:
    """Parse a rule header line; return ``FdbRule`` skeleton or ``None``."""
    m = _RE_RULE_NAME.match(line)
    if not m:
        return None
    mt = _RE_RULE_TAIL.match(m.group(2))
    if not mt:
        return None
    try:
        return FdbRule(
            name=m.group(1),
            run_time=float(mt.group(1)),
            source=Path(mt.group(2)) if mt.group(2) else Path(),
            dest=Path(mt.group(3)) if mt.group(3) else Path(),
            base=Path(mt.group(4)) if mt.group(4) else Path(),
            check_time=float(mt.group(5)),
            last_result=int(mt.group(6)),
        )
    except ValueError:
        return None


def _parse_file_entry(line: str) -> FdbFileEntry | None:
    """Parse a source-file entry line; return ``FdbFileEntry`` or ``None``."""
    mf = _RE_FILE_ENTRY.match(line)
    if not mf:
        return None
    try:
        return FdbFileEntry(
            path=Path(mf.group(1)),
            mtime=float(mf.group(2)),
            size=int(mf.group(3)),
            md5=mf.group(4),
            from_rule=mf.group(5),
        )
    except ValueError:
        return None


def _process_body_line(line: str, rule: FdbRule, state: int) -> int:
    """Dispatch one body line to the correct section; return updated state."""
    if line.startswith("(generated)"):
        return _GENERATED
    if line.startswith("(rewritten before read)"):
        return _REWRITTEN
    if line.startswith("(source)"):
        return _SOURCES
    if state == _SOURCES:
        entry = _parse_file_entry(line)
        if entry is not None:
            rule.files.append(entry)
    elif state in (_GENERATED, _REWRITTEN):
        sf = _RE_SIMPLE_FILE.match(line)
        if sf:
            p = Path(sf.group(1))
            if state == _GENERATED:
                rule.generated.append(p)
            else:
                rule.rewritten_before_read.append(p)
    return state


def _read_fdb_body(lines: list[str], path: Path) -> dict[str, FdbRule]:
    """Parse the body lines (everything after the version header)."""
    rules: dict[str, FdbRule] = {}
    current_rule: FdbRule | None = None
    state = _SOURCES

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("#", "%")):
            continue
        if _RE_RULE_NAME.match(line):
            current_rule = _parse_rule_header(line)
            if current_rule is None:
                logger.warning("latexmk: %s: malformed rule header: %s", path, line)
            else:
                rules[current_rule.name] = current_rule
                state = _SOURCES
            continue
        if current_rule is None:
            continue
        state = _process_body_line(line, current_rule, state)

    return rules


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_fdb(path: Path) -> dict[str, FdbRule]:
    """Parse .fdb_latexmk; return empty dict if file missing or corrupt.

    Mirrors ``rdb_read`` in ``latexmk.pl`` (lines 8009-8233).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        logger.warning("latexmk: cannot read %s: %s", path, exc)
        return {}

    lines = text.splitlines()
    if not lines or not _check_version(lines[0], path):
        return {}
    return _read_fdb_body(lines[1:], path)


def write_fdb(path: Path, rules: Mapping[str, FdbRule]) -> None:
    """Write .fdb_latexmk in Perl-compatible format.

    Mirrors ``rdb_write`` in ``latexmk.pl`` (lines 8305-8354).
    """
    parts: list[str] = [f"{_HEADER}\n"]
    for rule in rules.values():
        parts.append(
            f'["{rule.name}"] {rule.run_time!r}'
            f' "{rule.source}" "{rule.dest}" "{rule.base}"'
            f" {rule.check_time!r} {rule.last_result}\n"
        )
        parts.extend(
            f'  "{entry.path}" {entry.mtime!r} {entry.size} {entry.md5} "{entry.from_rule}"\n'
            for entry in rule.files
        )
        parts.append("  (generated)\n")
        parts.extend(f'  "{p}"\n' for p in rule.generated)
        parts.append("  (rewritten before read)\n")
        parts.extend(f'  "{p}"\n' for p in rule.rewritten_before_read)
    path.write_text("".join(parts), encoding="utf-8")
