"""Integration tests for makeglossaries secondary-rule handling.

Requires pdflatex + makeglossaries (Perl script) on PATH (--runintegration).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from latexmk_py.config import Config, DirectoriesConfig
from latexmk_py.rdb import RuleDatabase

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "glossaries"


@pytest.mark.integration
def test_glossaries_basic(tmp_path: Path) -> None:
    """pdflatex + makeglossaries produces a PDF and a .gls file."""
    shutil.copy(_FIXTURES / "main.tex", tmp_path / "main.tex")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    rdb = RuleDatabase(tmp_path / "main.tex", cfg)
    assert rdb.build() == 0
    assert (tmp_path / "main.pdf").exists()
    assert (tmp_path / "main.gls").exists()


@pytest.mark.integration
def test_glossaries_secondary_rule_appears(tmp_path: Path) -> None:
    """After build(), a makeglossaries_main rule is present in the rule list."""
    shutil.copy(_FIXTURES / "main.tex", tmp_path / "main.tex")
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    rdb = RuleDatabase(tmp_path / "main.tex", cfg)
    rdb.build()
    assert any(r.name == "makeglossaries_main" for r in rdb.rules)
