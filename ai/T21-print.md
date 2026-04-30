# T21: Print Support (-p, -print)
**Status:** `done`
**Depends on:** T19

## Goal

Implement `-p` (print after build) and `-print=WHAT` (choose what to print).
Mirrors `$printout_mode` / `$print_type` / `$lpr*` in `latexmk.pl`
(lines 770–773, 2226–2235, 3635–3650).

## Behaviour

- `-p` enables printing; `-print=WHAT` sets what: `dvi | ps | pdf | auto`.
- `auto` (default) resolves at build time: ps > pdf > dvi, whichever mode is active.
- After a successful build the appropriate print command is run once.
- Print command receives the final output file via `%S`; `%O` is empty by default.
- If the resolved command starts with `NONE`, emit a warning and skip (matches Perl).
- `-p` is silently accepted even when no print command is configured (Perl warns at runtime).

## Changes

### `src/latexmk_py/config.py`

`CommandsConfig` already has `print_pdf`, `print_ps`, `print_dvi` (all `""`).
Change defaults to match Perl platform defaults:

```python
@dataclass(slots=True, frozen=True)
class CommandsConfig:
    ...
    # Printing — empty means "not configured"; NONE prefix means unsupported.
    print_pdf: str = ""   # Unix: e.g. "lpr %O %S" — left to user config
    print_ps:  str = ""
    print_dvi: str = ""
```

Add to `OutputConfig` (or a new `PrintConfig`):
```python
print_type: str = "auto"   # "auto" | "dvi" | "ps" | "pdf" | "none"
```

### `src/latexmk_py/cli.py`

`_Flags` already has `print_mode` and `print_what`.  Wire them:

In `_parse()`, `-print=` already sets `flags.print_what`.
After parsing, resolve `cfg.output.print_type = flags.print_what` when
`flags.print_mode` is True.

Add a `_run_print()` helper called from `_run()` after a successful build when
`flags.print_mode`:

```python
def _run_print(tex_files: list[Path], cfg: Config) -> None:
    for f in tex_files:
        _print_file(f, cfg)
```

### `src/latexmk_py/printer.py` (new file)

```python
"""Print support — invoke lpr/lpr_pdf/lpr_dvi after a successful build."""

from __future__ import annotations
from pathlib import Path
from latexmk_py.config import Config
from latexmk_py.runner import run_command

def print_output(tex: Path, cfg: Config) -> int:
    """Run the configured print command for the current output mode.

    Returns the subprocess return code (0 = success).
    Mirrors do_one_tex_file print logic in latexmk.pl (lines 3635-3650).
    """
    ptype = _resolve_type(cfg)
    if ptype == "none":
        return 0
    cmd, output_file = _resolve_cmd_and_file(tex, cfg, ptype)
    if not cmd or cmd.startswith("NONE"):
        import logging
        logging.warning("latexmk: print command not configured for type %r", ptype)
        return 0
    return run_command(cmd, source=output_file, dest=output_file, cfg=cfg)

def _resolve_type(cfg: Config) -> str:
    ptype = cfg.output.print_type
    if ptype != "auto":
        return ptype
    if cfg.build.postscript_mode:   return "ps"
    if cfg.build.pdf_mode:          return "pdf"
    if cfg.build.dvi_mode:          return "dvi"
    return "none"

def _resolve_cmd_and_file(tex: Path, cfg: Config, ptype: str) -> tuple[str, Path]:
    stem = tex.stem
    match ptype:
        case "pdf":  return cfg.commands.print_pdf, tex.with_suffix(".pdf")
        case "ps":   return cfg.commands.print_ps,  tex.with_suffix(".ps")
        case "dvi":  return cfg.commands.print_dvi, tex.with_suffix(".dvi")
        case _:      return "", tex
```

Adapt `run_command` signature if needed, or use `runner.expand_cmd` +
`subprocess.run` directly — follow the pattern already used in `rdb.py`.

### `src/latexmk_py/cli.py` — dispatch

In `_run()`, after the build succeeds and when `flags.print_mode`:
```python
if flags.print_mode:
    from latexmk_py.printer import print_output
    for f in tex_files:
        print_output(f, cfg)
```

### TOML config keys

Map in `config.py`:
- `[output] print_type = "auto"`
- `[commands] print_pdf = "lpr %O %S"` etc.

### Help text

Update `_HELP`:
```
  -p                 Print after build
  -print=WHAT        dvi/ps/pdf/auto (default: auto)
```

## Tests

`tests/test_printer.py`:
- `_resolve_type` returns correct type for each mode combination
- when cmd is `""` or `"NONE..."`, returns 0 and emits a warning
- TOML `[output] print_type = "pdf"` is loaded

## Checklist
- [ ] `output.print_type` config field; default `"auto"`
- [ ] `-p` flag triggers print; `-print=WHAT` sets type
- [ ] `printer.py` resolves type and runs command
- [ ] `NONE`-prefixed commands are skipped with a warning
- [ ] TOML keys loaded for `print_type` and `print_*` commands
- [ ] Help text updated
- [ ] Tests pass; type-clean
