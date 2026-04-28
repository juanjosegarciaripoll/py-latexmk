"""Integration tests for Biber secondary-rule handling.

Requires pdflatex + biber on PATH (--runintegration).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from latexmk_py.config import BibtexConfig, Config, DirectoriesConfig
from latexmk_py.rdb import RuleDatabase

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "biblatex"


@pytest.mark.integration
def test_biber_basic(tmp_path: Path) -> None:
    """pdflatex + biber produces a PDF and a .bbl file."""
    shutil.copy(_FIXTURES / "main.tex", tmp_path / "main.tex")
    shutil.copy(_FIXTURES / "refs.bib", tmp_path / "refs.bib")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    rdb = RuleDatabase(tmp_path / "main.tex", cfg)
    assert rdb.build() == 0
    assert (tmp_path / "main.pdf").exists()
    assert (tmp_path / "main.bbl").exists()


@pytest.mark.integration
def test_biber_secondary_rule_appears_in_rules(tmp_path: Path) -> None:
    """After build(), a biber_main rule is present in the rule list."""
    shutil.copy(_FIXTURES / "main.tex", tmp_path / "main.tex")
    shutil.copy(_FIXTURES / "refs.bib", tmp_path / "refs.bib")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    rdb = RuleDatabase(tmp_path / "main.tex", cfg)
    rdb.build()
    assert any(r.name == "biber_main" for r in rdb.rules)


@pytest.mark.integration
def test_biber_not_run_when_use_0(tmp_path: Path) -> None:
    """bibtex.use=0 suppresses biber processing entirely."""
    shutil.copy(_FIXTURES / "main.tex", tmp_path / "main.tex")
    shutil.copy(_FIXTURES / "refs.bib", tmp_path / "refs.bib")
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        bibtex=BibtexConfig(use=0.0),
    )
    rdb = RuleDatabase(tmp_path / "main.tex", cfg)
    rdb.build()
    assert not any(r.name == "biber_main" for r in rdb.rules)
    assert not (tmp_path / "main.bbl").exists()
