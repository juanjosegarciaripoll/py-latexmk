# T02: Configuration System
**Status:** `todo`
**Depends on:** T01

## Goal
Implement `Config` dataclass and TOML loading/merging. Config is the single
source of truth passed everywhere; CLI (T03) maps args onto it.

## Files
- `latexmk_py/config.py`
- `tests/test_config.py`

## Config dataclass

Use nested frozen dataclasses with `slots=True`. Top-level:

```python
@dataclass(slots=True, frozen=True)
class BuildConfig:
    pdf_mode: int = 1
    dvi_mode: int = 0
    postscript_mode: int = 0
    xdv_mode: int = 0
    recorder: bool = True
    max_runs: int = 10
    cd: bool = False
    jobname: str = ""
    latex_extra_options: tuple[str, ...] = ()
    default_files: tuple[str, ...] = ("*.tex",)
    default_excluded_files: tuple[str, ...] = ()

@dataclass(slots=True, frozen=True)
class CommandsConfig:
    latex: str = "latex -interaction=nonstopmode %O %S"
    pdflatex: str = "pdflatex -interaction=nonstopmode %O %S"
    lualatex: str = "lualatex -interaction=nonstopmode %O %S"
    xelatex: str = "xelatex -interaction=nonstopmode %O %S"
    dvilualatex: str = "dvilualatex -interaction=nonstopmode %O %S"
    bibtex: str = "bibtex %O %S"
    biber: str = "biber %O %S"
    makeindex: str = "makeindex %O -o %D %S"
    dvips: str = "dvips %O -o %D %S"
    dvipdf: str = "dvipdf %O %S %D"
    ps2pdf: str = "ps2pdf %O %S %D"
    makeglossaries: str = "makeglossaries %O %B"
    print_pdf: str = ""
    print_ps: str = ""
    print_dvi: str = ""

@dataclass(slots=True, frozen=True)
class DirectoriesConfig:
    aux_dir: str = ""
    out_dir: str = ""
    out2_dir: str = ""
    emulate_aux_dir: bool = True

@dataclass(slots=True, frozen=True)
class BibtexConfig:
    use: float = 1.0   # 0, 1, 1.5, 2
    fudge: bool = True

@dataclass(slots=True, frozen=True)
class PreviewConfig:
    view: str = "default"
    sleep_time: float = 2.0
    timeout_mins: float = 0.0
    new_viewer_always: bool = False
    pdf_previewer: str = "auto"
    dvi_previewer: str = "auto"
    ps_previewer: str = "auto"

@dataclass(slots=True, frozen=True)
class CleanupConfig:
    extra_extensions: tuple[str, ...] = ()
    extra_full_extensions: tuple[str, ...] = ()
    includes_cusdep_generated: bool = False

@dataclass(slots=True, frozen=True)
class DepsConfig:
    enabled: bool = False
    file: str = "-"
    escape: str = "none"
    phony: bool = False

@dataclass(slots=True, frozen=True)
class OutputConfig:
    silent: bool = False
    show_time: bool = False
    max_logfile_warnings: int = 7
    warnings_as_errors: bool = False
    rc_report: bool = True

@dataclass(slots=True, frozen=True)
class CustomDep:
    from_ext: str
    to_ext: str
    must: bool
    command: str

@dataclass(slots=True, frozen=True)
class Config:
    build: BuildConfig = field(default_factory=BuildConfig)
    commands: CommandsConfig = field(default_factory=CommandsConfig)
    directories: DirectoriesConfig = field(default_factory=DirectoriesConfig)
    bibtex: BibtexConfig = field(default_factory=BibtexConfig)
    preview: PreviewConfig = field(default_factory=PreviewConfig)
    cleanup: CleanupConfig = field(default_factory=CleanupConfig)
    deps: DepsConfig = field(default_factory=DepsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    custom_deps: tuple[CustomDep, ...] = ()
    # runtime state (not from TOML; set by CLI)
    force: bool = False
    norc: bool = False
    extra_rc_files: tuple[str, ...] = ()
```

## Loading function

```python
def load_config(
    norc: bool = False,
    extra_rc_files: Sequence[str] = (),
) -> tuple[Config, list[str]]:
    """Load and merge TOML config files.

    Returns (merged Config, list of files actually loaded).
    """
```

Loading order:
1. Start with all-defaults `Config()`
2. Unless `norc`: load system config, then user config, then `./latexmk.toml`/`./.latexmk.toml`
3. Load each file in `extra_rc_files`
4. Return merged config + list of loaded paths (for `-rc-report`)

## Merging

TOML is loaded with `tomllib.load()`. Each TOML section maps directly to the
corresponding sub-dataclass. Unknown keys raise `ConfigError`. Lists become
tuples. `[[custom_dependency]]` becomes `tuple[CustomDep, ...]`.

Merging: for each sub-section, replace individual fields that are explicitly
set in the TOML. Use `dataclasses.replace()`.

## Validation

After merge, validate:
- `pdf_mode` in {0,1,2,3,4,5}
- `dvi_mode` in {0,1,2}
- `bibtex.use` in {0, 1, 1.5, 2}
- `deps.escape` in {"none","unix","nmake"}
- `preview.view` in {"default","pdf","dvi","ps","none"}
- Each `CustomDep`: `from_ext` and `to_ext` non-empty, `command` non-empty

Raise `ConfigError` on failure.

## Checklist
- [ ] `Config()` produces correct defaults
- [ ] TOML round-trip: write TOML, load it, compare
- [ ] Unknown TOML key raises `ConfigError`
- [ ] Invalid enum value raises `ConfigError`
- [ ] Merge order: later file overrides earlier field
- [ ] `[[custom_dependency]]` parsed correctly
- [ ] `uv run pytest tests/test_config.py -q` passes
- [ ] Type-clean (basedpyright + mypy)
