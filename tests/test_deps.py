"""Tests for deps.py (make-format dependency output)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
from latexmk_py.config import DepsConfig
from latexmk_py.deps import write_deps
from latexmk_py.rules import Rule


def _rule(
    *,
    name: str,
    kind: Literal["primary", "secondary", "postprocess", "cusdep"],
    source: Path,
    dest: Path,
    extra_sources: set[Path] | None = None,
) -> Rule:
    return Rule(
        name=name,
        kind=kind,
        command="cmd",
        source=source,
        dest=dest,
        base=Path("doc"),
        extra_sources=extra_sources or set(),
    )


def test_write_deps_stdout_basic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tex = tmp_path / "doc.tex"
    rules = [
        _rule(name="pdflatex", kind="primary", source=tex, dest=tmp_path / "doc.pdf"),
        _rule(
            name="bibtex_doc",
            kind="secondary",
            source=tmp_path / "doc.aux",
            dest=tmp_path / "doc.bbl",
            extra_sources={tmp_path / "refs.bib"},
        ),
    ]

    write_deps(rules, DepsConfig(enabled=True, file="-"), tex)
    out = capsys.readouterr().out
    assert f"{tmp_path / 'doc.pdf'}: \\" in out
    assert str(tex) in out
    assert str(tmp_path / "doc.aux") in out
    assert str(tmp_path / "refs.bib") in out
    assert str(tmp_path / "doc.pdf") not in out.split(":", 1)[1]


def test_write_deps_uses_postprocess_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tex = tmp_path / "doc.tex"
    rules = [
        _rule(name="latex", kind="primary", source=tex, dest=tmp_path / "doc.dvi"),
        _rule(name="dvipdf", kind="postprocess", source=tmp_path / "doc.dvi", dest=tmp_path / "doc.pdf"),
    ]
    write_deps(rules, DepsConfig(enabled=True, file="-"), tex)
    out = capsys.readouterr().out
    assert out.startswith(f"{tmp_path / 'doc.pdf'}: \\")


def test_write_deps_escape_modes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tex = tmp_path / "doc.tex"
    spaced = tmp_path / "file name.tex"
    rules = [_rule(name="pdflatex", kind="primary", source=spaced, dest=tmp_path / "doc.pdf")]

    write_deps(rules, DepsConfig(enabled=True, file="-", escape="none"), tex)
    out_none = capsys.readouterr().out
    assert "file name.tex" in out_none

    write_deps(rules, DepsConfig(enabled=True, file="-", escape="unix"), tex)
    out_unix = capsys.readouterr().out
    assert r"file\ name.tex" in out_unix

    write_deps(rules, DepsConfig(enabled=True, file="-", escape="nmake"), tex)
    out_nmake = capsys.readouterr().out
    assert "file^ name.tex" in out_nmake


def test_write_deps_phony_targets(tmp_path: Path) -> None:
    tex = tmp_path / "doc.tex"
    dep_file = tmp_path / "deps.d"
    rules = [
        _rule(name="pdflatex", kind="primary", source=tex, dest=tmp_path / "doc.pdf"),
        _rule(name="bibtex_doc", kind="secondary", source=tmp_path / "doc.aux", dest=tmp_path / "doc.bbl"),
    ]

    write_deps(rules, DepsConfig(enabled=True, file=str(dep_file), phony=True), tex)
    content = dep_file.read_text(encoding="utf-8")
    assert f"{tex}:" in content
    assert f"{tmp_path / 'doc.aux'}:" in content


def test_write_deps_writes_relative_mf_in_tex_dir(tmp_path: Path) -> None:
    tex_dir = tmp_path / "src"
    tex_dir.mkdir()
    tex = tex_dir / "doc.tex"
    rules = [_rule(name="pdflatex", kind="primary", source=tex, dest=tex_dir / "doc.pdf")]

    write_deps(rules, DepsConfig(enabled=True, file="deps.d"), tex)
    assert (tex_dir / "deps.d").exists()
