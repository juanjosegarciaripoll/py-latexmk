"""Viewer process management for -pv / -pvc.

Mirrors preview launching behavior in ``latexmk.pl`` (lines ~4000-4200).
"""

from __future__ import annotations

import shlex
import subprocess
from typing import TYPE_CHECKING

from latexmk_py.platform import default_viewer, is_windows
from latexmk_py.runner import expand_placeholders

if TYPE_CHECKING:
    from pathlib import Path

    from latexmk_py.config import Config

_WINDOWS_CREATION_FLAGS = (
    getattr(subprocess, "DETACHED_PROCESS", 0)
    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
)


def _viewer_command_template(output: Path, cfg: Config) -> str:
    suffix = output.suffix.lower()
    if suffix == ".pdf":
        template = cfg.preview.pdf_previewer
    elif suffix == ".dvi":
        template = cfg.preview.dvi_previewer
    elif suffix == ".ps":
        template = cfg.preview.ps_previewer
    else:
        template = cfg.preview.pdf_previewer
    return default_viewer("pdf") if template == "auto" else template


def _viewer_cmd_list(output: Path, cfg: Config) -> list[str]:
    template = _viewer_command_template(output, cfg)
    expanded = expand_placeholders(
        template,
        source=output,
        dest=output,
        base=output.with_suffix(""),
        root=output,
        main_tex=output,
        extra_opts=(),
        aux_dir="",
        out_dir="",
    )
    if is_windows() and template == 'start "" %S':
        return ["cmd", "/c", "start", "", str(output)]
    return shlex.split(expanded, posix=not is_windows())


def open_viewer(output: Path, cfg: Config) -> subprocess.Popen[bytes] | None:
    """Launch viewer for output file; return process handle or None."""
    if not output.exists():
        return None
    cmd_list = _viewer_cmd_list(output, cfg)
    if not cmd_list:
        return None
    if is_windows():
        return subprocess.Popen(  # noqa: S603
            cmd_list,
            creationflags=_WINDOWS_CREATION_FLAGS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return subprocess.Popen(  # noqa: S603
        cmd_list,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def viewer_running(proc: subprocess.Popen[bytes] | None) -> bool:
    """Return whether *proc* is still running."""
    return proc is not None and proc.poll() is None


def refresh_viewer(
    output: Path,
    proc: subprocess.Popen[bytes] | None,
    cfg: Config,
) -> subprocess.Popen[bytes] | None:
    """Reuse existing viewer or start a new one."""
    if not cfg.preview.new_viewer_always and viewer_running(proc):
        return proc
    return open_viewer(output, cfg)
