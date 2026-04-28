"""Make-format dependency output for ``-M`` / ``-deps``.

Mirrors dependency-output behavior in ``latexmk.pl`` (deps generation path).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from latexmk_py.config import DepsConfig
    from latexmk_py.rules import Rule

type EscapeMode = str


def _escape(path: str, mode: EscapeMode) -> str:
    """Escape spaces in *path* according to dependency escape mode."""
    match mode:
        case "unix":
            return path.replace(" ", r"\ ")
        case "nmake":
            return path.replace(" ", "^ ")
        case _:
            return path


def _final_output(rules: Sequence[Rule]) -> Path:
    """Return final dependency target path from a populated rule set."""
    post = [r for r in rules if r.kind == "postprocess"]
    if post:
        return post[-1].dest
    primary = [r for r in rules if r.kind == "primary"]
    if primary:
        return primary[-1].dest
    return rules[-1].dest


def write_deps(
    rules: Sequence[Rule],
    cfg: DepsConfig,
    tex: Path,
) -> None:
    """Write make-format dependency list to file or stdout.

    Mirrors ``-M/-MF/-MP`` behavior from ``latexmk.pl``.
    """
    target = _final_output(rules)
    all_deps: set[Path] = set()
    for rule in rules:
        all_deps.update(rule.extra_sources)
        all_deps.add(rule.source)
    all_deps.discard(target)

    dep_strs = [_escape(str(d), cfg.escape) for d in sorted(all_deps, key=str)]
    lines = [f"{_escape(str(target), cfg.escape)}: \\"]
    lines.extend(f"    {dep} \\" for dep in dep_strs[:-1])
    if dep_strs:
        lines.append(f"    {dep_strs[-1]}")

    if cfg.phony:
        lines.append("")
        lines.extend(f"{dep}:" for dep in dep_strs)

    content = "\n".join(lines) + "\n"

    if cfg.file == "-":
        sys.stdout.write(content)
    else:
        out = Path(cfg.file)
        if not out.is_absolute():
            out = tex.parent / out
        out.write_text(content, encoding="utf-8")
