"""Tests for printer.py - print support (-p, -print)."""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from latexmk_py.config import Config, load_config
from latexmk_py.printer import print_output, resolve_print_cmd_and_file, resolve_print_type

if TYPE_CHECKING:
    import pytest


def _cfg(**output_kwargs: object) -> Config:
    base = Config()
    return replace(base, output=replace(base.output, **output_kwargs))  # type: ignore[arg-type]


# ── _resolve_type ─────────────────────────────────────────────────────────────


class TestResolveType:
    def test_explicit_pdf(self) -> None:
        assert resolve_print_type(_cfg(print_type="pdf")) == "pdf"

    def test_explicit_ps(self) -> None:
        assert resolve_print_type(_cfg(print_type="ps")) == "ps"

    def test_explicit_dvi(self) -> None:
        assert resolve_print_type(_cfg(print_type="dvi")) == "dvi"

    def test_explicit_none(self) -> None:
        assert resolve_print_type(_cfg(print_type="none")) == "none"

    def test_auto_prefers_ps(self) -> None:
        cfg = replace(
            Config(),
            build=replace(Config().build, postscript_mode=1, pdf_mode=1),
        )
        assert resolve_print_type(cfg) == "ps"

    def test_auto_falls_back_to_pdf(self) -> None:
        cfg = replace(Config(), build=replace(Config().build, postscript_mode=0, pdf_mode=1))
        assert resolve_print_type(cfg) == "pdf"

    def test_auto_falls_back_to_dvi(self) -> None:
        cfg = replace(
            Config(),
            build=replace(Config().build, postscript_mode=0, pdf_mode=0, dvi_mode=1),
        )
        assert resolve_print_type(cfg) == "dvi"

    def test_auto_no_mode_is_none(self) -> None:
        cfg = replace(
            Config(),
            build=replace(Config().build, postscript_mode=0, pdf_mode=0, dvi_mode=0),
        )
        assert resolve_print_type(cfg) == "none"


# ── _resolve_cmd_and_file ─────────────────────────────────────────────────────


class TestResolveCmdAndFile:
    def test_pdf(self) -> None:
        cfg = replace(
            Config(),
            commands=replace(Config().commands, print_pdf="lpr %O %S"),
        )
        cmd, path = resolve_print_cmd_and_file(Path("doc.tex"), cfg, "pdf")
        assert cmd == "lpr %O %S"
        assert path == Path("doc.pdf")

    def test_ps(self) -> None:
        cfg = replace(
            Config(),
            commands=replace(Config().commands, print_ps="lpr %S"),
        )
        cmd, path = resolve_print_cmd_and_file(Path("doc.tex"), cfg, "ps")
        assert cmd == "lpr %S"
        assert path == Path("doc.ps")

    def test_dvi(self) -> None:
        cfg = replace(
            Config(),
            commands=replace(Config().commands, print_dvi="dvips | lpr"),
        )
        cmd, path = resolve_print_cmd_and_file(Path("doc.tex"), cfg, "dvi")
        assert cmd == "dvips | lpr"
        assert path == Path("doc.dvi")

    def test_unknown_returns_empty(self) -> None:
        cmd, _path = resolve_print_cmd_and_file(Path("doc.tex"), Config(), "bogus")
        assert cmd == ""


# ── print_output ──────────────────────────────────────────────────────────────


class TestPrintOutput:
    def test_empty_cmd_warns_and_returns_0(self, caplog: pytest.LogCaptureFixture) -> None:
        cfg = replace(
            Config(),
            output=replace(Config().output, print_type="pdf"),
            commands=replace(Config().commands, print_pdf=""),
        )
        with caplog.at_level(logging.WARNING, logger="latexmk_py.printer"):
            rc = print_output(Path("doc.tex"), cfg)
        assert rc == 0
        assert "not configured" in caplog.text

    def test_none_prefix_warns_and_returns_0(self, caplog: pytest.LogCaptureFixture) -> None:
        cfg = replace(
            Config(),
            output=replace(Config().output, print_type="pdf"),
            commands=replace(Config().commands, print_pdf="NONE"),
        )
        with caplog.at_level(logging.WARNING, logger="latexmk_py.printer"):
            rc = print_output(Path("doc.tex"), cfg)
        assert rc == 0
        assert "not configured" in caplog.text

    def test_print_type_none_skips(self, caplog: pytest.LogCaptureFixture) -> None:
        cfg = replace(Config(), output=replace(Config().output, print_type="none"))
        with caplog.at_level(logging.WARNING, logger="latexmk_py.printer"):
            rc = print_output(Path("doc.tex"), cfg)
        assert rc == 0
        assert caplog.text == ""


# ── TOML loading ──────────────────────────────────────────────────────────────


def test_output_print_type_default() -> None:
    assert Config().output.print_type == "auto"


def test_output_print_type_from_toml(tmp_path: Path) -> None:
    toml = tmp_path / "latexmk.toml"
    toml.write_text('[output]\nprint_type = "pdf"\n', encoding="utf-8")

    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        cfg, _ = load_config()
    finally:
        os.chdir(old)

    assert cfg.output.print_type == "pdf"
