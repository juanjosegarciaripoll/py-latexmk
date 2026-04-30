from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import latexmk_py.parsers.log as log_mod
from latexmk_py.parsers.log import LogResult, parse_log, unwrap_log_lines

if TYPE_CHECKING:
    import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "logs"


def test_parse_log_rerun_detected() -> None:
    result = parse_log(FIXTURES / "simple.log")
    assert result.rerun_needed is True


def test_parse_log_missing_files() -> None:
    result = parse_log(FIXTURES / "simple.log")
    assert "main.aux" in result.missing_files
    assert "main.bbl" in result.missing_files


def test_parse_log_reference_warning() -> None:
    result = parse_log(FIXTURES / "simple.log")
    assert result.bad_references == 1
    assert any("sec:missing" in w for w in result.warnings)


def test_parse_log_citation_warnings() -> None:
    result = parse_log(FIXTURES / "simple.log")
    assert result.bad_citations == 2  # LaTeX Warning + natbib Warning


def test_parse_log_multiply_defined_label_in_warnings() -> None:
    result = parse_log(FIXTURES / "simple.log")
    assert any("multiply defined" in w for w in result.warnings)


def test_parse_log_missing_file_returns_empty() -> None:
    result = parse_log(FIXTURES / "nonexistent.log")
    assert result == LogResult(
        rerun_needed=False,
        missing_files=frozenset(),
        warnings=(),
        errors=(),
        bad_references=0,
        bad_citations=0,
    )


def test_parse_log_error_lines(tmp_path: Path) -> None:
    log = tmp_path / "error.log"
    log.write_text(
        "This is pdfTeX\n"
        "! Undefined control sequence.\n"
        "l.5 \\badcmd\n"
        "./main.tex:10: Missing $ inserted.\n"
    )
    result = parse_log(log)
    assert any(line.startswith("!") for line in result.errors)
    assert any("main.tex:10:" in line for line in result.errors)


def testunwrap_log_lines_joins_at_wrap_boundary() -> None:
    wrap = log_mod.LOG_WRAP  # pyright: ignore[reportPrivateUsage]
    first = "a" * wrap
    second = "continuation"
    result = unwrap_log_lines([first, second, "standalone"])
    assert result == [first + second, "standalone"]


def testunwrap_log_lines_respects_custom_wrap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(log_mod, "LOG_WRAP", 10)
    first = "x" * 10
    second = "y"
    result = unwrap_log_lines([first, second])
    assert result == [first + second]


def test_parse_log_no_rerun(tmp_path: Path) -> None:
    log = tmp_path / "clean.log"
    log.write_text("This is pdfTeX\nOutput written on main.pdf (1 page).\n")
    result = parse_log(log)
    assert result.rerun_needed is False
    assert not result.missing_files
    assert not result.warnings


def test_parse_log_missing_file_patterns(tmp_path: Path) -> None:
    log = tmp_path / "missing.log"
    log.write_text(
        "This is pdfTeX\n"
        "No file missing.aux.\n"
        "! LaTeX Error: File `images/fig' not found.\n"
        "LaTeX Warning: File `logo.png' not found\n"
    )
    result = parse_log(log)
    assert "missing.aux" in result.missing_files
    assert "images/fig" in result.missing_files
    assert "logo.png" in result.missing_files
