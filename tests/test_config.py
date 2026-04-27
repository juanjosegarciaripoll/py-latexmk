"""Tests for src/latexmk_py/config.py (T02)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from latexmk_py.config import (
    BuildConfig,
    CleanupConfig,
    Config,
    CustomDep,
    load_config,
)
from latexmk_py.errors import ConfigError


def test_defaults() -> None:
    cfg = Config()
    assert cfg.build.pdf_mode == 1
    assert cfg.build.recorder is True
    assert cfg.build.default_files == ("*.tex",)
    assert cfg.build.latex_extra_options == ()
    assert cfg.commands.pdflatex == "pdflatex -interaction=nonstopmode %O %S"
    assert cfg.bibtex.use == 1.0
    assert cfg.preview.view == "default"
    assert cfg.custom_deps == ()
    assert cfg.force is False
    assert cfg.norc is False


def test_norc_returns_defaults() -> None:
    cfg, loaded = load_config(norc=True)
    assert loaded == []
    assert cfg.build == BuildConfig()
    assert cfg.cleanup == CleanupConfig()


def test_toml_round_trip(tmp_path: Path) -> None:
    toml = """\
[build]
pdf_mode = 2
latex_extra_options = ["-shell-escape"]

[commands]
pdflatex = "pdflatex -interaction=nonstopmode -synctex=1 %O %S"

[bibtex]
use = 1.5
"""
    p = tmp_path / "rc.toml"
    p.write_text(toml, encoding="utf-8")
    cfg, loaded = load_config(norc=True, extra_rc_files=[str(p)])
    assert cfg.build.pdf_mode == 2
    assert cfg.build.latex_extra_options == ("-shell-escape",)
    assert cfg.commands.pdflatex == "pdflatex -interaction=nonstopmode -synctex=1 %O %S"
    assert cfg.bibtex.use == 1.5
    assert str(p) in loaded


def test_unknown_section_key_raises(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text("[build]\nbad_key = 42\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_unknown_top_level_section_raises(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text("[phantom]\nfoo = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown top-level"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_invalid_pdf_mode_raises(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text("[build]\npdf_mode = 99\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="pdf_mode"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_invalid_bibtex_use_raises(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text("[bibtex]\nuse = 3.0\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=r"bibtex\.use"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_invalid_deps_escape_raises(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text('[deps]\nescape = "bad"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match=r"deps\.escape"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_invalid_preview_view_raises(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text('[preview]\nview = "bad"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match=r"preview\.view"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_merge_order_later_wins(tmp_path: Path) -> None:
    p1 = tmp_path / "first.toml"
    p2 = tmp_path / "second.toml"
    p1.write_text("[build]\npdf_mode = 2\nmax_runs = 5\n", encoding="utf-8")
    p2.write_text("[build]\npdf_mode = 4\n", encoding="utf-8")
    cfg, _ = load_config(norc=True, extra_rc_files=[str(p1), str(p2)])
    assert cfg.build.pdf_mode == 4  # second file wins
    assert cfg.build.max_runs == 5  # only in first file


def test_custom_dependency_parsed(tmp_path: Path) -> None:
    toml = """\
[[custom_dependency]]
from = "fig"
to = "eps"
must = true
command = "fig2dev -Leps %S %D"

[[custom_dependency]]
from = "glo"
to = "gls"
command = "makeglossaries %B"
"""
    p = tmp_path / "rc.toml"
    p.write_text(toml, encoding="utf-8")
    cfg, _ = load_config(norc=True, extra_rc_files=[str(p)])
    assert len(cfg.custom_deps) == 2
    assert cfg.custom_deps[0] == CustomDep(
        from_ext="fig", to_ext="eps", must=True, command="fig2dev -Leps %S %D"
    )
    assert cfg.custom_deps[1] == CustomDep(
        from_ext="glo", to_ext="gls", must=False, command="makeglossaries %B"
    )


def test_custom_dependency_accumulates_across_files(tmp_path: Path) -> None:
    p1 = tmp_path / "first.toml"
    p2 = tmp_path / "second.toml"
    p1.write_text(
        '[[custom_dependency]]\nfrom = "fig"\nto = "eps"\ncommand = "fig2dev %S %D"\n',
        encoding="utf-8",
    )
    p2.write_text(
        '[[custom_dependency]]\nfrom = "svg"\nto = "pdf"\ncommand = "inkscape %S %D"\n',
        encoding="utf-8",
    )
    cfg, _ = load_config(norc=True, extra_rc_files=[str(p1), str(p2)])
    assert len(cfg.custom_deps) == 2
    assert cfg.custom_deps[0].from_ext == "fig"
    assert cfg.custom_deps[1].from_ext == "svg"


def test_custom_dependency_unknown_key_raises(tmp_path: Path) -> None:
    toml = '[[custom_dependency]]\nfrom = "fig"\nto = "eps"\ncommand = "x"\nbad = 1\n'
    p = tmp_path / "rc.toml"
    p.write_text(toml, encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(norc=True, extra_rc_files=[str(p)])


def test_bibtex_use_int_accepted(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text("[bibtex]\nuse = 2\n", encoding="utf-8")
    cfg, _ = load_config(norc=True, extra_rc_files=[str(p)])
    assert cfg.bibtex.use == 2.0


def test_extra_rc_files_reflected_in_config(tmp_path: Path) -> None:
    p = tmp_path / "rc.toml"
    p.write_text("[build]\npdf_mode = 3\n", encoding="utf-8")
    cfg, loaded = load_config(norc=True, extra_rc_files=[str(p)])
    assert cfg.extra_rc_files == (str(p),)
    assert cfg.norc is True
    assert str(p) in loaded
