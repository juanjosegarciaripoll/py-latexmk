"""Tests for cleaner.py (-c / -C / -CF cleanup modes)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from latexmk_py.cleaner import FINAL_EXTS, INTERMEDIATE_EXTS, clean

if TYPE_CHECKING:
    from pathlib import Path
from latexmk_py.config import CleanupConfig, Config, DirectoriesConfig
from latexmk_py.rules import Rule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_files(d: Path, stem: str, exts: list[str]) -> list[Path]:
    """Create empty files {stem}.{ext} in *d*; return their Paths."""
    d.mkdir(parents=True, exist_ok=True)
    paths = [d / f"{stem}.{ext}" for ext in exts]
    for p in paths:
        p.write_bytes(b"content")
    return paths


def _stub_rule(tmp_path: Path, name: str, dest_name: str) -> Rule:
    dest = tmp_path / dest_name
    dest.write_bytes(b"generated")
    return Rule(
        name=name,
        kind="cusdep",
        command="cmd",
        source=tmp_path / "src.fig",
        dest=dest,
        base=tmp_path / name,
    )


# ---------------------------------------------------------------------------
# Extension sets
# ---------------------------------------------------------------------------


def test_intermediate_exts_contains_aux() -> None:
    assert "aux" in INTERMEDIATE_EXTS


def test_intermediate_exts_contains_fdb() -> None:
    assert "fdb_latexmk" in INTERMEDIATE_EXTS


def test_final_exts_contains_pdf() -> None:
    assert "pdf" in FINAL_EXTS


def test_final_exts_does_not_overlap_intermediate() -> None:
    assert INTERMEDIATE_EXTS.isdisjoint(FINAL_EXTS)


# ---------------------------------------------------------------------------
# -c mode (mode=1): remove intermediate, keep final
# ---------------------------------------------------------------------------


def test_clean_mode1_removes_aux(tmp_path: Path) -> None:
    aux = tmp_path / "doc.aux"
    aux.write_bytes(b"")
    clean(tmp_path / "doc.tex", Config(), mode=1)
    assert not aux.exists()


def test_clean_mode1_removes_log(tmp_path: Path) -> None:
    log = tmp_path / "doc.log"
    log.write_bytes(b"")
    clean(tmp_path / "doc.tex", Config(), mode=1)
    assert not log.exists()


def test_clean_mode1_removes_fdb(tmp_path: Path) -> None:
    fdb = tmp_path / "doc.fdb_latexmk"
    fdb.write_bytes(b"")
    clean(tmp_path / "doc.tex", Config(), mode=1)
    assert not fdb.exists()


def test_clean_mode1_keeps_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    clean(tmp_path / "doc.tex", Config(), mode=1)
    assert pdf.exists()


def test_clean_mode1_removes_multiple_exts(tmp_path: Path) -> None:
    files = _make_files(tmp_path, "doc", ["aux", "log", "toc", "bbl"])
    clean(tmp_path / "doc.tex", Config(), mode=1)
    for p in files:
        assert not p.exists(), f"{p.name} should have been removed"


# ---------------------------------------------------------------------------
# -C mode (mode=2): remove intermediate + final
# ---------------------------------------------------------------------------


def test_clean_mode2_removes_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    clean(tmp_path / "doc.tex", Config(), mode=2)
    assert not pdf.exists()


def test_clean_mode2_removes_dvi(tmp_path: Path) -> None:
    dvi = tmp_path / "doc.dvi"
    dvi.write_bytes(b"dvi")
    clean(tmp_path / "doc.tex", Config(), mode=2)
    assert not dvi.exists()


def test_clean_mode2_removes_intermediate_and_final(tmp_path: Path) -> None:
    files = _make_files(tmp_path, "doc", ["aux", "log", "pdf", "dvi"])
    clean(tmp_path / "doc.tex", Config(), mode=2)
    for p in files:
        assert not p.exists()


# ---------------------------------------------------------------------------
# -CF mode (fdb_only)
# ---------------------------------------------------------------------------


def test_clean_fdb_only_removes_only_fdb(tmp_path: Path) -> None:
    fdb = tmp_path / "doc.fdb_latexmk"
    aux = tmp_path / "doc.aux"
    pdf = tmp_path / "doc.pdf"
    fdb.write_bytes(b"")
    aux.write_bytes(b"")
    pdf.write_bytes(b"%PDF")

    clean(tmp_path / "doc.tex", Config(), mode=1, fdb_only=True)

    assert not fdb.exists()
    assert aux.exists()
    assert pdf.exists()


# ---------------------------------------------------------------------------
# Missing files — no exception
# ---------------------------------------------------------------------------


def test_clean_missing_files_no_error(tmp_path: Path) -> None:
    clean(tmp_path / "doc.tex", Config(), mode=2)  # nothing exists; must not raise


# ---------------------------------------------------------------------------
# Extra extensions
# ---------------------------------------------------------------------------


def test_clean_extra_extensions_mode1(tmp_path: Path) -> None:
    p = tmp_path / "doc.myext"
    p.write_bytes(b"")
    cfg = Config(cleanup=CleanupConfig(extra_extensions=("myext",)))
    clean(tmp_path / "doc.tex", cfg, mode=1)
    assert not p.exists()


def test_clean_extra_full_extensions_mode2_only(tmp_path: Path) -> None:
    p = tmp_path / "doc.myout"
    p.write_bytes(b"")
    cfg = Config(cleanup=CleanupConfig(extra_full_extensions=("myout",)))
    # mode=1 should NOT remove it
    clean(tmp_path / "doc.tex", cfg, mode=1)
    assert p.exists()
    # mode=2 should remove it
    clean(tmp_path / "doc.tex", cfg, mode=2)
    assert not p.exists()


# ---------------------------------------------------------------------------
# cusdep-generated files
# ---------------------------------------------------------------------------


def test_clean_cusdep_files_when_enabled(tmp_path: Path) -> None:
    rule = _stub_rule(tmp_path, "fig2eps", "figname.eps")
    cfg = Config(cleanup=CleanupConfig(includes_cusdep_generated=True))
    clean(tmp_path / "doc.tex", cfg, mode=1, rules=[rule])
    assert not rule.dest.exists()


def test_clean_cusdep_files_skipped_when_disabled(tmp_path: Path) -> None:
    rule = _stub_rule(tmp_path, "fig2eps", "figname.eps")
    cfg = Config(cleanup=CleanupConfig(includes_cusdep_generated=False))
    clean(tmp_path / "doc.tex", cfg, mode=1, rules=[rule])
    assert rule.dest.exists()


def test_clean_cusdep_extra_dests_removed(tmp_path: Path) -> None:
    extra = tmp_path / "figname.png"
    extra.write_bytes(b"extra")
    rule = _stub_rule(tmp_path, "fig2eps", "figname.eps")
    rule.extra_dests.add(extra)
    cfg = Config(cleanup=CleanupConfig(includes_cusdep_generated=True))
    clean(tmp_path / "doc.tex", cfg, mode=1, rules=[rule])
    assert not extra.exists()


def test_clean_non_cusdep_rules_not_removed(tmp_path: Path) -> None:
    dest = tmp_path / "doc.pdf"
    dest.write_bytes(b"%PDF")
    rule = Rule(
        name="pdflatex",
        kind="primary",
        command="pdflatex",
        source=tmp_path / "doc.tex",
        dest=dest,
        base=tmp_path / "doc",
    )
    cfg = Config(cleanup=CleanupConfig(includes_cusdep_generated=True))
    clean(tmp_path / "doc.tex", cfg, mode=1, rules=[rule])
    assert dest.exists()  # primary rule dest untouched by cusdep cleanup


# ---------------------------------------------------------------------------
# Directory search scope
# ---------------------------------------------------------------------------


def test_clean_searches_out_dir(tmp_path: Path) -> None:
    out = tmp_path / "build"
    out.mkdir()
    aux_file = out / "doc.aux"
    aux_file.write_bytes(b"")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(out)))
    clean(tmp_path / "doc.tex", cfg, mode=1)
    assert not aux_file.exists()


def test_clean_searches_aux_dir(tmp_path: Path) -> None:
    out = tmp_path / "build"
    aux_dir = tmp_path / "aux"
    out.mkdir()
    aux_dir.mkdir()
    aux_file = aux_dir / "doc.aux"
    aux_file.write_bytes(b"")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(out), aux_dir=str(aux_dir)))
    clean(tmp_path / "doc.tex", cfg, mode=1)
    assert not aux_file.exists()


def test_clean_tex_parent_always_searched(tmp_path: Path) -> None:
    aux = tmp_path / "doc.aux"
    aux.write_bytes(b"")
    out = tmp_path / "build"
    cfg = Config(directories=DirectoriesConfig(out_dir=str(out)))
    clean(tmp_path / "doc.tex", cfg, mode=1)
    assert not aux.exists()


def test_clean_deduplicates_dirs(tmp_path: Path) -> None:
    """When out_dir == tex.parent, each file is attempted only once (no double-remove error)."""
    aux = tmp_path / "doc.aux"
    aux.write_bytes(b"")
    # out_dir points to the same location as tex.parent
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    clean(tmp_path / "doc.tex", cfg, mode=1)  # must not raise
    assert not aux.exists()


def test_clean_fdb_only_searches_out_dir(tmp_path: Path) -> None:
    out = tmp_path / "build"
    out.mkdir()
    fdb = out / "doc.fdb_latexmk"
    fdb.write_bytes(b"")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(out)))
    clean(tmp_path / "doc.tex", cfg, mode=1, fdb_only=True)
    assert not fdb.exists()
