# Changes

## Unreleased

- T05: Implemented `runner.py` — placeholder expansion (`%S %D %B %R %T %O %Y %Z`) and subprocess execution with shell-operator detection.
- T06: Implemented `fdb.py` — `.fdb_latexmk` read/write in Perl-compatible format (version 4).
- T07: Implemented `rules.py` — `Rule` dataclass, `init_rules` (all pdf/dvi modes), `out_of_date`, `compute_md5`, `topo_sort`.
- T08: Implemented `rdb.py` — `RuleDatabase.build()` with multi-pass convergence loop, `.fls`/`.log` dependency discovery, `.fdb_latexmk` persistence, and `-output-directory` support; verified end-to-end with MiKTeX pdflatex.
- T09: Extended `rdb.py` with automatic bibtex/biber secondary-rule detection; bibtex runs when `.aux` has `\bibdata` and `.bib` is accessible; biber runs when `.bcf` is non-empty; `bibtex.use=0` suppresses both.
- T10: Extended `rdb.py` with makeindex and makeglossaries secondary rules; makeindex fires when `.idx` is produced; makeglossaries fallback fires when `.glo` is produced and no custom dependency covers it.
