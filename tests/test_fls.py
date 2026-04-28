from __future__ import annotations

from pathlib import Path

import pytest

from latexmk_py.parsers.fls import FlsResult, parse_fls

FIXTURES = Path(__file__).parent / "fixtures" / "logs"


def test_parse_fls_pwd() -> None:
    result = parse_fls(FIXTURES / "simple.fls")
    assert result.pwd == "/home/user/project"  # noqa: S105


def test_parse_fls_inputs_stripped_of_pwd() -> None:
    result = parse_fls(FIXTURES / "simple.fls")
    names = {p.as_posix() for p in result.inputs}
    assert "main.tex" in names
    assert "chapter1.tex" in names


def test_parse_fls_inputs_absolute_outside_pwd() -> None:
    result = parse_fls(FIXTURES / "simple.fls")
    names = {p.as_posix() for p in result.inputs}
    assert any("article.cls" in n for n in names)


def test_parse_fls_outputs_stripped_of_pwd() -> None:
    result = parse_fls(FIXTURES / "simple.fls")
    names = {p.as_posix() for p in result.outputs}
    assert "main.aux" in names
    assert "main.pdf" in names


def test_parse_fls_missing_file_returns_empty() -> None:
    result = parse_fls(FIXTURES / "nonexistent.fls")
    assert result == FlsResult(pwd="", inputs=frozenset(), outputs=frozenset())


def test_parse_fls_backslash_paths(tmp_path: Path) -> None:
    fls = tmp_path / "test.fls"
    fls.write_text("PWD C:/project\nINPUT C:\\project\\main.tex\nOUTPUT C:\\project\\main.pdf\n")
    result = parse_fls(fls)
    assert result.pwd == "C:/project"  # noqa: S105
    assert Path("main.tex") in result.inputs
    assert Path("main.pdf") in result.outputs


def test_parse_fls_no_pwd(tmp_path: Path) -> None:
    fls = tmp_path / "no_pwd.fls"
    fls.write_text("INPUT main.tex\nOUTPUT main.pdf\n")
    result = parse_fls(fls)
    assert result.pwd == ""
    assert Path("main.tex") in result.inputs


@pytest.mark.parametrize("line", ["", "   ", "# comment"])
def test_parse_fls_blank_and_comment_lines(tmp_path: Path, line: str) -> None:
    fls = tmp_path / "sparse.fls"
    fls.write_text(f"{line}\nINPUT main.tex\n")
    result = parse_fls(fls)
    assert Path("main.tex") in result.inputs
