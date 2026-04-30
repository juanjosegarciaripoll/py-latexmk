# Changelog

All notable user-facing changes to this project are documented in this file.

## 0.3.0 — 2026-04-30
- Added `-logfilewarninglist` / `-logfilewarninglist-` as aliases for
  `-logfilewarnings` / `-logfilewarnings-` (latexmk.pl lines 2137–2140).
- Added `-bibtex-min-crossrefs=N` CLI flag and `[bibtex] min_crossrefs`
  TOML key; passes `-min-crossrefs=N` to bibtex (latexmk.pl lines 2200–2205).
- Added `-xdv` / `-xdv-` flags for XDV-only mode: xelatex runs but
  xdvipdfmx is not invoked (latexmk.pl line 1405).

- Added `-p` (print after build) and `-print=WHAT` (dvi/ps/pdf/auto) flags; the
  `[output] print_type` and `[commands] print_pdf/print_ps/print_dvi` TOML keys
  configure the print command. Commands prefixed with `NONE` are skipped with a warning.

- Added `-l` / `-l-` flags for landscape mode; selects `dvips_landscape` command
  and platform-appropriate DVI viewer (`xdvi -paper usr` on Unix).

- CLI now accepts TeX engine passthrough flags (`-synctex`, `-file-line-error`,
  `-shell-escape`, `-max-print-line`, and ~40 others from latexmk.pl lines 549–668)
  and forwards them to `*latex` via `latex_extra_options`.
- Added `-latexoption=OPT` to append arbitrary options to every `*latex` invocation.
- `-showextraoptions` now lists the full passthrough allowlist.
- Log parser unwraps lines at the column specified by the `max_print_line` env var
  (default 79), matching TeXLive behaviour.

## 0.2.4 — 2026-04-29

- Replaced ad-hoc `tools/release.py`, `latexmk.spec`, and `packaging/` with the
  [jj-release](https://github.com/juanjosegarciaripoll/jj-release) reusable workflows.
  The release pipeline now runs CI (lint + type-check + tests on Ubuntu and Windows)
  before building artifacts, then produces a source archive, a Windows relocatable
  binary, and a Windows installer, and publishes a GitHub release — all from a single
  `v*` tag push.

## 0.2.3 — 2026-04-29

## 0.2.2 — 2026-04-29

## 0.2.1 — 2026-04-29

- Added GitHub release automation for version tags (`v*`) with quality gates,
  cross-platform artifact builds, and release asset publishing.
- `--version` now keeps Perl latexmk as the primary version and can append the
  installed Python package version in parentheses.

## v0.1.0 - 2026-04-28

- Reimplemented core `latexmk` behavior in Python 3.13+ with stdlib-only
  runtime dependencies.
- Added full CLI flag coverage with config loading/overrides and dispatch.
- Implemented parsers for `.fls`, `.log`, `.aux`, and `.bcf`.
- Implemented command runner with placeholder expansion (`%S %D %B %R %T %O %Y %Z`).
- Added `.fdb_latexmk` read/write compatibility.
- Implemented rule graph, out-of-date checks, and build convergence loop.
- Added bibliography support for bibtex and biber.
- Added makeindex and glossaries integration.
- Added TOML custom dependency support.
- Added output/aux/out2 directory handling and aux-dir emulation behavior.
- Added cleanup modes (`-c`, `-C`, `-CF`).
- Added DVI/PS/XDV build modes and postprocess flow.
- Added dependency file output (`-M`, `-MF`, `-MP`, `-deps`).
- Added preview support (`-pv`, `-pvc`) with watch/rebuild loop.
- Added integration and differential testing scaffolding.
- Added distribution tooling:
  - PyInstaller one-file builds
  - platform/arch artifact renaming
  - relocatable archives and checksums
  - packaging templates for winget/homebrew/Linux consumption
