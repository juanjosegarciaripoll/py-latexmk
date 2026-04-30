"""Config dataclass and TOML loading for latexmk_py.

Config file discovery and merge order mirrors latexmk.pl (lines 1-500 approx.).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from latexmk_py.errors import ConfigError
from latexmk_py.platform import system_config_dir, user_config_dir

if TYPE_CHECKING:
    from collections.abc import Sequence

# ── dataclasses ──────────────────────────────────────────────────────────────


@dataclass(slots=True, frozen=True)
class BuildConfig:
    """Build engine and run-control settings."""

    pdf_mode: int = 1
    dvi_mode: int = 0
    postscript_mode: int = 0
    xdv_mode: int = 0
    recorder: bool = True
    max_runs: int = 10
    cd: bool = False
    jobname: str = ""
    landscape: bool = False
    latex_extra_options: tuple[str, ...] = ()
    default_files: tuple[str, ...] = ("*.tex",)
    default_excluded_files: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class CommandsConfig:
    """Command templates for all tools; placeholders expanded by runner.py."""

    latex: str = "latex -interaction=nonstopmode %O %S"
    pdflatex: str = "pdflatex -interaction=nonstopmode %O %S"
    lualatex: str = "lualatex -interaction=nonstopmode %O %S"
    xelatex: str = "xelatex -interaction=nonstopmode %O %S"
    dvilualatex: str = "dvilualatex -interaction=nonstopmode %O %S"
    bibtex: str = "bibtex %O %S"
    biber: str = "biber %O %S"
    makeindex: str = "makeindex %O -o %D %S"
    dvips: str = "dvips %O -o %D %S"
    dvips_landscape: str = "dvips -tlandscape %O -o %D %S"
    dvipdf: str = "dvipdf %O %S %D"
    ps2pdf: str = "ps2pdf %O %S %D"
    xdvipdfmx: str = "xdvipdfmx -E -o %D %O %S"
    makeglossaries: str = "makeglossaries %O %B"
    print_pdf: str = ""
    print_ps: str = ""
    print_dvi: str = ""


@dataclass(slots=True, frozen=True)
class DirectoriesConfig:
    """Output and auxiliary directory settings."""

    aux_dir: str = ""
    out_dir: str = ""
    out2_dir: str = ""
    emulate_aux_dir: bool = True


@dataclass(slots=True, frozen=True)
class BibtexConfig:
    """BibTeX/Biber invocation settings."""

    use: float = 1.0  # 0, 1, 1.5, 2
    fudge: bool = True
    min_crossrefs: int = 0  # 0 = do not pass -min-crossrefs (use bibtex default)


@dataclass(slots=True, frozen=True)
class PreviewConfig:
    """Viewer and continuous-preview settings."""

    view: str = "default"
    sleep_time: float = 2.0
    timeout_mins: float = 0.0
    new_viewer_always: bool = False
    pdf_previewer: str = "auto"
    dvi_previewer: str = "auto"
    ps_previewer: str = "auto"
    dvi_previewer_landscape: str = "auto"
    ps_previewer_landscape: str = "auto"


@dataclass(slots=True, frozen=True)
class CleanupConfig:
    """Cleanup (-c / -C) extension lists."""

    extra_extensions: tuple[str, ...] = ()
    extra_full_extensions: tuple[str, ...] = ()
    includes_cusdep_generated: bool = False


@dataclass(slots=True, frozen=True)
class DepsConfig:
    """Make-format dependency output settings."""

    enabled: bool = False
    file: str = "-"
    escape: str = "none"
    phony: bool = False


@dataclass(slots=True, frozen=True)
class OutputConfig:
    """Terminal output and logging settings."""

    silent: bool = False
    show_time: bool = False
    max_logfile_warnings: int = 7
    warnings_as_errors: bool = False
    rc_report: bool = True
    print_type: str = "auto"  # "auto" | "dvi" | "ps" | "pdf" | "none"


@dataclass(slots=True, frozen=True)
class CustomDep:
    """A single TOML-declared custom dependency rule."""

    from_ext: str
    to_ext: str
    must: bool
    command: str


@dataclass(slots=True, frozen=True)
class Config:
    """Top-level configuration; single source of truth passed everywhere."""

    build: BuildConfig = field(default_factory=BuildConfig)
    commands: CommandsConfig = field(default_factory=CommandsConfig)
    directories: DirectoriesConfig = field(default_factory=DirectoriesConfig)
    bibtex: BibtexConfig = field(default_factory=BibtexConfig)
    preview: PreviewConfig = field(default_factory=PreviewConfig)
    cleanup: CleanupConfig = field(default_factory=CleanupConfig)
    deps: DepsConfig = field(default_factory=DepsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    custom_deps: tuple[CustomDep, ...] = ()
    # runtime state -- not from TOML; set by CLI
    force: bool = False
    preview_mode: bool = False
    norc: bool = False
    extra_rc_files: tuple[str, ...] = ()


_VALID_TOP: frozenset[str] = frozenset(
    {
        "build",
        "commands",
        "directories",
        "bibtex",
        "preview",
        "cleanup",
        "deps",
        "output",
        "custom_dependency",
    }
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _lists_to_tuples(data: dict[str, object], *keys: str) -> dict[str, object]:
    """Return a copy of *data* with the named fields converted from list to tuple."""
    result = dict(data)
    for k in keys:
        v = result.get(k)
        if v is None:
            continue
        if not isinstance(v, list):
            raise ConfigError(f"latexmk: {k} must be a list, got {type(v).__name__}")
        result[k] = tuple(cast("list[object]", v))
    return result


def _merge_raw(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Merge two raw TOML dicts; section-level fields from *override* win.

    ``[[custom_dependency]]`` entries are accumulated across files.
    """
    result: dict[str, object] = dict(base)
    for k, v in override.items():
        existing = result.get(k)
        if k == "custom_dependency" and isinstance(v, list) and isinstance(existing, list):
            result[k] = cast("list[object]", existing) + cast("list[object]", v)
        elif isinstance(v, dict) and isinstance(existing, dict):
            # section-level merge: only override the keys present in the new file
            result[k] = {**cast("dict[str, object]", existing), **cast("dict[str, object]", v)}
        else:
            result[k] = v
    return result


def _build_custom_deps(entries: list[object]) -> tuple[CustomDep, ...]:
    result: list[CustomDep] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"latexmk: [[custom_dependency]][{i}] must be a table")
        d = cast("dict[str, object]", entry)
        bad = set(d) - {"from", "to", "must", "command"}
        if bad:
            raise ConfigError(
                f"latexmk: unknown key(s) in [[custom_dependency]][{i}]: {', '.join(sorted(bad))}"
            )
        try:
            result.append(
                CustomDep(
                    from_ext=str(d["from"]),
                    to_ext=str(d["to"]),
                    must=bool(d.get("must", False)),
                    command=str(d["command"]),
                )
            )
        except KeyError as exc:
            raise ConfigError(
                f"latexmk: [[custom_dependency]][{i}] missing required key {exc}"
            ) from exc
    return tuple(result)


def _section(raw: dict[str, object], name: str) -> dict[str, object]:
    v = raw.get(name, {})
    if not isinstance(v, dict):
        raise ConfigError(f"latexmk: [{name}] must be a table")
    return cast("dict[str, object]", v)


def _config_from_raw(raw: dict[str, object]) -> Config:
    bad = set(raw) - _VALID_TOP
    if bad:
        raise ConfigError(f"latexmk: unknown top-level section(s): {', '.join(sorted(bad))}")

    bd = _lists_to_tuples(
        _section(raw, "build"),
        "latex_extra_options",
        "default_files",
        "default_excluded_files",
    )
    cm = _section(raw, "commands")
    dr = _section(raw, "directories")
    bt = dict(_section(raw, "bibtex"))
    if "use" in bt:
        bt["use"] = float(bt["use"])  # type: ignore[arg-type]  # TOML int for 0/1/2 must become float
    pv = _section(raw, "preview")
    cl = _lists_to_tuples(
        _section(raw, "cleanup"),
        "extra_extensions",
        "extra_full_extensions",
    )
    dp = _section(raw, "deps")
    op = _section(raw, "output")

    raw_deps = raw.get("custom_dependency", [])
    if not isinstance(raw_deps, list):
        raise ConfigError("latexmk: custom_dependency must be an array of tables")
    custom_deps = _build_custom_deps(cast("list[object]", raw_deps))

    try:
        cfg = Config(
            build=BuildConfig(**bd),  # type: ignore[arg-type]
            commands=CommandsConfig(**cm),  # type: ignore[arg-type]
            directories=DirectoriesConfig(**dr),  # type: ignore[arg-type]
            bibtex=BibtexConfig(**bt),  # type: ignore[arg-type]
            preview=PreviewConfig(**pv),  # type: ignore[arg-type]
            cleanup=CleanupConfig(**cl),  # type: ignore[arg-type]
            deps=DepsConfig(**dp),  # type: ignore[arg-type]
            output=OutputConfig(**op),  # type: ignore[arg-type]
            custom_deps=custom_deps,
        )
    except TypeError as exc:
        raise ConfigError(f"latexmk: unknown key: {exc}") from exc
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if cfg.build.pdf_mode not in {0, 1, 2, 3, 4, 5}:
        raise ConfigError(f"latexmk: build.pdf_mode must be 0-5, got {cfg.build.pdf_mode}")
    if cfg.build.dvi_mode not in {0, 1, 2}:
        raise ConfigError(f"latexmk: build.dvi_mode must be 0-2, got {cfg.build.dvi_mode}")
    if cfg.bibtex.use not in {0, 1, 1.5, 2}:
        raise ConfigError(f"latexmk: bibtex.use must be 0/1/1.5/2, got {cfg.bibtex.use}")
    if cfg.deps.escape not in {"none", "unix", "nmake"}:
        raise ConfigError(f"latexmk: deps.escape must be none/unix/nmake, got {cfg.deps.escape!r}")
    if cfg.preview.view not in {"default", "pdf", "dvi", "ps", "none"}:
        raise ConfigError(
            f"latexmk: preview.view must be default/pdf/dvi/ps/none, got {cfg.preview.view!r}"
        )
    if cfg.output.print_type not in {"auto", "dvi", "ps", "pdf", "none"}:
        raise ConfigError(
            f"latexmk: output.print_type must be auto/dvi/ps/pdf/none,"
            f" got {cfg.output.print_type!r}"
        )
    for cd in cfg.custom_deps:
        if not cd.from_ext or not cd.to_ext or not cd.command:
            raise ConfigError(
                "latexmk: custom_dependency fields 'from', 'to', and 'command' must be non-empty"
            )


def _load_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except OSError as exc:
        raise ConfigError(f"latexmk: cannot read {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"latexmk: invalid TOML in {path}: {exc}") from exc


# ── public API ────────────────────────────────────────────────────────────────


def load_config(
    *,
    norc: bool = False,
    extra_rc_files: Sequence[str] = (),
) -> tuple[Config, list[str]]:
    """Load and merge TOML config files.

    Returns (merged Config, list of files actually loaded).
    Mirrors config file discovery in latexmk.pl (lines ~200-350).
    """
    raw: dict[str, object] = {}
    loaded: list[str] = []

    if not norc:
        sys_override = os.environ.get("LATEXMKRCSYS")
        system = Path(sys_override) if sys_override else system_config_dir() / "config.toml"
        candidates: list[Path] = [
            system,
            user_config_dir() / "config.toml",
            Path("latexmk.toml"),
            Path(".latexmk.toml"),
        ]
        for path in candidates:
            if path.is_file():
                raw = _merge_raw(raw, _load_toml(path))
                loaded.append(str(path))

    for rc in extra_rc_files:
        path = Path(rc)
        raw = _merge_raw(raw, _load_toml(path))
        loaded.append(str(path))

    cfg = _config_from_raw(raw)
    return replace(cfg, norc=norc, extra_rc_files=tuple(extra_rc_files)), loaded
