"""Tests for rdb.py (RuleDatabase build loop)."""

from __future__ import annotations

import shutil
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

from latexmk_py.config import (
    BibtexConfig,
    BuildConfig,
    Config,
    CustomDep,
    DirectoriesConfig,
    OutputConfig,
)
from latexmk_py.errors import FileMissingError
from latexmk_py.parsers.bcf import BcfResult
from latexmk_py.parsers.dotaux import AuxResult
from latexmk_py.parsers.fls import FlsResult
from latexmk_py.parsers.log import LogResult
from latexmk_py.rdb import RuleDatabase
from latexmk_py.rules import init_rules
from latexmk_py.runner import RunResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HELLO_TEX = r"""\documentclass{article}
\begin{document}
Hello, world!
\end{document}
"""

_FIXTURES_SIMPLE = Path(__file__).parent / "fixtures" / "simple"

_EMPTY_FLS = FlsResult(pwd="", inputs=frozenset(), outputs=frozenset())
_NO_RERUN_LOG = LogResult(
    rerun_needed=False,
    missing_files=frozenset(),
    warnings=(),
    errors=(),
    bad_references=0,
    bad_citations=0,
)
_RERUN_LOG = LogResult(
    rerun_needed=True,
    missing_files=frozenset(),
    warnings=(),
    errors=(),
    bad_references=0,
    bad_citations=0,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tex(tmp_path: Path, content: str = _HELLO_TEX) -> Path:
    tex = tmp_path / "doc.tex"
    tex.write_text(content, encoding="utf-8")
    return tex


def _default_cfg(tmp_path: Path) -> Config:
    """Config with out_dir=tmp_path so all rule paths are absolute."""
    return Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))


@contextmanager
def _mock_build(*, exit_code: int = 0, rerun: bool = False) -> Generator[MagicMock]:
    """Patch run_command (creates dest on success), parse_fls, parse_log."""
    log_result = _RERUN_LOG if rerun else _NO_RERUN_LOG
    _exit = exit_code

    def _fake(_cmd: str, *, dest: Path, **__: object) -> RunResult:
        if _exit == 0:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"%PDF-1.4 fake")
        return RunResult(exit_code=_exit, stdout="", stderr="", elapsed=0.1)

    with (
        patch("latexmk_py.rdb.run_command", side_effect=_fake) as mock_run,
        patch("latexmk_py.rdb.parse_log", return_value=log_result),
        patch("latexmk_py.rdb.parse_fls", return_value=_EMPTY_FLS),
    ):
        yield mock_run


@contextmanager
def _mock_build_rerun_once() -> Generator[MagicMock]:
    """First parse_log returns rerun=True; second returns False."""

    def _fake(_cmd: str, *, dest: Path, **__: object) -> RunResult:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-1.4 fake")
        return RunResult(exit_code=0, stdout="", stderr="", elapsed=0.1)

    with (
        patch("latexmk_py.rdb.run_command", side_effect=_fake) as mock_run,
        patch("latexmk_py.rdb.parse_log", side_effect=[_RERUN_LOG, _NO_RERUN_LOG]),
        patch("latexmk_py.rdb.parse_fls", return_value=_EMPTY_FLS),
    ):
        yield mock_run


# ---------------------------------------------------------------------------
# _fdb_path
# ---------------------------------------------------------------------------


def test_fdb_path_no_out_dir(tmp_path: Path) -> None:
    tex = tmp_path / "doc.tex"
    rdb = RuleDatabase(tex, Config())
    assert rdb._fdb_path() == tmp_path / "doc.fdb_latexmk"  # noqa: SLF001  # type: ignore[reportPrivateUsage]


def test_fdb_path_with_out_dir(tmp_path: Path) -> None:
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    rdb = RuleDatabase(tmp_path / "doc.tex", cfg)
    assert rdb._fdb_path() == tmp_path / "doc.fdb_latexmk"  # noqa: SLF001  # type: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# _build_extra_opts
# ---------------------------------------------------------------------------


def test_recorder_flag_added_for_primary(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(build=BuildConfig(recorder=True))
    rdb = RuleDatabase(tex, cfg)
    rule = init_rules(tex, cfg)[0]
    assert "-recorder" in rdb._build_extra_opts(rule)  # noqa: SLF001  # type: ignore[reportPrivateUsage]


def test_recorder_flag_absent_when_disabled(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(build=BuildConfig(recorder=False))
    rdb = RuleDatabase(tex, cfg)
    rule = init_rules(tex, cfg)[0]
    assert "-recorder" not in rdb._build_extra_opts(rule)  # noqa: SLF001  # type: ignore[reportPrivateUsage]


def test_output_dir_in_opts_when_set(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    out = str(tmp_path / "out")
    cfg = Config(directories=DirectoriesConfig(out_dir=out))
    rdb = RuleDatabase(tex, cfg)
    rule = init_rules(tex, cfg)[0]
    opts = rdb._build_extra_opts(rule)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert any(o.startswith("-output-directory=") for o in opts)


def test_output_dir_absent_when_not_set(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config()
    rdb = RuleDatabase(tex, cfg)
    rule = init_rules(tex, cfg)[0]
    opts = rdb._build_extra_opts(rule)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(o.startswith("-output-directory=") for o in opts)


def test_extra_latex_options_forwarded(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(build=BuildConfig(latex_extra_options=("-synctex=1", "-file-line-error")))
    rdb = RuleDatabase(tex, cfg)
    rule = init_rules(tex, cfg)[0]
    opts = rdb._build_extra_opts(rule)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert "-synctex=1" in opts
    assert "-file-line-error" in opts


# ---------------------------------------------------------------------------
# build() — error cases
# ---------------------------------------------------------------------------


def test_build_raises_on_missing_tex(tmp_path: Path) -> None:
    rdb = RuleDatabase(tmp_path / "noexist.tex", Config())
    with pytest.raises(FileMissingError):
        rdb.build()


def test_build_no_rules_returns_zero(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(build=BuildConfig(pdf_mode=0, dvi_mode=0))
    assert RuleDatabase(tex, cfg).build() == 0


# ---------------------------------------------------------------------------
# build() — single-rule happy path
# ---------------------------------------------------------------------------


def test_build_runs_primary_rule(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build() as mock_run:
        assert RuleDatabase(tex, cfg).build() == 0
    assert mock_run.call_count == 1


def test_build_returns_zero_on_success(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build():
        assert RuleDatabase(tex, cfg).build() == 0


def test_build_returns_12_on_failure(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build(exit_code=1):
        assert RuleDatabase(tex, cfg).build() == 12


def test_build_force_continues_after_failure(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = replace(_default_cfg(tmp_path), force=True)
    with _mock_build(exit_code=1):
        assert RuleDatabase(tex, cfg).build() == 0


def test_build_silent_suppresses_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tex = _make_tex(tmp_path)
    cfg = replace(_default_cfg(tmp_path), output=OutputConfig(silent=True))
    with _mock_build():
        RuleDatabase(tex, cfg).build()
    assert "applying rule" not in capsys.readouterr().out


def test_build_non_silent_prints_rule_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build():
        RuleDatabase(tex, cfg).build()
    assert "applying rule" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# build() — FDB persistence
# ---------------------------------------------------------------------------


def test_build_writes_fdb(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build():
        RuleDatabase(tex, cfg).build()
    assert (tmp_path / "doc.fdb_latexmk").exists()


def test_build_writes_fdb_failure_path(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build(exit_code=1):
        RuleDatabase(tex, cfg).build()
    assert (tmp_path / "doc.fdb_latexmk").exists()


# ---------------------------------------------------------------------------
# build() — convergence
# ---------------------------------------------------------------------------


def test_build_reruns_when_log_says_rerun(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build_rerun_once() as mock_run:
        assert RuleDatabase(tex, cfg).build() == 0
    assert mock_run.call_count == 2


def test_build_warns_on_no_convergence(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    tex = _make_tex(tmp_path)
    cfg = replace(_default_cfg(tmp_path), build=BuildConfig(max_runs=2))
    with _mock_build(rerun=True), caplog.at_level("WARNING"):
        RuleDatabase(tex, cfg).build()
    assert "did not converge" in caplog.text


def test_build_no_stale_after_first_run_with_no_rerun(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    with _mock_build() as mock_run:
        RuleDatabase(tex, cfg).build()
    assert mock_run.call_count == 1


# ---------------------------------------------------------------------------
# Integration tests (require pdflatex/TeX install)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_integration_basic_compile(tmp_path: Path) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    rdb = RuleDatabase(tex, cfg)
    assert rdb.build() == 0
    assert (tmp_path / "hello.pdf").exists()


@pytest.mark.integration
def test_integration_fdb_written(tmp_path: Path) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    RuleDatabase(tex, cfg).build()
    assert (tmp_path / "hello.fdb_latexmk").exists()


@pytest.mark.integration
def test_integration_second_run_no_op(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    RuleDatabase(tex, cfg).build()
    capsys.readouterr()  # clear first-build output
    RuleDatabase(tex, cfg).build()
    assert "applying rule" not in capsys.readouterr().out


@pytest.mark.integration
def test_integration_touch_reruns(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    RuleDatabase(tex, cfg).build()
    # Modify source (different content → different MD5)
    tex.write_text(_HELLO_TEX + "\n% touched\n", encoding="utf-8")
    capsys.readouterr()
    RuleDatabase(tex, cfg).build()
    assert "applying rule 'pdflatex'" in capsys.readouterr().out


@pytest.mark.integration
def test_integration_force_reruns(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)))
    RuleDatabase(tex, cfg).build()
    cfg_force = replace(cfg, force=True)
    capsys.readouterr()
    RuleDatabase(tex, cfg_force).build()
    assert "applying rule 'pdflatex'" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Secondary rule detection — unit tests
# ---------------------------------------------------------------------------


def _rdb_with_primary(tmp_path: Path) -> RuleDatabase:
    """RuleDatabase pre-loaded with one primary pdflatex rule."""
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    rdb = RuleDatabase(tex, cfg)
    rules = init_rules(tex, cfg)
    rdb.rules = rules
    rdb._rule_map = {r.name: r for r in rules}  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    return rdb


def test_bibtex_rule_added_when_bib_exists(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    (tmp_path / "refs.bib").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert any(r.name == "bibtex_doc" for r in rdb.rules)


def test_bibtex_rule_not_added_when_use_0(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        bibtex=BibtexConfig(use=0.0),
    )
    rdb = RuleDatabase(tex, cfg)
    rdb.rules = init_rules(tex, cfg)
    rdb._rule_map = {r.name: r for r in rdb.rules}  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    primary = rdb.rules[0]
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    (tmp_path / "refs.bib").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(r.name == "bibtex_doc" for r in rdb.rules)


def test_bibtex_rule_not_added_when_bib_missing(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    # refs.bib intentionally absent
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(r.name == "bibtex_doc" for r in rdb.rules)


def test_bibtex_rule_added_for_use_2_without_bib(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        bibtex=BibtexConfig(use=2.0),
    )
    rdb = RuleDatabase(tex, cfg)
    rdb.rules = init_rules(tex, cfg)
    rdb._rule_map = {r.name: r for r in rdb.rules}  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    primary = rdb.rules[0]
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert any(r.name == "bibtex_doc" for r in rdb.rules)


def test_biber_rule_added_when_bcf_nonempty(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.bcf").write_bytes(b"<xml/>")
    with patch("latexmk_py.rdb.parse_bcf", return_value=BcfResult(data_sources=frozenset())):
        rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert any(r.name == "biber_doc" for r in rdb.rules)


def test_biber_not_added_when_bcf_empty(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.bcf").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(r.name == "biber_doc" for r in rdb.rules)


def test_biber_takes_priority_over_bibtex(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.bcf").write_bytes(b"<xml/>")
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    (tmp_path / "refs.bib").write_bytes(b"")
    with patch("latexmk_py.rdb.parse_bcf", return_value=BcfResult(data_sources=frozenset())):
        rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    names = [r.name for r in rdb.rules]
    assert "biber_doc" in names
    assert "bibtex_doc" not in names


def test_bibtex_rule_not_added_twice(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    (tmp_path / "refs.bib").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert sum(1 for r in rdb.rules if r.name == "bibtex_doc") == 1


def test_rule_cwd_secondary_fudge(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    rdb = RuleDatabase(tex, cfg)
    rules = init_rules(tex, cfg)
    secondary = replace(rules[0], kind="secondary")
    assert rdb._rule_cwd(secondary) == tex.parent  # noqa: SLF001  # type: ignore[reportPrivateUsage]


def test_rule_cwd_secondary_no_fudge(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        bibtex=BibtexConfig(fudge=False),
    )
    rdb = RuleDatabase(tex, cfg)
    rules = init_rules(tex, cfg)
    secondary = replace(rules[0], kind="secondary")
    assert rdb._rule_cwd(secondary) is None  # noqa: SLF001  # type: ignore[reportPrivateUsage]


def test_latex_extra_options_not_forwarded_to_secondary(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        build=BuildConfig(latex_extra_options=("-synctex=1",)),
    )
    rdb = RuleDatabase(tex, cfg)
    rules = init_rules(tex, cfg)
    secondary = replace(rules[0], kind="secondary")
    opts = rdb._build_extra_opts(secondary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert "-synctex=1" not in opts


def test_mock_build_with_bibtex_secondary(tmp_path: Path) -> None:
    """Full build loop adds bibtex rule and both primary+secondary run."""
    tex = _make_tex(tmp_path)
    cfg = _default_cfg(tmp_path)
    bib = tmp_path / "refs.bib"
    bib.write_bytes(b"")
    bbl = tmp_path / "doc.bbl"

    aux_result = AuxResult(
        bib_files=frozenset(["refs.bib"]),
        bst_files=frozenset(),
        aux_inputs=frozenset(),
    )

    run_calls: list[str] = []

    def _fake(cmd: str, *, dest: Path, **__: object) -> RunResult:
        run_calls.append(cmd)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-1.4 fake")
        if "bibtex" in cmd:
            bbl.write_bytes(b"\\bibitem{ref1}")
        return RunResult(exit_code=0, stdout="", stderr="", elapsed=0.1)

    with (
        patch("latexmk_py.rdb.run_command", side_effect=_fake),
        patch("latexmk_py.rdb.parse_log", return_value=_NO_RERUN_LOG),
        patch("latexmk_py.rdb.parse_fls", return_value=_EMPTY_FLS),
        patch("latexmk_py.rdb.parse_aux", return_value=aux_result),
    ):
        result = RuleDatabase(tex, cfg).build()

    assert result == 0
    assert any("bibtex" in c for c in run_calls)


# ---------------------------------------------------------------------------
# makeindex and makeglossaries detection — unit tests
# ---------------------------------------------------------------------------


def test_makeindex_rule_added_when_idx_exists(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.idx").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert any(r.name == "makeindex_doc" for r in rdb.rules)


def test_makeindex_rule_not_added_when_idx_absent(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(r.name == "makeindex_doc" for r in rdb.rules)


def test_makeindex_rule_not_added_twice(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.idx").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert sum(1 for r in rdb.rules if r.name == "makeindex_doc") == 1


def test_glossaries_rule_added_when_glo_exists(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.glo").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert any(r.name == "makeglossaries_doc" for r in rdb.rules)


def test_glossaries_rule_not_added_when_glo_absent(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(r.name == "makeglossaries_doc" for r in rdb.rules)


def test_glossaries_rule_not_added_when_cusdep_configured(tmp_path: Path) -> None:
    tex = _make_tex(tmp_path)
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        custom_deps=(CustomDep(from_ext="glo", to_ext="gls", must=False, command="cmd"),),
    )
    rdb = RuleDatabase(tex, cfg)
    rdb.rules = init_rules(tex, cfg)
    rdb._rule_map = {r.name: r for r in rdb.rules}  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    primary = rdb.rules[0]
    (tmp_path / "doc.glo").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    assert not any(r.name == "makeglossaries_doc" for r in rdb.rules)


def test_makeindex_and_bibtex_coexist(tmp_path: Path) -> None:
    rdb = _rdb_with_primary(tmp_path)
    primary = rdb.rules[0]
    (tmp_path / "doc.aux").write_text("\\bibdata{refs}\n", encoding="utf-8")
    (tmp_path / "refs.bib").write_bytes(b"")
    (tmp_path / "doc.idx").write_bytes(b"")
    rdb._add_secondary_rules(primary)  # noqa: SLF001  # type: ignore[reportPrivateUsage]
    names = [r.name for r in rdb.rules]
    assert "bibtex_doc" in names
    assert "makeindex_doc" in names
