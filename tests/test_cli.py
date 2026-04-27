"""Tests for src/latexmk_py/cli.py (T03)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from latexmk_py.cli import (
    VERSION,
    _Flags,  # pyright: ignore[reportPrivateUsage]
    _parse,  # pyright: ignore[reportPrivateUsage]
    _preparse,  # pyright: ignore[reportPrivateUsage]
    _run,  # pyright: ignore[reportPrivateUsage]
)
from latexmk_py.config import BuildConfig, Config, OutputConfig
from latexmk_py.errors import BadOptionsError, FileMissingError

if TYPE_CHECKING:
    from pathlib import Path


def _cfg(argv: list[str]) -> Config:
    """Parse *argv* against default Config; return resulting Config."""
    cfg, _, _ = _parse(argv, Config())
    return cfg


def _fls(argv: list[str]) -> _Flags:  # pyright: ignore[reportPrivateUsage]
    """Parse *argv* against default Config; return dispatch flags."""
    _, flags, _ = _parse(argv, Config())
    return flags


# ── help / version ────────────────────────────────────────────────────────────


def test_help_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-help"])
    assert exc_info.value.code == 0
    assert "Usage" in capsys.readouterr().out


def test_h_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-h"])
    assert exc_info.value.code == 0
    assert "Usage" in capsys.readouterr().out


def test_version_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-version"])
    assert exc_info.value.code == 0
    assert f"latexmk version {VERSION}" in capsys.readouterr().out


def test_v_exits_0() -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-v"])
    assert exc_info.value.code == 0


def test_commands_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-commands", "-norc"])
    assert exc_info.value.code == 0
    assert "pdflatex" in capsys.readouterr().out


def test_dir_report_only_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-dir-report-only", "-norc"])
    assert exc_info.value.code == 0
    assert "out_dir" in capsys.readouterr().out


def test_showextraoptions_exits_0() -> None:
    with pytest.raises(SystemExit) as exc_info:
        _run(["-showextraoptions"])
    assert exc_info.value.code == 0


# ── unknown flags ─────────────────────────────────────────────────────────────


def test_unknown_flag_raises() -> None:
    with pytest.raises(BadOptionsError, match="unknown option"):
        _run(["-notaflag"])


def test_unknown_flag_message() -> None:
    with pytest.raises(BadOptionsError, match="latexmk:"):
        _parse(["-NOPE"], Config())


# ── no tex files ──────────────────────────────────────────────────────────────


def test_no_tex_files_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileMissingError):
        _run(["-norc"])


def test_missing_explicit_file_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileMissingError, match="not found"):
        _run(["-norc", "ghost.tex"])


# ── output format flags ───────────────────────────────────────────────────────


def test_pdf_mode_flags() -> None:
    assert _cfg(["-pdf"]).build.pdf_mode == 1
    assert _cfg(["-pdfdvi"]).build.pdf_mode == 2
    assert _cfg(["-pdflua"]).build.pdf_mode == 4
    assert _cfg(["-pdfxe"]).build.pdf_mode == 5
    assert _cfg(["-pdf-"]).build.pdf_mode == 0


def test_dvi_mode_flags() -> None:
    assert _cfg(["-dvi"]).build.dvi_mode == 1
    assert _cfg(["-dvilua"]).build.dvi_mode == 2
    assert _cfg(["-dvi-"]).build.dvi_mode == 0


def test_ps_mode_flags() -> None:
    assert _cfg(["-ps"]).build.postscript_mode == 1
    assert _cfg(["-ps-"]).build.postscript_mode == 0


def test_output_format_shorthand() -> None:
    assert _cfg(["-output-format=pdf"]).build.pdf_mode == 1
    assert _cfg(["-output-format=dvi"]).build.dvi_mode == 1
    assert _cfg(["-output-format=ps"]).build.postscript_mode == 1
    assert _cfg(["-output-format=dvilua"]).build.dvi_mode == 2
    assert _cfg(["-output-format=pdfxe"]).build.pdf_mode == 5


def test_output_format_unknown_raises() -> None:
    with pytest.raises(BadOptionsError):
        _parse(["-output-format=unknown"], Config())


# ── directory flags ───────────────────────────────────────────────────────────


def test_outdir_equals() -> None:
    assert _cfg(["-outdir=build"]).directories.out_dir == "build"


def test_outdir_space() -> None:
    assert _cfg(["-outdir", "build"]).directories.out_dir == "build"


def test_output_directory_alias() -> None:
    assert _cfg(["-output-directory=out"]).directories.out_dir == "out"


def test_auxdir_equals() -> None:
    assert _cfg(["-auxdir=aux"]).directories.aux_dir == "aux"


def test_aux_directory_alias() -> None:
    assert _cfg(["-aux-directory", "aux"]).directories.aux_dir == "aux"


def test_out2dir() -> None:
    assert _cfg(["-out2dir=final"]).directories.out2_dir == "final"


def test_cd_flags() -> None:
    assert _cfg(["-cd"]).build.cd is True
    assert _cfg(["-cd-"]).build.cd is False


def test_jobname() -> None:
    assert _cfg(["-jobname=myjob"]).build.jobname == "myjob"


def test_emulate_aux_dir_flags() -> None:
    assert _cfg(["-emulate-aux-dir"]).directories.emulate_aux_dir is True
    assert _cfg(["-emulate-aux-dir-"]).directories.emulate_aux_dir is False


# ── bibtex flags ──────────────────────────────────────────────────────────────


def test_bibtex_force() -> None:
    assert _cfg(["-bibtex"]).bibtex.use == 2.0


def test_bibtex_disable() -> None:
    assert _cfg(["-bibtex-"]).bibtex.use == 0.0
    assert _cfg(["-nobibtex"]).bibtex.use == 0.0


def test_bibtex_cond() -> None:
    assert _cfg(["-bibtex-cond"]).bibtex.use == 1.0
    assert _cfg(["-bibtex-cond1"]).bibtex.use == 1.5


def test_bibtex_cmd() -> None:
    assert _cfg(["-bibtex=mybibtex"]).commands.bibtex == "mybibtex"


def test_bibtexfudge_flags() -> None:
    assert _cfg(["-bibtexfudge"]).bibtex.fudge is True
    assert _cfg(["-bibtexfudge-"]).bibtex.fudge is False
    assert _cfg(["-nobibtexfudge"]).bibtex.fudge is False


def test_biber_cmd() -> None:
    assert _cfg(["-biber=mybiber"]).commands.biber == "mybiber"


# ── processing flags ──────────────────────────────────────────────────────────


def test_force_flags() -> None:
    assert _cfg(["-f"]).force is True
    assert _cfg(["-f-"]).force is False


def test_go_mode_flags() -> None:
    assert _fls(["-g"]).go_mode == 1
    assert _fls(["-g-"]).go_mode == 0
    assert _fls(["-gg"]).go_mode == 2
    assert _fls(["-gt"]).go_mode == 3


def test_gg_also_sets_cleanup_mode() -> None:
    flags = _fls(["-gg"])
    assert flags.cleanup_mode == 2


def test_recorder_flags() -> None:
    assert _cfg(["-recorder"]).build.recorder is True
    assert _cfg(["-recorder-"]).build.recorder is False


def test_interaction_appends_to_extra_opts() -> None:
    opts = _cfg(["-interaction=nonstopmode"]).build.latex_extra_options
    assert "-interaction=nonstopmode" in opts


def test_interaction_as_separate_arg() -> None:
    opts = _cfg(["-interaction", "batchmode"]).build.latex_extra_options
    assert "-interaction=batchmode" in opts


def test_interaction_appends_to_existing() -> None:
    base = Config(build=BuildConfig(latex_extra_options=("-file-line-error",)))
    cfg, _, _ = _parse(["-interaction=nonstopmode"], base)
    assert cfg.build.latex_extra_options == ("-file-line-error", "-interaction=nonstopmode")


# ── preview flags ─────────────────────────────────────────────────────────────


def test_preview_flags() -> None:
    assert _fls(["-pv"]).preview_mode is True
    assert _fls(["-pvc"]).preview_continuous is True
    assert _fls(["-pvc-"]).preview_continuous is False


def test_view_flag() -> None:
    assert _cfg(["-view=pdf"]).preview.view == "pdf"
    assert _cfg(["-view", "dvi"]).preview.view == "dvi"


def test_pvctimeoutmins() -> None:
    assert _cfg(["-pvctimeoutmins=5"]).preview.timeout_mins == 5.0


def test_pvctimeoutmins_invalid_raises() -> None:
    with pytest.raises(BadOptionsError, match="requires a number"):
        _parse(["-pvctimeoutmins=abc"], Config())


def test_new_viewer_flags() -> None:
    assert _cfg(["-new-viewer"]).preview.new_viewer_always is True
    assert _cfg(["-new-viewer-"]).preview.new_viewer_always is False


def test_print_flags() -> None:
    assert _fls(["-p"]).print_mode is True
    assert _fls(["-print=pdf"]).print_what == "pdf"


# ── cleanup flags ─────────────────────────────────────────────────────────────


def test_cleanup_flags() -> None:
    assert _fls(["-c"]).cleanup_mode == 1
    assert _fls(["-C"]).cleanup_mode == 2
    assert _fls(["-CA"]).cleanup_mode == 2
    assert _fls(["-CF"]).cleanup_fdb is True


# ── dependency flags ──────────────────────────────────────────────────────────


def test_deps_flags() -> None:
    assert _cfg(["-deps"]).deps.enabled is True
    assert _cfg(["-dependents"]).deps.enabled is True
    assert _cfg(["-deps-"]).deps.enabled is False


def test_deps_out() -> None:
    assert _cfg(["-deps-out=deps.d"]).deps.file == "deps.d"


def test_deps_escape() -> None:
    assert _cfg(["-deps-escape=unix"]).deps.escape == "unix"


def test_m_and_mf_flags() -> None:
    assert _cfg(["-M"]).deps.enabled is True
    assert _cfg(["-MF", "out.d"]).deps.file == "out.d"
    assert _cfg(["-MP"]).deps.phony is True


# ── diagnostics flags ─────────────────────────────────────────────────────────


def test_quiet_flags() -> None:
    assert _cfg(["-quiet"]).output.silent is True
    assert _cfg(["-silent"]).output.silent is True


def test_diagnostics_overrides_silent() -> None:
    base = Config(output=OutputConfig(silent=True))
    cfg, flags, _ = _parse(["-diagnostics"], base)
    assert cfg.output.silent is False
    assert flags.verbose is True


def test_time_flags() -> None:
    assert _cfg(["-time"]).output.show_time is True
    assert _cfg(["-time-"]).output.show_time is False


def test_werror_flag() -> None:
    assert _cfg(["-Werror"]).output.warnings_as_errors is True


def test_rc_report_flags() -> None:
    assert _cfg(["-rc-report"]).output.rc_report is True
    assert _cfg(["-rc-report-"]).output.rc_report is False


def test_rules_flags() -> None:
    assert _fls(["-rules"]).rules_list is True
    assert _fls(["-rules-"]).rules_list is False


def test_logfilewarnings_flag() -> None:
    assert _fls(["-logfilewarnings"]).log_warnings is True


# ── config control ────────────────────────────────────────────────────────────


def test_norc_flag_is_accepted() -> None:
    # -norc is silently passed through (already handled by _preparse)
    _parse(["-norc"], Config())


def test_r_flag_is_accepted() -> None:
    # -r FILE is silently passed through (already handled by _preparse)
    _parse(["-r", "extra.toml"], Config())


def test_r_equals_form() -> None:
    _, extra = _preparse(["-r=extra.toml"])
    assert extra == ["extra.toml"]


# ── preparse ──────────────────────────────────────────────────────────────────


def test_preparse_norc() -> None:
    norc, extra = _preparse(["-norc", "file.tex"])
    assert norc is True
    assert extra == []


def test_preparse_r_file() -> None:
    norc, extra = _preparse(["-r", "my.toml"])
    assert norc is False
    assert extra == ["my.toml"]


def test_preparse_stops_at_double_dash() -> None:
    norc, _extra = _preparse(["--", "-norc"])
    assert norc is False


def test_preparse_r_missing_arg_raises() -> None:
    with pytest.raises(BadOptionsError, match="-r requires"):
        _preparse(["-r"])


# ── positional args ───────────────────────────────────────────────────────────


def test_positional_args_become_tex_files() -> None:
    _, _, tex = _parse(["file1.tex", "file2.tex"], Config())
    assert tex == ["file1.tex", "file2.tex"]


def test_double_dash_ends_option_parsing() -> None:
    cfg, _, tex = _parse(["-pdf", "--", "-notaflag.tex"], Config())
    assert cfg.build.pdf_mode == 1
    assert tex == ["-notaflag.tex"]


# ── config suppression / override ────────────────────────────────────────────


def test_norc_suppresses_config_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "latexmk.toml").write_text("[build]\npdf_mode = 99\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    # With -norc the broken file is skipped; FileMissingError (no .tex) expected
    with pytest.raises(FileMissingError):
        _run(["-norc"])


def test_r_file_applies_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc = tmp_path / "extra.toml"
    rc.write_text("[build]\npdf_mode = 0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileMissingError):
        _run(["-norc", "-r", str(rc)])


# ── flag splitting edge cases ────────────────────────────────────────────────


def test_positional_with_equals_not_split() -> None:
    """A positional arg containing '=' must not be split as a flag."""
    _, _, tex = _parse(["foo=mma.tex"], Config())
    assert tex == ["foo=mma.tex"]


def test_flag_value_with_equals_in_value() -> None:
    """-outdir=a=b should give out_dir='a=b', not split further."""
    assert _cfg(["-outdir=a=b"]).directories.out_dir == "a=b"


def test_dash_only_with_equals_is_unknown_flag() -> None:
    """-=value has no alphanumeric name; must not be split, reported as unknown."""
    with pytest.raises(BadOptionsError, match="unknown option"):
        _parse(["-=value"], Config())


# ── _Flags defaults ───────────────────────────────────────────────────────────


def test_flags_defaults() -> None:
    flags = _Flags()  # pyright: ignore[reportPrivateUsage]
    assert flags.cleanup_mode == 0
    assert flags.go_mode == 0
    assert flags.preview_continuous is False
    assert flags.verbose is False
