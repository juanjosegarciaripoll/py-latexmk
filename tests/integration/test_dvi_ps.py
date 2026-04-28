"""Integration tests for DVI and PostScript build modes (T14).

Requires latex + dvips on PATH (--runintegration).
ps2pdf (Ghostscript) is needed for pdf_mode=2; skipped if absent.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from latexmk_py.config import BuildConfig, Config, DirectoriesConfig
from latexmk_py.rdb import RuleDatabase

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "simple"


def _has_tool(name: str) -> bool:
    return shutil.which(name) is not None


# ---------------------------------------------------------------------------
# dvi_mode=1 — latex → DVI
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_dvi_mode_produces_dvi(tmp_path: Path) -> None:
    """latex run produces hello.dvi."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=0, dvi_mode=1),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    rdb = RuleDatabase(tmp_path / "hello.tex", cfg)
    assert rdb.build() == 0
    assert (tmp_path / "hello.dvi").exists()


@pytest.mark.integration
def test_dvi_mode_no_pdf(tmp_path: Path) -> None:
    """DVI mode does not produce a PDF."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=0, dvi_mode=1),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    RuleDatabase(tmp_path / "hello.tex", cfg).build()
    assert not (tmp_path / "hello.pdf").exists()


@pytest.mark.integration
def test_dvi_mode_second_run_no_op(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Second DVI build with unchanged source skips latex."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=0, dvi_mode=1),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    RuleDatabase(tmp_path / "hello.tex", cfg).build()
    capsys.readouterr()
    RuleDatabase(tmp_path / "hello.tex", cfg).build()
    assert "applying rule" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# postscript_mode=1 — latex → dvips → PS
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not _has_tool("dvips"), reason="dvips not installed")
def test_postscript_mode_produces_ps(tmp_path: Path) -> None:
    """postscript_mode=1 produces hello.ps via dvips."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=0, postscript_mode=1),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    rdb = RuleDatabase(tmp_path / "hello.tex", cfg)
    assert rdb.build() == 0
    assert (tmp_path / "hello.ps").exists()


@pytest.mark.integration
@pytest.mark.skipif(not _has_tool("dvips"), reason="dvips not installed")
def test_postscript_mode_rule_kinds(tmp_path: Path) -> None:
    """postscript_mode creates one primary (latex) and one postprocess (dvips) rule."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=0, postscript_mode=1),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    rdb = RuleDatabase(tmp_path / "hello.tex", cfg)
    rdb.build()
    kinds = {r.kind for r in rdb.rules}
    assert "primary" in kinds
    assert "postprocess" in kinds


# ---------------------------------------------------------------------------
# pdf_mode=3 — latex → dvipdf → PDF
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not _has_tool("dvipdf"), reason="dvipdf not installed")
def test_pdf_mode3_produces_pdf(tmp_path: Path) -> None:
    """pdf_mode=3 (latex+dvipdf) produces hello.pdf."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=3),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    rdb = RuleDatabase(tmp_path / "hello.tex", cfg)
    assert rdb.build() == 0
    assert (tmp_path / "hello.pdf").exists()


# ---------------------------------------------------------------------------
# Postprocess skip on second run
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not _has_tool("dvips"), reason="dvips not installed")
def test_postprocess_skip_when_source_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Second build with postscript_mode skips dvips when DVI unchanged."""
    shutil.copy(_FIXTURES / "hello.tex", tmp_path / "hello.tex")
    cfg = Config(
        build=BuildConfig(pdf_mode=0, postscript_mode=1),
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
    )
    RuleDatabase(tmp_path / "hello.tex", cfg).build()
    capsys.readouterr()
    RuleDatabase(tmp_path / "hello.tex", cfg).build()
    assert "applying rule" not in capsys.readouterr().out
