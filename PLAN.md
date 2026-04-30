# PLAN.md — Python latexmk

Ref: latexmk 4.88 (2026-03-09). Python 3.13+, stdlib only, no runtime deps.
Goal: portable CLI for Linux/macOS/Windows, works with VS Code LaTeX Workshop,
TeXstudio, TeXShop, AUCTeX, vimtex.

Detailed specs live in `ai/`. Read the relevant task file before implementing.

## Dropped features

| Feature | Replacement |
|---|---|
| Programmable `.latexmkrc` (Perl eval) | TOML config only (`ai/config-schema.md`) |
| `-e CODE` / exec-style `-r FILE` | `-r FILE` loads TOML only |
| `add_cus_dep` subroutines | TOML `[[custom_dependency]]` |
| Banner overlay (`-bm -bi -bs -d -dF -pF`) | external tools |
| Cygwin/MSYS special-casing | POSIX or Win32 |
| `Win32::GetACP` codepage conversions | UTF-8 everywhere |
| `-use-make` | rarely used |

## Layout

Standard `src/` layout — the installable package lives under `src/`, not at the repo root.

```
src/latexmk_py/
  __init__.py, __main__.py
  cli.py          argparse → Config; dispatch        (T03)
  config.py       Config dataclass, TOML merge       (T02)
  rules.py        Rule dataclass, init_rules()       (T07)
  rdb.py          RuleDatabase, build(), watch()     (T08–T11)
  runner.py       placeholder expansion, subprocess  (T05)
  parsers/        fls.py  log.py  aux.py  bcf.py     (T04)
  fdb.py          .fdb_latexmk read/write            (T06)
  cleaner.py      -c / -C                            (T13)
  viewer.py       -pv / -pvc                         (T16)
  deps.py         -M / -MF / -deps                   (T15)
  errors.py                                          (T01 ✓)
  platform.py                                        (T01 ✓)
tests/
  conftest.py
  fixtures/       simple/ biblatex/ bibtex/ makeindex/ glossaries/ multichapter/ logs/
  test_*.py
  integration/    test_*.py  known_divergences.py    (T17)
tools/                                               (T18 — does not exist yet)
  release.py      release artifact builder
packaging/                                           (T18)
  winget/         local manifest templates
latexmk.spec      PyInstaller spec                   (T18)
latexmk/          Perl reference (READ-ONLY)
```

## Configuration

Full schema: `ai/config-schema.md`. Implementation: `ai/T02-config.md`.

TOML (`tomllib` stdlib). Merge order (later overrides):
1. System: `/etc/latexmk/config.toml` | `%ProgramData%\latexmk\config.toml`
2. User: `$XDG_CONFIG_HOME/latexmk/config.toml` | `%APPDATA%\latexmk\config.toml`
3. Project: `./latexmk.toml` or `./.latexmk.toml`
4. CLI: `-r FILE` (TOML)

`-norc` skips 1–3. CLI flags override all.

## CLI Flags

Full flag list with Config mapping: `ai/T03-cli.md`.

Groups: output format · engine commands · file/directory · bibtex/biber ·
processing control · preview · cleanup · dependency output · config control ·
diagnostics.

Key flags for editor compatibility (LaTeX Workshop):
```
latexmk -pdf -interaction=nonstopmode -file-line-error -synctex=1 -outdir=DIR FILE
latexmk -pvc -pdf -interaction=nonstopmode -synctex=1 -outdir=DIR FILE
```
`-file-line-error` passes through to *latex via `%O` unchanged.

## Build Algorithm

Full pseudocode and details: `ai/T08-build-loop.md`.

### Rule kinds
- `primary`: latex / pdflatex / lualatex / xelatex / dvilualatex  (T08, T14)
- `secondary`: bibtex / biber / makeindex  (T09, T10)
- `postprocess`: dvips / dvipdf / ps2pdf  (T14)
- `cusdep`: TOML-declared  (T11)

### Out-of-date conditions
1. Never run
2. Source MD5 changed
3. Source disappeared
4. Dest missing or MD5 changed
5. A rule generating this rule's source is out-of-date
6. Force flag

### Dependency discovery after each primary run
`.fls` (INPUT/OUTPUT lines, primary) + `.log` (Rerun signal, always) +
`.aux` (`\bibdata`, `\@input`) + `.bcf` (biber sources).
See `ai/T04-parsers.md` for parser specs including exact regexes.

### Secondary rule triggers
| Condition | Rule |
|---|---|
| `.aux` has `\bibdata` + `.bib` reachable | bibtex (T09) |
| `.bcf` non-empty | biber (T09) |
| `.idx` exists | makeindex (T10) |
| `.glo` exists + no cusdep configured | makeglossaries fallback (T10) |
| *latex missing-file + matching cusdep `from` file exists | cusdep (T11) |

### -pvc loop
```
build(); open_viewer()
loop: sleep → stat sources → MD5 confirm → rebuild + refresh
      SIGINT → exit cleanly; timeout → exit
```
See `ai/T16-preview-pvc.md`.

## Placeholder Tokens

Full table and expansion rules: `ai/T05-runner.md`.
`%S %D %B %R %T %O %Y %Z` — expanded in `runner.py`, then
`shlex.split` → `subprocess.run(..., shell=False)`.
Exception: `|`/`&&`/`;` in command → `shell=True`.

## .fdb_latexmk Format

Binary-compatible with Perl latexmk 4.88. Full grammar: `ai/T06-fdb.md`.

## Exit Codes

0=success · 10=bad options · 11=missing file · 12=build error ·
13=config error · 20=internal. Prefix: `latexmk: <msg>`.

## Editor Compatibility

LaTeX Workshop, TeXstudio, AUCTeX, vimtex all work with standard flags and
exit codes. TeXstudio reads `.fdb_latexmk`; needs exact format.

## Distribution

Release automation is tag-driven (`v*`) and builds:
- Windows prebuilt executable artifacts (`latexmk.exe`) plus checksums
- generated winget manifests (release-engineering artifacts)
- source tarball (sdist)

Details: `ai/T18-distribution.md`.
End-user Windows install guidance is direct download of prebuilt binaries from
GitHub Releases. Source-install fallback remains supported.

## Modules

| Module | Responsibility | Task |
|---|---|---|
| `cli.py` | argparse → Config; dispatch | T03 |
| `config.py` | Config dataclass; TOML merge | T02 |
| `rules.py` | Rule dataclass; init_rules() | T07 |
| `rdb.py` | build(); watch(); convergence | T08–T11 |
| `runner.py` | placeholder expand; subprocess | T05 |
| `parsers/` | fls / log / aux / bcf parsers | T04 |
| `fdb.py` | read_fdb(); write_fdb() | T06 |
| `cleaner.py` | clean(mode) | T13 |
| `viewer.py` | open_viewer(); viewer_running() | T16 |
| `deps.py` | write_deps() make-format | T15 |
| `errors.py` | exception hierarchy | T01 |
| `platform.py` | is_windows(), default_viewer() | T01 |

## Tasks (priority order)

| # | Task | Status |
|---|---|---|
| T01 | Project scaffold (pyproject, errors, platform) | `done` |
| T02 | Config system (TOML loading, Config dataclass) | `done` |
| T03 | CLI / argparse (all flags, dispatch) | `done` |
| T04 | Parsers (fls, log, aux, bcf) | `done` |
| T05 | Runner (placeholder expansion, subprocess) | `done` |
| T06 | FDB read/write | `done` |
| T07 | Rule engine (Rule dataclass, out-of-date, topo-sort) | `done` |
| T08 | Primary build loop (pdflatex / lualatex / xelatex) | `done` |
| T09 | Bibliography (bibtex + biber) | `done` |
| T10 | Makeindex & glossaries | `done` |
| T11 | Custom dependencies (TOML cusdep) | `done` |
| T12 | Output & aux directories | `done` |
| T13 | Cleanup (-c, -C, -CF) | `done` |
| T14 | DVI / PS modes | `done` |
| T15 | Dependency output (-M, -deps) | `done` |
| T16 | Preview & -pvc | `done` |
| T17 | Integration tests | `done` |
| T18 | Release distribution (Windows binaries + release automation) | `done` |
| T19 | TeX engine passthrough options + `-latexoption` + `-showextraoptions` | `done` |
| T20 | Landscape mode (`-l`) | `done` |
| T21 | Print support (`-p`, `-print`) | `done` |
| T22 | Small missing options (warning aliases, bibtex crossrefs, XDV mode) | `done` |

