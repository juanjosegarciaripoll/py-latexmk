# Changelog

All notable user-facing changes to this project are documented in this file.

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
