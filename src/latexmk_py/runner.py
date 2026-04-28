"""Placeholder expansion and subprocess execution for latexmk_py.

This is the only module that calls subprocess.run.

Mirrors the command-template system in latexmk.pl (~lines 2900-3100).
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

from latexmk_py.errors import BuildError

# Shell metacharacters that force shell=True.
# Negative lookbehind skips backslash-escaped occurrences.
SHELL_OPERATORS = re.compile(r"(?<![\\])[|&;]")


@dataclass(slots=True, frozen=True)
class RunResult:
    """Result of a single command run via run_command."""

    exit_code: int
    stdout: str
    stderr: str
    elapsed: float  # wall-clock seconds


def _substitute_path(template: str, token: str, value: str) -> str:
    """Replace token in template, double-quoting value when it contains spaces.

    When the expanded value contains a space the replacement is always
    ``"value"`` whether the token appeared bare or already inside ``"..."``
    in the template.  The two-step order prevents bare replacements from
    double-quoting an occurrence that was already quoted in the template.
    """
    if " " not in value:
        return template.replace(token, value)
    # Step 1: already-quoted occurrences — replace "%S" → "value" (keep quotes).
    result = template.replace(f'"{token}"', f'"{value}"')
    # Step 2: bare occurrences — wrap value in quotes.
    return result.replace(token, f'"{value}"')


def expand_placeholders(
    template: str,
    *,
    source: Path,
    dest: Path,
    base: Path,  # noqa: ARG001 -- part of the interface; not directly expanded
    root: Path,
    main_tex: Path,
    extra_opts: Sequence[str],
    aux_dir: str,
    out_dir: str,
) -> str:
    """Substitute %S %D %B %R %T %O %Y %Z in template.

    Mirrors the command-template handling in ``latexmk.pl`` (~lines 2900-3100).
    Expansion order follows the Perl reference implementation.
    """
    result = template
    result = _substitute_path(result, "%S", str(source))
    result = _substitute_path(result, "%D", str(dest))
    result = _substitute_path(result, "%B", source.stem)
    result = _substitute_path(result, "%R", root.stem)
    result = _substitute_path(result, "%T", str(main_tex))
    # %O is already shell-quoted via shlex.join; no further quoting applied.
    result = result.replace("%O", shlex.join(extra_opts))
    result = _substitute_path(result, "%Y", (aux_dir + "/") if aux_dir else "")
    return _substitute_path(result, "%Z", (out_dir + "/") if out_dir else "")


def run_command(
    template: str,
    *,
    source: Path,
    dest: Path,
    base: Path,
    root: Path,
    main_tex: Path,
    extra_opts: Sequence[str],
    aux_dir: str,
    out_dir: str,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Expand template and execute as a subprocess; return RunResult.

    Never raises on a non-zero exit code -- callers decide whether to raise
    ``BuildError``.  ``subprocess.TimeoutExpired`` is caught and re-raised
    as ``BuildError``.

    Mirrors the ``Run`` / ``Run_SubProcess`` logic in ``latexmk.pl``.
    """
    cmd_str = expand_placeholders(
        template,
        source=source,
        dest=dest,
        base=base,
        root=root,
        main_tex=main_tex,
        extra_opts=extra_opts,
        aux_dir=aux_dir,
        out_dir=out_dir,
    )

    use_shell = bool(SHELL_OPERATORS.search(cmd_str))

    if use_shell:
        cmd: str | list[str] = cmd_str
    elif sys.platform == "win32":
        cmd = shlex.split(cmd_str, posix=False)
    else:
        cmd = shlex.split(cmd_str)

    t0 = time.monotonic()
    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            shell=use_shell,
            capture_output=True,
            encoding="utf-8",
            cwd=cwd,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BuildError(f"latexmk: command timed out: {cmd_str}") from exc
    elapsed = time.monotonic() - t0

    return RunResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        elapsed=elapsed,
    )
