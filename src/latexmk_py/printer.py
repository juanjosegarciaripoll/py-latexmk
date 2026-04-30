"""Print support - invoke lpr/lpr_pdf/lpr_dvi after a successful build.

Mirrors do_one_tex_file print logic in latexmk.pl (lines 3635-3650)
and $printout_mode / $print_type / $lpr* variables (lines 770-773, 2226-2235).
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

from latexmk_py.runner import SHELL_OPERATORS, expand_placeholders

if TYPE_CHECKING:
    from pathlib import Path

    from latexmk_py.config import Config

log = logging.getLogger(__name__)


def print_output(tex: Path, cfg: Config) -> int:
    """Run the configured print command for the current output mode.

    Returns the subprocess return code (0 = success).
    Mirrors do_one_tex_file print logic in latexmk.pl (lines 3635-3650).
    """
    ptype = resolve_print_type(cfg)
    if ptype == "none":
        return 0
    cmd_template, output_file = resolve_print_cmd_and_file(tex, cfg, ptype)
    if not cmd_template or cmd_template.startswith("NONE"):
        log.warning("latexmk: print command not configured for type %r", ptype)
        return 0
    cmd_str = expand_placeholders(
        cmd_template,
        source=output_file,
        dest=output_file,
        base=output_file.with_suffix(""),
        root=output_file,
        main_tex=tex,
        extra_opts=(),
        aux_dir=cfg.directories.aux_dir,
        out_dir=cfg.directories.out_dir,
    )
    use_shell = bool(SHELL_OPERATORS.search(cmd_str))
    if use_shell:
        cmd: str | list[str] = cmd_str
    elif sys.platform == "win32":
        cmd = cmd_str
    else:
        cmd = shlex.split(cmd_str)
    log.debug("Printing: %s", cmd_str)
    proc = subprocess.run(cmd, shell=use_shell, check=False)  # noqa: S603
    return proc.returncode


def resolve_print_type(cfg: Config) -> str:
    """Return the effective print type, resolving "auto" from the active build mode.

    Mirrors the $print_type / $printout_mode logic in latexmk.pl (lines 2226-2235).
    """
    ptype = cfg.output.print_type
    if ptype != "auto":
        return ptype
    if cfg.build.postscript_mode:
        return "ps"
    if cfg.build.pdf_mode:
        return "pdf"
    if cfg.build.dvi_mode:
        return "dvi"
    return "none"


def resolve_print_cmd_and_file(tex: Path, cfg: Config, ptype: str) -> tuple[str, Path]:
    """Return (command_template, output_path) for the given print type."""
    match ptype:
        case "pdf":
            return cfg.commands.print_pdf, tex.with_suffix(".pdf")
        case "ps":
            return cfg.commands.print_ps, tex.with_suffix(".ps")
        case "dvi":
            return cfg.commands.print_dvi, tex.with_suffix(".dvi")
        case _:
            return "", tex
