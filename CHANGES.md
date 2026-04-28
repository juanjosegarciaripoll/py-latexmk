# Changes

## Unreleased

- T05: Implemented `runner.py` — placeholder expansion (`%S %D %B %R %T %O %Y %Z`) and subprocess execution with shell-operator detection.
- T06: Implemented `fdb.py` — `.fdb_latexmk` read/write in Perl-compatible format (version 4).
- T07: Implemented `rules.py` — `Rule` dataclass, `init_rules` (all pdf/dvi modes), `out_of_date`, `compute_md5`, `topo_sort`.
- T08: Implemented `rdb.py` — `RuleDatabase.build()` with multi-pass convergence loop, `.fls`/`.log` dependency discovery, `.fdb_latexmk` persistence, and `-output-directory` support; verified end-to-end with MiKTeX pdflatex.
- T09: Extended `rdb.py` with automatic bibtex/biber secondary-rule detection; bibtex runs when `.aux` has `\bibdata` and `.bib` is accessible; biber runs when `.bcf` is non-empty; `bibtex.use=0` suppresses both.
- T10: Extended `rdb.py` with makeindex and makeglossaries secondary rules; makeindex fires when `.idx` is produced; makeglossaries fallback fires when `.glo` is produced and no custom dependency covers it.
- T11: Extended `rdb.py` with TOML custom-dependency support; cusdep rules created when `.log` reports a missing file whose source (from-extension) exists; `must=True` raises `FileMissingError` when source is absent.
- T12: Extended `rdb.py` with full directory support: `_setup_dirs` creates `out_dir`/`aux_dir`/`out2_dir` before runs; TeX Live emulation moves aux files from `out_dir` to `aux_dir` after each primary run; `_copy_out2dir` copies output to `out2_dir` on success; `-aux-directory` passed directly when `emulate_aux_dir=False` (MiKTeX).
- T13: Implemented `cleaner.py` — `clean()` for `-c` (intermediate), `-C` (+ final), and `-CF` (fdb only); searches `out_dir`, `aux_dir`, and `tex.parent`; removes cusdep-generated files when `includes_cusdep_generated=True`.
