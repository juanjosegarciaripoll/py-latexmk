"""Rule dataclass, init_rules, out_of_date, compute_md5, topo_sort.

No subprocess calls in this module.
Mirrors the rule-database layer of latexmk.pl (rdb_create_rule, lines ~11320,
and rdb_initialize_rules, lines 3648-3728).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

    from latexmk_py.config import Config
    from latexmk_py.fdb import FdbRule

# pdf_mode values (mirrors latexmk.pl lines 1452-1456)
_PM_PDFLATEX = 1
_PM_PS = 2
_PM_DVIPDF = 3
_PM_LUALATEX = 4
_PM_XELATEX = 5
# dvi_mode values (mirrors latexmk.pl line 1446)
_DM_LATEX = 1
_DM_DVILUALATEX = 2

_KIND_PRIORITY: dict[str, int] = {
    "primary": 0,
    "secondary": 1,
    "cusdep": 2,
    "postprocess": 3,
}


@dataclass(slots=True)
class Rule:
    """Mutable build state for one latexmk rule.

    Mirrors an entry in the rule database of ``latexmk.pl``
    (``rdb_create_rule``, lines ~11320).
    """

    name: str
    kind: Literal["primary", "secondary", "postprocess", "cusdep"]
    command: str  # template before placeholder expansion
    source: Path
    dest: Path
    base: Path  # stem, no ext, no dir  (used for %B expansion)
    extra_sources: set[Path] = field(default_factory=set)
    extra_dests: set[Path] = field(default_factory=set)
    source_md5: dict[Path, str] = field(default_factory=dict)
    dest_md5: dict[Path, str] = field(default_factory=dict)
    run_time: float = 0.0  # 0.0 = never run
    last_result: int = 0
    last_message: str = ""
    out_of_date: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _out(stem: str, ext: str, dir_str: str) -> Path:
    """Build dir/stem.ext path; dir_str='' gives Path('stem.ext')."""
    return Path(dir_str) / f"{stem}{ext}"


def _restore_from_fdb(rules: list[Rule], fdb: dict[str, FdbRule]) -> None:
    """Restore run_time, last_result, and md5 caches from a .fdb_latexmk database."""
    for rule in rules:
        fr = fdb.get(rule.name)
        if fr is None:
            continue
        rule.run_time = fr.run_time
        rule.last_result = fr.last_result
        for entry in fr.files:
            rule.source_md5[entry.path] = entry.md5
        if rule.dest.exists():
            rule.dest_md5[rule.dest] = compute_md5(rule.dest)
        # Prior state restored: clear the flag so MD5 checks govern freshness.
        rule.out_of_date = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_md5(path: Path) -> str:
    """Compute MD5 hex digest without loading the whole file into memory.

    Uses ``hashlib.file_digest`` (Python 3.11+) with a ``BufferedReader``.
    """
    with path.open("rb") as f:
        return hashlib.file_digest(f, "md5").hexdigest()


def _make_special_mode_rules(tex: Path, cfg: Config) -> list[Rule]:
    """Build rules for postscript_mode=1 or xdv_mode=1 (no pdf_mode / dvi_mode set).

    Mirrors the postscript / xdv branches of ``rdb_initialize_rules`` in
    ``latexmk.pl`` (lines 3648-3728).
    """
    stem = tex.stem
    d = cfg.directories
    c = cfg.commands
    if cfg.build.postscript_mode:
        # latex → .dvi → dvips → .ps
        dvi = _out(stem, ".dvi", d.out_dir)
        ps_ = _out(stem, ".ps", d.out_dir)
        base = Path(stem)
        dvips_cmd = c.dvips_landscape if cfg.build.landscape else c.dvips
        return [
            Rule(name="latex", kind="primary", command=c.latex, source=tex, dest=dvi, base=base),
            Rule(
                name="dvips", kind="postprocess", command=dvips_cmd, source=dvi, dest=ps_, base=base
            ),
        ]
    if cfg.build.xdv_mode:
        # xelatex → .xdv only (no xdvipdfmx conversion to PDF)
        return [
            Rule(
                name="xelatex",
                kind="primary",
                command=c.xelatex,
                source=tex,
                dest=_out(stem, ".xdv", d.out_dir),
                base=Path(stem),
            )
        ]
    return []


def init_rules(
    tex: Path,
    cfg: Config,
    fdb: dict[str, FdbRule] | None = None,
) -> list[Rule]:
    """Build the initial rule set for one .tex source file.

    Mirrors ``rdb_initialize_rules`` in ``latexmk.pl`` (lines 3648-3728).
    Creates the primary rule and any postprocess rules.  Secondary rules
    (bibtex, makeindex) are added dynamically by rdb.py after parsing .aux.
    Restores run_time and source_md5 from fdb if available.
    """
    stem = tex.stem
    d = cfg.directories
    c = cfg.commands
    rules: list[Rule] = []

    pm = cfg.build.pdf_mode
    dm = cfg.build.dvi_mode

    if pm == _PM_PDFLATEX:
        # pdflatex → .pdf
        rules.append(
            Rule(
                name="pdflatex",
                kind="primary",
                command=c.pdflatex,
                source=tex,
                dest=_out(stem, ".pdf", d.out_dir),
                base=Path(stem),
            )
        )
    elif pm == _PM_PS:
        # latex → .dvi → dvips → .ps → ps2pdf → .pdf
        dvi = _out(stem, ".dvi", d.out_dir)
        ps_ = _out(stem, ".ps", d.out_dir)
        pdf = _out(stem, ".pdf", d.out_dir)
        base = Path(stem)
        dvips_cmd = c.dvips_landscape if cfg.build.landscape else c.dvips
        rules.extend(
            [
                Rule(
                    name="latex", kind="primary", command=c.latex, source=tex, dest=dvi, base=base
                ),
                Rule(
                    name="dvips",
                    kind="postprocess",
                    command=dvips_cmd,
                    source=dvi,
                    dest=ps_,
                    base=base,
                ),
                Rule(
                    name="ps2pdf",
                    kind="postprocess",
                    command=c.ps2pdf,
                    source=ps_,
                    dest=pdf,
                    base=base,
                ),
            ]
        )
    elif pm == _PM_DVIPDF:
        # latex (or dvilualatex) + dvipdf → .pdf
        dvi = _out(stem, ".dvi", d.out_dir)
        pdf = _out(stem, ".pdf", d.out_dir)
        base = Path(stem)
        pname: str = "dvilualatex" if dm == _DM_DVILUALATEX else "latex"
        pcmd: str = c.dvilualatex if dm == _DM_DVILUALATEX else c.latex
        rules.extend(
            [
                Rule(name=pname, kind="primary", command=pcmd, source=tex, dest=dvi, base=base),
                Rule(
                    name="dvipdf",
                    kind="postprocess",
                    command=c.dvipdf,
                    source=dvi,
                    dest=pdf,
                    base=base,
                ),
            ]
        )
    elif pm == _PM_LUALATEX:
        # lualatex → .pdf
        rules.append(
            Rule(
                name="lualatex",
                kind="primary",
                command=c.lualatex,
                source=tex,
                dest=_out(stem, ".pdf", d.out_dir),
                base=Path(stem),
            )
        )
    elif pm == _PM_XELATEX:
        # xelatex → .xdv → xdvipdfmx → .pdf
        xdv = _out(stem, ".xdv", d.aux_dir)
        pdf = _out(stem, ".pdf", d.out_dir)
        base = Path(stem)
        rules.extend(
            [
                Rule(
                    name="xelatex",
                    kind="primary",
                    command=c.xelatex,
                    source=tex,
                    dest=xdv,
                    base=base,
                ),
                Rule(
                    name="xdvipdfmx",
                    kind="postprocess",
                    command=c.xdvipdfmx,
                    source=xdv,
                    dest=pdf,
                    base=base,
                ),
            ]
        )
    elif dm == _DM_LATEX:
        # latex → .dvi only
        rules.append(
            Rule(
                name="latex",
                kind="primary",
                command=c.latex,
                source=tex,
                dest=_out(stem, ".dvi", d.out_dir),
                base=Path(stem),
            )
        )
    elif dm == _DM_DVILUALATEX:
        # dvilualatex → .dvi only
        rules.append(
            Rule(
                name="dvilualatex",
                kind="primary",
                command=c.dvilualatex,
                source=tex,
                dest=_out(stem, ".dvi", d.out_dir),
                base=Path(stem),
            )
        )
    else:
        rules.extend(_make_special_mode_rules(tex, cfg))

    if fdb:
        _restore_from_fdb(rules, fdb)

    return rules


def out_of_date(rule: Rule, *, force: bool = False) -> bool:
    """Return True if rule needs to run.

    Mirrors the out-of-date detection in ``latexmk.pl`` (~lines 9300-9340).
    Never raises; a missing or unreadable file is treated as out-of-date.
    """
    if rule.run_time == 0.0 or force:
        return True
    for src, expected in rule.source_md5.items():
        try:
            if compute_md5(src) != expected:
                return True
        except OSError:
            return True
    if not rule.dest.exists():
        return True
    for dest, expected in rule.dest_md5.items():
        try:
            if not dest.exists() or compute_md5(dest) != expected:
                return True
        except OSError:
            return True
    return False


def topo_sort(rules: Sequence[Rule]) -> list[Rule]:
    """Return rules in dependency order: primary → secondary → cusdep → postprocess.

    Mirrors the rule network ordering in ``latexmk.pl`` (``rdb_set_rule_net``,
    lines 3803+).  A simple priority sort suffices because the dependency graph
    has at most three levels for any current rule set.
    """
    return sorted(rules, key=lambda r: (_KIND_PRIORITY[r.kind], r.name))
