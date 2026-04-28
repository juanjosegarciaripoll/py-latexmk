from __future__ import annotations

import sys
from pathlib import Path

import pytest

from latexmk_py.errors import BuildError
from latexmk_py.runner import RunResult, expand_placeholders, run_command

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = Path("/proj")
_SIMPLE_KWARGS: dict[str, object] = {
    "source": _BASE / "main.tex",
    "dest": _BASE / "main.pdf",
    "base": _BASE / "main",
    "root": _BASE / "main",
    "main_tex": _BASE / "main.tex",
    "extra_opts": [],
    "aux_dir": "",
    "out_dir": "",
}


def _expand(template: str, **overrides: object) -> str:
    kwargs = {**_SIMPLE_KWARGS, **overrides}
    return expand_placeholders(template, **kwargs)  # type: ignore[arg-type]


def _exe_template() -> str:
    """Return 'exe %S' with forward slashes, quoting exe if it contains spaces."""
    exe = sys.executable.replace("\\", "/")
    return f'"{exe}" %S' if " " in exe else f"{exe} %S"


def _write_script(tmp_path: Path, name: str, code: str) -> Path:
    script = tmp_path / name
    script.write_text(code, encoding="utf-8")
    return script


# ---------------------------------------------------------------------------
# expand_placeholders — individual tokens
# ---------------------------------------------------------------------------


def test_expand_token_source() -> None:
    assert _expand("%S") == str(_BASE / "main.tex")


def test_expand_token_dest() -> None:
    assert _expand("%D") == str(_BASE / "main.pdf")


def test_expand_token_base() -> None:
    assert _expand("%B") == "main"


def test_expand_token_root() -> None:
    assert _expand("%R", root=_BASE / "root.tex") == "root"


def test_expand_token_maintex() -> None:
    assert _expand("%T", main_tex=_BASE / "doc.tex") == str(_BASE / "doc.tex")


def test_expand_opts_empty() -> None:
    assert _expand("%O") == ""


def test_expand_opts_single() -> None:
    assert _expand("%O", extra_opts=["-interaction=nonstopmode"]) == "-interaction=nonstopmode"


def test_expand_opts_multiple() -> None:
    result = _expand("%O", extra_opts=["-interaction=nonstopmode", "-synctex=1"])
    assert result == "-interaction=nonstopmode -synctex=1"


def test_expand_auxdir_empty() -> None:
    assert _expand("%Y") == ""


def test_expand_auxdir_set() -> None:
    assert _expand("%Y", aux_dir="build") == "build/"


def test_expand_outdir_empty() -> None:
    assert _expand("%Z") == ""


def test_expand_outdir_set() -> None:
    assert _expand("%Z", out_dir="out") == "out/"


def test_expand_combined_template() -> None:
    src = _BASE / "main.tex"
    result = _expand(
        "pdflatex %O -output-directory=%Z %S",
        extra_opts=["-synctex=1"],
        out_dir="build",
        source=src,
    )
    assert result == f"pdflatex -synctex=1 -output-directory=build/ {src}"


# ---------------------------------------------------------------------------
# expand_placeholders — space-quoting (platform-neutral: use str() for paths)
# ---------------------------------------------------------------------------


def test_space_in_source_gets_quoted() -> None:
    src = Path("/my docs/main.tex")
    result = _expand("%S", source=src)
    assert result == f'"{src}"'


def test_space_in_source_already_quoted_not_double_quoted() -> None:
    src = Path("/my docs/main.tex")
    result = _expand('"%S"', source=src)
    assert result == f'"{src}"'


def test_space_in_dest_gets_quoted() -> None:
    dst = Path("/out put/main.pdf")
    result = _expand("%D", dest=dst)
    assert result == f'"{dst}"'


def test_space_in_aux_dir_gets_quoted() -> None:
    result = _expand("%Y", aux_dir="my build")
    assert result == '"my build/"'


def test_space_in_out_dir_gets_quoted() -> None:
    result = _expand("%Z", out_dir="my out")
    assert result == '"my out/"'


def test_no_space_no_quotes() -> None:
    result = _expand("%S", source=Path("/proj/main.tex"))
    assert '"' not in result


# ---------------------------------------------------------------------------
# run_command — basic execution (script files avoid inline-quoting issues)
# ---------------------------------------------------------------------------


def test_run_returns_run_result(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "raise SystemExit(0)\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert isinstance(result, RunResult)


def test_run_exit_zero(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "raise SystemExit(0)\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert result.exit_code == 0


def test_run_exit_nonzero_no_raise(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "raise SystemExit(42)\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert result.exit_code == 42


def test_run_captures_stdout(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "print('hello runner')\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert "hello runner" in result.stdout


def test_run_captures_stderr(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "import sys; sys.stderr.write('err output\\n')\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert "err output" in result.stderr


def test_run_elapsed_positive(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "pass\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert result.elapsed >= 0.0


# ---------------------------------------------------------------------------
# run_command — shell operator detection
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="shell pipe test requires sh")
def test_shell_pipe_triggers_shell_true() -> None:
    result = run_command("echo foo | cat", **_SIMPLE_KWARGS)  # type: ignore[arg-type]
    assert result.exit_code == 0
    assert "foo" in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="shell semicolon requires sh")
def test_shell_semicolon_triggers_shell_true() -> None:
    result = run_command("echo a; echo b", **_SIMPLE_KWARGS)  # type: ignore[arg-type]
    assert result.exit_code == 0


def test_no_shell_operators_runs_direct(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "pass\n")
    result = run_command(_exe_template(), **{**_SIMPLE_KWARGS, "source": script})  # type: ignore[arg-type]
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# run_command — timeout raises BuildError
# ---------------------------------------------------------------------------


def test_timeout_raises_build_error(tmp_path: Path) -> None:
    script = _write_script(tmp_path, "t.py", "import time; time.sleep(10)\n")
    with pytest.raises(BuildError, match="timed out"):
        run_command(
            _exe_template(),
            **{**_SIMPLE_KWARGS, "source": script},  # type: ignore[arg-type]
            timeout=0.1,
        )
