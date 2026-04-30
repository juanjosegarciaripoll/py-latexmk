"""CLI entry point for latexmk_py.

Parses all CLI flags, loads TOML config, applies overrides, dispatches.
Mirrors the argument-parsing logic in latexmk.pl (lines ~500-900).
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys
from dataclasses import dataclass, replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

from latexmk_py.cleaner import clean
from latexmk_py.config import CommandsConfig, Config, load_config
from latexmk_py.errors import (
    BadOptionsError,
    BuildError,
    ConfigError,
    FileMissingError,
    LatexmkError,
)
from latexmk_py.platform import user_log_dir
from latexmk_py.rdb import RuleDatabase

PERL_LATEXMK_VERSION = "4.88"

_GO_CLEAN_REBUILD = 2  # go_mode value for -gg: clean then rebuild
_CLEAN_MODE_FULL = 2

# Matches -flagname=value where flagname is letters/digits/hyphens.
# Guards against splitting filenames that happen to contain '='.
_OPT_ASSIGN = re.compile(r"^-[A-Za-z0-9][A-Za-z0-9-]*=")

# Options recognised but not interpreted by latexmk; forwarded to *latex.
# Source: latexmk.pl lines 549-668.
_PASSTHROUGH_FLAGS: frozenset[str] = frozenset(
    {
        "-cnf-line",
        "-draftmode",
        "-enc",
        "-etex",
        "-file-line-error",
        "-no-file-line-error",
        "-fmt",
        "-halt-on-error",
        "-ipc",
        "-ipc-start",
        "-kpathsea-debug",
        "-mktex",
        "-no-mktex",
        "-mltex",
        "-output-comment",
        "-parse-first-line",
        "-no-parse-first-line",
        "-progname",
        "-shell-escape",
        "-no-shell-escape",
        "-shell-restricted",
        "-src-specials",
        "-synctex",
        "-translate-file",
        "-8bit",
        # MiKTeX
        "-alias",
        "-buf-size",
        "-c-style-errors",
        "-no-c-style-errors",
        "-disable-installer",
        "-enable-installer",
        "-disable-pipes",
        "-enable-pipes",
        "-disable-write18",
        "-enable-write18",
        "-restrict-write18",
        "-dont-parse-first-line",
        "-enable-enctex",
        "-enable-mltex",
        "-error-line",
        "-extra-mem-bot",
        "-extra-mem-top",
        "-font-max",
        "-font-mem-size",
        "-half-error-line",
        "-hash-extra",
        "-job-time",
        "-main-memory",
        "-max-in-open",
        "-max-print-line",
        "-max-strings",
        "-nest-size",
        "-param-size",
        "-pool-size",
        "-record-package-usages",
        "-save-size",
        "-stack-size",
        "-string-vacancies",
        "-tcx",
        "-time-statistics",
        "-trace",
        "-trie-size",
        "-undump",
    }
)

_HELP = """\
Usage: latexmk [options] [file ...]

Output format:
  -pdf               Build PDF via pdflatex (default)
  -pdfdvi            Build PDF via latex+dvipdf
  -pdflua            Build PDF via lualatex
  -pdfxe             Build PDF via xelatex
  -pdf-              Disable PDF output
  -dvi / -dvi-       DVI mode on/off
  -dvilua            DVI via lualatex
  -ps / -ps-         PostScript mode on/off
  -output-format=F   Shorthand: pdf/dvi/ps/dvilua/pdfxe

Engine commands (optional =CMD replaces the command):
  -latex[=CMD]       -pdflatex[=CMD]  -lualatex[=CMD]  -xelatex[=CMD]
  -bibtex[=CMD]      -biber[=CMD]
  -stdtexcmds        Reset all commands to built-in defaults

Directories:
  -auxdir=D / -aux-directory=D     Auxiliary files directory
  -outdir=D / -output-directory=D  Main output directory
  -out2dir=D                       Secondary output directory
  -cd / -cd-                       cd to source dir on/off
  -jobname=N                       Set \\jobname
  -emulate-aux-dir / -emulate-aux-dir-

BibTeX/Biber:
  -bibtex / -bibtex- / -nobibtex   Force/disable BibTeX
  -bibtex-cond / -bibtex-cond1     Conditional BibTeX modes
  -bibtexfudge / -bibtexfudge- / -nobibtexfudge
  -bibtex-min-crossrefs=N          Pass -min-crossrefs=N to bibtex

Processing:
  -f / -f-           Force rebuild on/off
  -g / -g-           Force rerun on/off
  -gg                Clean then rebuild
  -gt                Regenerate all outputs
  -recorder / -recorder-
  -interaction=MODE  Pass -interaction=MODE to *latex
  -pretex=CODE / -usepretex[=CODE]

Preview:
  -l / -l-           Landscape mode on/off
  -xdv / -xdv-       XDV-only output on/off (xelatex without xdvipdfmx)
  -pv                Open viewer after build
  -pvc / -pvc-       Continuous preview on/off
  -view=WHAT         What to view: default/pdf/dvi/ps/none
  -pvctimeout / -pvctimeoutmins=N
  -new-viewer / -new-viewer-
  -p                 Print after build
  -print=WHAT        dvi/ps/pdf

Cleanup:
  -c                 Remove regenerable auxiliary files
  -C / -CA           Remove all generated files
  -CF                Also remove .fdb_latexmk

Dependency output:
  -deps / -deps-     Enable/disable dependency output
  -deps-out=F        Write deps to file F
  -deps-escape=K     Escape style: none/unix/nmake
  -M                 Enable deps (same as -deps)
  -MF F              Write deps to F
  -MP                Add phony targets

Config:
  -norc              Skip all config files
  -r FILE            Load extra TOML config file

Diagnostics:
  -h / -help         This help text
  -v / -version      Print version and exit
  -commands          Show resolved command strings
  -diagnostics       Verbose diagnostic output
  -dir-report        Show resolved directory paths
  -dir-report-only   Show directories and exit
  -time / -time-     Show per-rule timing on/off
  -rc-report / -rc-report-
  -rules / -rules-
  -quiet / -silent   Suppress informational output
  -logfilewarnings / -logfilewarninglist   Show warnings from log file
  -Werror            Treat warnings as errors
  -showextraoptions  List passthrough *latex options
"""


# ── dispatch-only flags (not stored in Config) ────────────────────────────────


@dataclass
class _Flags:
    """CLI flags that control dispatch but don't belong in Config."""

    preview_mode: bool = False
    preview_continuous: bool = False
    print_mode: bool = False
    print_what: str | None = None  # None means not explicitly set; resolved from config default
    cleanup_mode: int = 0
    cleanup_fdb: bool = False
    go_mode: int = 0  # 0=normal 1=-g 2=-gg 3=-gt
    pretex: str = ""
    verbose: bool = False
    dir_report: bool = False
    dir_report_only: bool = False
    rules_list: bool = False
    log_warnings: bool = False
    want_help: bool = False
    want_version: bool = False
    want_commands: bool = False
    want_showextraoptions: bool = False


# ── parsing helpers ───────────────────────────────────────────────────────────


def _preparse(argv: list[str]) -> tuple[bool, list[str]]:
    """First pass: extract -norc and -r FILE before config loading."""
    norc = False
    extra_rc: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            break
        if a == "-norc":
            norc = True
        elif a == "-r":
            i += 1
            if i >= len(argv):
                raise BadOptionsError("latexmk: -r requires a file argument")
            extra_rc.append(argv[i])
        elif a.startswith("-r="):
            extra_rc.append(a[3:])
        i += 1
    return norc, extra_rc


def _take(argv: list[str], i: int, flag: str) -> tuple[str, int]:
    """Return (value, next_index) or raise BadOptionsError."""
    if i >= len(argv):
        raise BadOptionsError(f"latexmk: {flag} requires an argument")
    return argv[i], i + 1


def _parse(argv: list[str], base: Config) -> tuple[Config, _Flags, list[str]]:  # noqa: C901
    """Parse *argv* on top of *base*, returning (updated Config, flags, tex files)."""
    build = base.build
    cmds = base.commands
    dirs = base.directories
    bibtex = base.bibtex
    preview = base.preview
    output = base.output
    deps = base.deps
    force = base.force

    flags = _Flags()
    tex_files: list[str] = []
    i = 0

    while i < len(argv):
        raw = argv[i]
        i += 1

        if raw == "--":
            tex_files.extend(argv[i:])
            break

        if not raw.startswith("-"):
            tex_files.append(raw)
            continue

        # Mirror latexmk.pl line 2038: s/^--/-/
        # Normalize double-dash prefix for matching; pass raw to *latex.
        normalized = "-" + raw[2:] if raw.startswith("--") else raw

        # Split -flagname=value only when the part before '=' is a valid flag name.
        if _OPT_ASSIGN.match(normalized):
            flag, val_str = normalized.split("=", 1)
            has_val = True
        else:
            flag, val_str, has_val = normalized, "", False

        match flag:
            # ── output format ─────────────────────────────────────────────
            case "-pdf":
                build = replace(build, pdf_mode=1)
            case "-pdfdvi":
                build = replace(build, pdf_mode=2)
            case "-pdflua":
                build = replace(build, pdf_mode=4)
            case "-pdfxe":
                build = replace(build, pdf_mode=5)
            case "-pdf-":
                build = replace(build, pdf_mode=0)
            case "-dvi":
                build = replace(build, dvi_mode=1)
            case "-dvilua":
                build = replace(build, dvi_mode=2)
            case "-dvi-":
                build = replace(build, dvi_mode=0)
            case "-ps":
                build = replace(build, postscript_mode=1)
            case "-ps-":
                build = replace(build, postscript_mode=0)
            case "-output-format":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                match val_str:
                    case "pdf":
                        build = replace(build, pdf_mode=1)
                    case "dvi":
                        build = replace(build, dvi_mode=1)
                    case "ps":
                        build = replace(build, postscript_mode=1)
                    case "dvilua":
                        build = replace(build, dvi_mode=2)
                    case "pdfxe":
                        build = replace(build, pdf_mode=5)
                    case _:
                        raise BadOptionsError(f"latexmk: unknown -output-format value {val_str!r}")
            # ── engine commands ───────────────────────────────────────────
            case "-latex":
                if has_val:
                    cmds = replace(cmds, latex=val_str)
            case "-pdflatex":
                if has_val:
                    cmds = replace(cmds, pdflatex=val_str)
            case "-lualatex":
                if has_val:
                    cmds = replace(cmds, lualatex=val_str)
            case "-xelatex":
                if has_val:
                    cmds = replace(cmds, xelatex=val_str)
            case "-stdtexcmds":
                cmds = CommandsConfig()
            # ── directories ───────────────────────────────────────────────
            case "-auxdir" | "-aux-directory":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                dirs = replace(dirs, aux_dir=val_str)
            case "-outdir" | "-output-directory":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                dirs = replace(dirs, out_dir=val_str)
            case "-out2dir":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                dirs = replace(dirs, out2_dir=val_str)
            case "-cd":
                build = replace(build, cd=True)
            case "-cd-":
                build = replace(build, cd=False)
            case "-jobname":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                build = replace(build, jobname=val_str)
            case "-emulate-aux-dir":
                dirs = replace(dirs, emulate_aux_dir=True)
            case "-emulate-aux-dir-":
                dirs = replace(dirs, emulate_aux_dir=False)
            # ── bibtex / biber ────────────────────────────────────────────
            case "-bibtex":
                # -bibtex=CMD sets the command; bare -bibtex forces use=2
                if has_val:
                    cmds = replace(cmds, bibtex=val_str)
                else:
                    bibtex = replace(bibtex, use=2.0)
            case "-bibtex-" | "-nobibtex":
                bibtex = replace(bibtex, use=0.0)
            case "-bibtex-cond":
                bibtex = replace(bibtex, use=1.0)
            case "-bibtex-cond1":
                bibtex = replace(bibtex, use=1.5)
            case "-bibtexfudge":
                bibtex = replace(bibtex, fudge=True)
            case "-bibtexfudge-" | "-nobibtexfudge":
                bibtex = replace(bibtex, fudge=False)
            case "-bibtex-min-crossrefs":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                try:
                    bibtex = replace(bibtex, min_crossrefs=int(val_str))
                except ValueError:
                    raise BadOptionsError(
                        "latexmk: -bibtex-min-crossrefs requires an integer"
                    ) from None
            case "-biber":
                if has_val:
                    cmds = replace(cmds, biber=val_str)
                else:
                    bibtex = replace(bibtex, use=2.0)
            # ── processing ────────────────────────────────────────────────
            case "-f":
                force = True
            case "-f-":
                force = False
            case "-g":
                flags.go_mode = 1
            case "-g-":
                flags.go_mode = 0
            case "-gg":
                flags.go_mode = _GO_CLEAN_REBUILD
                flags.cleanup_mode = _GO_CLEAN_REBUILD
            case "-gt":
                flags.go_mode = 3
            case "-recorder":
                build = replace(build, recorder=True)
            case "-recorder-":
                build = replace(build, recorder=False)
            case "-interaction":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                build = replace(
                    build,
                    latex_extra_options=(*build.latex_extra_options, f"-interaction={val_str}"),
                )
            case "-pretex":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                flags.pretex = val_str
            case "-usepretex":
                flags.pretex = val_str if has_val else ""
            case "-latexoption":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                build = replace(build, latex_extra_options=(*build.latex_extra_options, val_str))
            case "-l":
                build = replace(build, landscape=True)
            case "-l-":
                build = replace(build, landscape=False)
            case "-xdv":
                build = replace(build, xdv_mode=1, pdf_mode=0)
            case "-xdv-":
                build = replace(build, xdv_mode=0)
            # ── preview / print ───────────────────────────────────────────
            case "-pv":
                flags.preview_mode = True
            case "-pvc":
                flags.preview_continuous = True
            case "-pvc-":
                flags.preview_continuous = False
            case "-view":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                preview = replace(preview, view=val_str)
            case "-pvctimeout":
                pass  # enables timeout; actual value set by -pvctimeoutmins
            case "-pvctimeoutmins":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                try:
                    preview = replace(preview, timeout_mins=float(val_str))
                except ValueError:
                    raise BadOptionsError(
                        f"latexmk: -pvctimeoutmins requires a number, got {val_str!r}"
                    ) from None
            case "-new-viewer":
                preview = replace(preview, new_viewer_always=True)
            case "-new-viewer-":
                preview = replace(preview, new_viewer_always=False)
            case "-p":
                flags.print_mode = True
            case "-print":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                flags.print_what = val_str
            # ── cleanup ───────────────────────────────────────────────────
            case "-c":
                flags.cleanup_mode = 1
            case "-C" | "-CA":
                flags.cleanup_mode = 2
            case "-CF":
                flags.cleanup_fdb = True
            # ── dependency output ─────────────────────────────────────────
            case "-deps" | "-dependents":
                deps = replace(deps, enabled=True)
            case "-deps-":
                deps = replace(deps, enabled=False)
            case "-deps-out":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                deps = replace(deps, file=val_str)
            case "-deps-escape":
                if not has_val:
                    val_str, i = _take(argv, i, flag)
                deps = replace(deps, escape=val_str)
            case "-M":
                deps = replace(deps, enabled=True)
            case "-MF":
                val_str, i = _take(argv, i, flag)
                deps = replace(deps, file=val_str)
            case "-MP":
                deps = replace(deps, phony=True)
            # ── config control ────────────────────────────────────────────
            case "-norc":
                pass  # already handled by _preparse + load_config
            case "-r":
                if not has_val:
                    _, i = _take(argv, i, flag)
                # already handled by _preparse + load_config
            # ── diagnostics ───────────────────────────────────────────────
            case "-h" | "-help":
                flags.want_help = True
            case "-v" | "-version":
                flags.want_version = True
            case "-commands":
                flags.want_commands = True
            case "-diagnostics":
                flags.verbose = True
                output = replace(output, silent=False)
            case "-dir-report":
                flags.dir_report = True
            case "-dir-report-only":
                flags.dir_report_only = True
            case "-time":
                output = replace(output, show_time=True)
            case "-time-":
                output = replace(output, show_time=False)
            case "-rc-report":
                output = replace(output, rc_report=True)
            case "-rc-report-":
                output = replace(output, rc_report=False)
            case "-rules":
                flags.rules_list = True
            case "-rules-":
                flags.rules_list = False
            case "-quiet" | "-silent":
                output = replace(output, silent=True)
            case "-logfilewarninglist" | "-logfilewarnings":
                flags.log_warnings = True
            case "-logfilewarninglist-" | "-logfilewarnings-":
                flags.log_warnings = False
            case "-Werror":
                output = replace(output, warnings_as_errors=True)
            case "-showextraoptions":
                flags.want_showextraoptions = True
            case _:
                if flag in _PASSTHROUGH_FLAGS:
                    build = replace(build, latex_extra_options=(*build.latex_extra_options, raw))
                else:
                    raise BadOptionsError(f"latexmk: unknown option {raw!r}")

    cfg = replace(
        base,
        build=build,
        commands=cmds,
        directories=dirs,
        bibtex=bibtex,
        preview=preview,
        output=output,
        deps=deps,
        force=force,
    )
    return cfg, flags, tex_files


# ── output helpers ────────────────────────────────────────────────────────────


def _out(msg: str = "") -> None:
    print(msg)  # noqa: T201


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)  # noqa: T201


# ── info printers ─────────────────────────────────────────────────────────────


def _print_help() -> None:
    _out(_HELP.rstrip())


def _print_commands(cfg: Config) -> None:
    c = cfg.commands
    _out(f"latex:          {c.latex}")
    _out(f"pdflatex:       {c.pdflatex}")
    _out(f"lualatex:       {c.lualatex}")
    _out(f"xelatex:        {c.xelatex}")
    _out(f"bibtex:         {c.bibtex}")
    _out(f"biber:          {c.biber}")
    _out(f"makeindex:      {c.makeindex}")
    _out(f"dvips:          {c.dvips}")
    _out(f"dvipdf:         {c.dvipdf}")
    _out(f"ps2pdf:         {c.ps2pdf}")
    _out(f"makeglossaries: {c.makeglossaries}")


def _print_dirs(cfg: Config) -> None:
    d = cfg.directories
    _out(f"aux_dir:  {d.aux_dir or '(same as out_dir)'}")
    _out(f"out_dir:  {d.out_dir or '(source directory)'}")
    _out(f"out2_dir: {d.out2_dir or '(same as out_dir)'}")


def _python_version_suffix() -> str:
    """Return optional Python package version suffix for informational output."""
    try:
        pkg_version = version("latexmk")
    except PackageNotFoundError:
        return ""
    return f" (python package {pkg_version})"


# ── file resolution ───────────────────────────────────────────────────────────


def _resolve_tex_files(pos_args: list[str], cfg: Config) -> list[Path]:
    """Return .tex file paths from positional args or config glob patterns."""
    if pos_args:
        # Mirrors find_basename in latexmk.pl (lines 4317-4321).
        # Rule 1: ext==.tex and file exists → use as-is.
        # Rule 2: file.tex exists (regardless of ext) → use file.tex.
        # Rule 3: file exists with any extension → use as-is.
        # Uses is_file() to match Perl's -f (regular file, not directory).
        def _resolve_one(s: str) -> Path:
            p = Path(s)
            if p.suffix == ".tex" and p.is_file():  # rule 1
                return p
            tex = Path(str(p) + ".tex")
            if tex.is_file():  # rule 2
                return tex
            return p  # rule 3 / not found (caught below)

        paths = [_resolve_one(f) for f in pos_args]
        missing = [p for p in paths if not p.exists()]
        if missing:
            names = ", ".join(str(p) for p in missing)
            raise FileMissingError(f"latexmk: file(s) not found: {names}")
        return paths

    excluded = set(cfg.build.default_excluded_files)
    results: list[Path] = []
    for pat in cfg.build.default_files:
        results.extend(p for p in Path().glob(pat) if str(p) not in excluded)
    if not results:
        raise FileMissingError("latexmk: no .tex files found")
    return results


# ── stub dispatch ─────────────────────────────────────────────────────────────


def _run_build(tex_files: list[Path], cfg: Config) -> None:
    for f in tex_files:
        rc = RuleDatabase(f, cfg).build()
        if rc != 0:
            raise BuildError(f"latexmk: build failed for {f}")


def _run_watch(tex_files: list[Path], cfg: Config) -> None:
    for f in tex_files:
        rc = RuleDatabase(f, cfg).watch()
        if rc != 0:
            raise BuildError(f"latexmk: watch failed for {f}")


def _clean_mode_value(cleanup_mode: int) -> Literal[1, 2]:
    return 2 if cleanup_mode >= _CLEAN_MODE_FULL else 1


def _run_clean(tex_files: list[Path], cfg: Config, *, cleanup_mode: int, cleanup_fdb: bool) -> None:
    mode = _clean_mode_value(cleanup_mode)
    for f in tex_files:
        clean(f, cfg, mode=mode, fdb_only=cleanup_fdb and cleanup_mode == 0)
        if cleanup_fdb and cleanup_mode > 0:
            clean(f, cfg, mode=mode, fdb_only=True)


# ── core logic ────────────────────────────────────────────────────────────────


def _dispatch_info_flags(flags: _Flags, cfg: Config) -> None:
    """Handle immediate-exit diagnostic flags; exits if any flag is active."""
    if flags.want_help:
        _print_help()
        sys.exit(0)
    if flags.want_version:
        _out(f"latexmk version {PERL_LATEXMK_VERSION}{_python_version_suffix()}")
        sys.exit(0)
    if flags.want_showextraoptions:
        _out("Options forwarded to *latex (not interpreted by latexmk):\n")
        for opt in sorted(_PASSTHROUGH_FLAGS):
            _out(f"  {opt}")
        sys.exit(0)
    if flags.want_commands:
        _print_commands(cfg)
        sys.exit(0)
    if flags.dir_report_only:
        _print_dirs(cfg)
        sys.exit(0)
    if flags.dir_report:
        _print_dirs(cfg)


def _run(argv: list[str]) -> None:
    """Parse *argv*, load config, apply overrides, dispatch."""
    # Phase 1: extract -norc / -r before loading config
    norc, extra_rc = _preparse(argv)
    cfg, _loaded = load_config(norc=norc, extra_rc_files=extra_rc)

    # Phase 2: full parse on top of loaded config
    cfg, flags, tex_args = _parse(argv, cfg)

    _dispatch_info_flags(flags, cfg)

    tex_files = _resolve_tex_files(tex_args, cfg)

    cfg = replace(cfg, preview_mode=flags.preview_mode or flags.preview_continuous)

    if flags.print_what is not None:
        cfg = replace(cfg, output=replace(cfg.output, print_type=flags.print_what))

    # Pure cleanup: -c / -C / -CF without -gg
    if (flags.cleanup_mode > 0 or flags.cleanup_fdb) and flags.go_mode != _GO_CLEAN_REBUILD:
        _run_clean(tex_files, cfg, cleanup_mode=flags.cleanup_mode, cleanup_fdb=flags.cleanup_fdb)
        return

    # -gg: clean first, then fall through to build
    if flags.go_mode == _GO_CLEAN_REBUILD:
        _run_clean(tex_files, cfg, cleanup_mode=flags.cleanup_mode, cleanup_fdb=flags.cleanup_fdb)

    if flags.preview_continuous:
        _run_watch(tex_files, cfg)
    else:
        _run_build(tex_files, cfg)
        if flags.print_mode:
            from latexmk_py.printer import print_output  # noqa: PLC0415

            for f in tex_files:
                print_output(f, cfg)


# ── entry point ───────────────────────────────────────────────────────────────

_LOG_MAX_BYTES = 512 * 1024  # 512 KB per file
_LOG_BACKUP_COUNT = 2  # latexmk.log + latexmk.log.1 + latexmk.log.2


def _setup_logging() -> None:
    """Configure a rotating file handler for the root logger.

    Writes to the platform log directory (up to 3 files, 512 KB each).
    Silently skips if the directory cannot be created (e.g., read-only FS).
    """
    log_dir = user_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    log_path = log_dir / "latexmk.log"
    try:
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        return

    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.root.addHandler(handler)
    if logging.root.level == logging.WARNING:
        logging.root.setLevel(logging.DEBUG)


_log = logging.getLogger(__name__)


def _log_invocation() -> None:
    """Emit one DEBUG line describing how latexmk was invoked."""
    _log.debug(
        "invoked: binary=%s cwd=%s args=%r",
        sys.argv[0],
        Path.cwd(),
        sys.argv[1:],
    )


def main() -> None:
    """Parse args, load config, dispatch.

    Mirrors ``main`` in ``latexmk.pl`` (lines ~1-100).
    """
    _setup_logging()
    _log_invocation()
    try:
        _run(sys.argv[1:])
    except BadOptionsError as exc:
        _err(str(exc))
        sys.exit(10)
    except FileMissingError as exc:
        _err(str(exc))
        sys.exit(11)
    except BuildError as exc:
        _err(str(exc))
        sys.exit(12)
    except ConfigError as exc:
        _err(str(exc))
        sys.exit(13)
    except LatexmkError as exc:
        _err(str(exc))
        sys.exit(20)
    except Exception as exc:  # noqa: BLE001
        _err(f"latexmk: internal error: {exc}")
        sys.exit(20)
