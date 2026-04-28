# latexmk (Python port)

`latexmk` automates LaTeX builds by running the required tools until outputs
converge (for example: `pdflatex`, `bibtex`/`biber`, `makeindex`, and related
post-processing).

This document describes the Python port in this repository.

## Compatibility goals

- Keep user-visible behavior close to Perl `latexmk`.
- Preserve stable exit codes and diagnostics prefixed with `latexmk:`.
- Keep `.fdb_latexmk` compatibility for editor/tool integration.

## Common usage

```bash
latexmk -pdf main.tex
latexmk -pvc -pdf main.tex
latexmk -c main.tex
latexmk -C main.tex
```

## Important option groups

### Output format

- `-pdf`, `-pdfdvi`, `-pdflua`, `-pdfxe`, `-pdf-`
- `-dvi`, `-dvi-`, `-dvilua`
- `-ps`, `-ps-`
- `-output-format=pdf|dvi|ps|dvilua|pdfxe`

### Engine command overrides

- `-latex[=CMD]`, `-pdflatex[=CMD]`, `-lualatex[=CMD]`, `-xelatex[=CMD]`
- `-bibtex[=CMD]`, `-biber[=CMD]`
- `-stdtexcmds`

### Directories

- `-auxdir=D`, `-aux-directory=D`
- `-outdir=D`, `-output-directory=D`
- `-out2dir=D`
- `-cd`, `-cd-`
- `-emulate-aux-dir`, `-emulate-aux-dir-`

### Bibliography and indexing

- `-bibtex`, `-bibtex-`, `-nobibtex`
- `-bibtex-cond`, `-bibtex-cond1`
- `-biber`

### Build control

- `-f`, `-f-`
- `-g`, `-g-`, `-gg`, `-gt`
- `-recorder`, `-recorder-`
- `-interaction=MODE`

### Preview

- `-pv`
- `-pvc`, `-pvc-`
- `-view=WHAT`
- `-pvctimeoutmins=N`
- `-new-viewer`, `-new-viewer-`

### Cleanup

- `-c` (intermediate generated files)
- `-C` / `-CA` (more complete cleanup)
- `-CF` (`.fdb_latexmk`)

### Dependency output

- `-M`, `-MF FILE`, `-MP`
- `-deps`, `-deps-`
- `-deps-out=FILE`
- `-deps-escape=none|unix|nmake`

### Config and diagnostics

- `-norc`, `-r FILE`
- `-help`, `-version`, `-commands`
- `-dir-report`, `-dir-report-only`
- `-diagnostics`
- `-quiet`, `-silent`

## Configuration model

Configuration is TOML-only (no Perl code execution).

Merge order (later overrides earlier):

1. System config
2. User config
3. Project config
4. CLI `-r FILE` config

`-norc` skips steps 1–3.

## Exit codes

- `0`: success
- `10`: bad options
- `11`: missing file
- `12`: build error
- `13`: config error
- `20`: internal error

## Key files

- `latexmk.toml` / `.latexmk.toml`: project config
- `.fdb_latexmk`: build state database
- `*.fls`, `*.log`, `*.aux`, `*.bcf`: dependency/rerun detection inputs

## Differences from Perl latexmk

- No programmable `.latexmkrc` Perl evaluation.
- No `-e CODE` execution mode.
- No fallback to running Perl `latexmk.pl`.

## Licensing and attribution

This project is GPL-2.0 licensed.
The man page in `docs/latexmk.1` is adapted from upstream `latexmk`
documentation with attribution.
