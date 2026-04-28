"""Cleanup logic for -c / -C / -CF modes.

Mirrors ``clean_up`` / ``clean_up_bibtex`` / ``clean_up_aux`` in
``latexmk.pl`` (lines ~5100-5350).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Literal

    from latexmk_py.config import Config
    from latexmk_py.rules import Rule

logger = logging.getLogger(__name__)

# Files removed by -c (intermediate, never the final output).
INTERMEDIATE_EXTS: frozenset[str] = frozenset(
    {
        "acn",
        "acr",
        "alg",
        "aux",
        "bbl",
        "bcf",
        "blg",
        "brf",
        "fdb_latexmk",
        "fls",
        "glg",
        "glo",
        "gls",
        "idx",
        "ilg",
        "ind",
        "ist",
        "lof",
        "log",
        "lot",
        "nav",
        "out",
        "run.xml",
        "snm",
        "synctex",
        "synctex.gz",
        "toc",
        "vrb",
        "xdy",
    }
)

# Additional files removed by -C (final output formats).
FINAL_EXTS: frozenset[str] = frozenset({"dvi", "hnt", "pdf", "ps", "xdv"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_dir(dir_str: str, tex_parent: Path) -> Path:
    """Resolve a directory string relative to the .tex parent when not absolute."""
    if not dir_str:
        return tex_parent
    p = Path(dir_str)
    return p if p.is_absolute() else tex_parent / p


def _affected_dirs(tex: Path, cfg: Config) -> list[Path]:
    """Return unique search directories for cleanup: out_dir, aux_dir, tex.parent."""
    tex_parent = tex.parent
    candidates: list[Path] = [
        _resolve_dir(d, tex_parent)
        for d in (cfg.directories.out_dir, cfg.directories.aux_dir)
        if d
    ] + [tex_parent]

    seen: set[Path] = set()
    result: list[Path] = []
    for d in candidates:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result


_MODE_FULL = 2  # -C: remove final output in addition to intermediate files


def _exts_to_remove(cfg: Config, mode: int) -> frozenset[str]:
    """Return the full set of extensions to delete for *mode*."""
    exts: frozenset[str] = INTERMEDIATE_EXTS | frozenset(cfg.cleanup.extra_extensions)
    if mode == _MODE_FULL:
        exts |= FINAL_EXTS | frozenset(cfg.cleanup.extra_full_extensions)
    return exts


def _try_remove(p: Path) -> None:
    """Delete *p*, logging the action; silently ignore missing files."""
    try:
        p.unlink()
        logger.info("latexmk: removing %s", p)
    except FileNotFoundError:
        pass


def _clean_cusdep_files(rules: Sequence[Rule]) -> None:
    """Remove destination files produced by cusdep rules."""
    for rule in rules:
        if rule.kind == "cusdep":
            _try_remove(rule.dest)
            for p in rule.extra_dests:
                _try_remove(p)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clean(
    tex: Path,
    cfg: Config,
    mode: Literal[1, 2],
    *,
    fdb_only: bool = False,
    rules: Sequence[Rule] | None = None,
) -> None:
    """Remove generated files for *tex* according to *mode*.

    *mode* ``1`` corresponds to ``-c`` (intermediate files only).
    *mode* ``2`` corresponds to ``-C`` (intermediate + final output).
    *fdb_only* ``True`` corresponds to ``-CF`` (only ``.fdb_latexmk``).

    Mirrors ``clean_up`` in ``latexmk.pl`` (lines ~5100-5350).
    """
    base = tex.stem
    search_dirs = _affected_dirs(tex, cfg)

    if fdb_only:
        for d in search_dirs:
            _try_remove(d / f"{base}.fdb_latexmk")
        return

    exts = _exts_to_remove(cfg, mode)
    for d in search_dirs:
        for ext in exts:
            _try_remove(d / f"{base}.{ext}")

    if cfg.cleanup.includes_cusdep_generated and rules:
        _clean_cusdep_files(rules)
