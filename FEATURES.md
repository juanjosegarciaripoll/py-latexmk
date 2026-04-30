# Feature Comparison: py-latexmk vs latexmk.pl

Comparison of the Python reimplementation against the reference Perl script
(`latexmk/latexmk.pl`).  Status codes: **YES** = fully implemented, **PARTIAL** =
works but incomplete, **NO** = not implemented.

---

## 1. CLI Options

### Output Format

| Option | Status | Notes |
|--------|--------|-------|
| `-pdf` | YES | pdflatex path |
| `-pdfdvi` | YES | latex → dvipdf |
| `-pdflua` / `-pdflualatex` | YES | lualatex |
| `-pdfxe` / `-pdfxelatex` | YES | xelatex + xdvipdfmx |
| `-pdf-` | YES | disable PDF output |
| `-dvi` / `-dvi-` | YES | DVI mode on/off |
| `-dvilua` | YES | DVI via lualatex |
| `-ps` / `-ps-` | YES | PostScript mode on/off |
| `-output-format=F` | PARTIAL | `pdf/dvi/ps/dvilua/pdfxe` — `pdfxe` missing |

### Engine Commands

| Option | Status | Notes |
|--------|--------|-------|
| `-latex[=CMD]` | YES | |
| `-pdflatex[=CMD]` | YES | |
| `-lualatex[=CMD]` | YES | |
| `-xelatex[=CMD]` | YES | |
| `-bibtex[=CMD]` | YES | |
| `-biber[=CMD]` | YES | |
| `-stdtexcmds` | YES | resets all commands to defaults |
| **`-latexoption=OPT`** | **NO** | appends OPT to all `*latex` command strings |

### Directories

| Option | Status |
|--------|--------|
| `-auxdir` / `-aux-directory` | YES |
| `-outdir` / `-output-directory` | YES |
| `-out2dir` | YES |
| `-cd` / `-cd-` | YES |
| `-jobname` | YES |
| `-emulate-aux-dir` / `-emulate-aux-dir-` | YES |

### BibTeX / Biber

| Option | Status |
|--------|--------|
| `-bibtex` / `-bibtex-` / `-nobibtex` | YES |
| `-bibtex-cond` / `-bibtex-cond1` | YES |
| `-bibtexfudge` / `-bibtexfudge-` / `-nobibtexfudge` | YES |

### Processing Control

| Option | Status | Notes |
|--------|--------|-------|
| `-f` / `-f-` | YES | force rebuild |
| `-g` / `-g-` | YES | force rerun |
| `-gg` | YES | clean then rebuild |
| `-gt` | YES | regenerate all outputs |
| `-recorder` / `-recorder-` | YES | |
| `-interaction=MODE` | YES | passed through to `*latex` |
| `-pretex=CODE` / `-usepretex[=CODE]` | YES | |

### TeX Engine Passthrough Options

In Perl latexmk, options in this list are forwarded to `*latex` as-is.  In
py-latexmk **every unrecognised option raises `BadOptionsError`** — none of
these are accepted.

**TeXLive options not yet accepted by py-latexmk:**

| Option | Description |
|--------|-------------|
| `-cnf-line=STRING` | parse STRING as a configuration file line |
| `-draftmode` | draft mode (no output PDF) |
| `-enc` | enable encTeX |
| `-etex` | enable e-TeX extensions |
| `-file-line-error` / `-no-file-line-error` | file:line:error style messages |
| `-fmt=FMTNAME` | use alternate format file |
| `-halt-on-error` | stop at first error |
| `-ipc` / `-ipc-start` | send DVI to socket |
| `-kpathsea-debug=NUMBER` | kpathsea debug flags |
| `-mktex=FMT` / `-no-mktex=FMT` | mktex generation control |
| `-mltex` | MLTeX extensions |
| `-output-comment=STRING` | DVI file comment |
| `-parse-first-line` / `-no-parse-first-line` | first-line parsing |
| `-progname=STRING` | set program/format name |
| `-shell-escape` / `-no-shell-escape` / `-shell-restricted` | shell escape |
| `-src-specials[=WHERE]` | insert source specials |
| **`-synctex=NUMBER`** | generate SyncTeX data |
| `-translate-file=TCXNAME` | TCX file |
| `-8bit` | make all characters printable |

**MiKTeX options not yet accepted by py-latexmk:**

| Option | Description |
|--------|-------------|
| `-alias=app` | pretend to be app |
| `-buf-size=n` | character buffer size |
| `-c-style-errors` / `-no-c-style-errors` | C-style error messages |
| `-disable-installer` / `-enable-installer` | package auto-install |
| `-disable-pipes` / `-enable-pipes` | child process I/O |
| `-disable-write18` / `-enable-write18` / `-restrict-write18` | write18 control |
| `-dont-parse-first-line` | disable first-line check |
| `-enable-enctex` / `-enable-mltex` | TeX extensions |
| `-error-line=n` | context line width |
| `-extra-mem-bot=n` / `-extra-mem-top=n` | extra memory |
| `-font-max=n` / `-font-mem-size=n` | font memory limits |
| `-half-error-line=n` | first context line width |
| `-hash-extra=n` | hash table extra space |
| `-job-time=file` | output file timestamp |
| `-main-memory=n` | main memory size |
| `-max-in-open=n` | max simultaneous input files |
| **`-max-print-line=n`** | width of log output lines |
| `-max-strings=n` | maximum string count |
| `-nest-size=n` | semantic nesting depth |
| `-param-size=n` | macro parameter space |
| `-pool-size=n` | string pool size |
| `-record-package-usages=file` | package usage recording |
| `-save-size=n` | group save space |
| `-stack-size=n` | simultaneous input sources |
| `-string-vacancies=n` | string vacancies |
| `-tcx=name` | TCX table |
| `-time-statistics` | processing time statistics |
| `-trace[=tracestreams]` | trace messages |
| `-trie-size=n` | hyphenation pattern space |
| `-undump=name` | format name |

**Workaround:** any of the above can be injected today via
`latex_extra_options` in `latexmk.toml` or via a command-string override.

### Preview / Print

| Option | Status | Notes |
|--------|--------|-------|
| `-pv` | YES | open viewer after build |
| `-pvc` / `-pvc-` | YES | continuous preview |
| `-view=WHAT` | YES | `default/pdf/dvi/ps/none` |
| `-pvctimeout` / `-pvctimeoutmins=N` | YES | |
| `-new-viewer` / `-new-viewer-` | YES | |
| `-p` | NO | print after build |
| `-print=WHAT` | NO | `dvi/ps/pdf` |

### Cleanup

| Option | Status |
|--------|--------|
| `-c` | YES |
| `-C` / `-CA` | YES |
| `-CF` | YES |

### Dependency Output

| Option | Status |
|--------|--------|
| `-deps` / `-deps-` | YES |
| `-deps-out=F` | YES |
| `-deps-escape=K` | YES |
| `-M` / `-MF F` / `-MP` | YES |

### Miscellaneous / Less-Used Options

| Option | Status | Notes |
|--------|--------|-------|
| `-norc` | YES | |
| `-r FILE` | YES | extra TOML config |
| `-h` / `-help` | YES | |
| `-v` / `-version` | YES | |
| `-commands` | YES | |
| `-diagnostics` | YES | |
| `-dir-report` / `-dir-report-only` | YES | |
| `-time` / `-time-` | YES | |
| `-rc-report` / `-rc-report-` | YES | |
| `-rules` / `-rules-` | YES | |
| `-quiet` / `-silent` | YES | |
| `-logfilewarnings` | YES | |
| `-Werror` | YES | |
| `-showextraoptions` | PARTIAL | prints stub; lists no options |
| `-l` / `-l-` | NO | landscape mode |
| `-hnt` | NO | HNT/HINT output mode |
| `-e CODE` | NO | execute Perl/config code |
| `-use-make` / `-use-make-` | NO | use make for missing files |
| `-logfilewarninglist` / `-logfilewarninglist-` | NO | filter warning list |
| `-bibtex-min-crossrefs` | NO | bibtex crossref threshold |
| `-dvi-filter=F` / `-ps-filter=F` | NO | pipe DVI/PS through filter |
| `-kpsewhich-show` | NO | show kpsewhich lookups |

---

## 2. Configuration Variables

### Build

| Variable | Status |
|----------|--------|
| `pdf_mode` (0–5) | YES |
| `dvi_mode` (0–2) | YES |
| `postscript_mode` | YES |
| `xdv_mode` | NO |
| `max_runs` | YES |
| `cd` | YES |
| `jobname` | YES |
| `latex_extra_options` | YES |
| `default_files` | YES |
| `default_excluded_files` | YES |
| `recorder` | YES |

### Commands

| Variable | Status |
|----------|--------|
| `latex`, `pdflatex`, `lualatex`, `xelatex`, `dvilualatex` | YES |
| `bibtex`, `biber` | YES |
| `makeindex` | YES |
| `dvips`, `dvipdf`, `ps2pdf`, `xdvipdfmx` | YES |
| `makeglossaries` | YES |
| `print_pdf`, `print_ps`, `print_dvi` | NO |

### Directories

| Variable | Status |
|----------|--------|
| `aux_dir` | YES |
| `out_dir` | YES |
| `out2_dir` | YES |
| `emulate_aux_dir` | YES |

### BibTeX / Biber

| Variable | Status |
|----------|--------|
| `bibtex.use` (0 / 1 / 1.5 / 2) | YES |
| `bibtex.fudge` | YES |
| `bibtex_min_crossrefs` | NO |

### Preview

| Variable | Status |
|----------|--------|
| `view` | YES |
| `sleep_time` | YES |
| `timeout_mins` | YES |
| `new_viewer_always` | YES |
| `pdf_previewer`, `dvi_previewer`, `ps_previewer` | YES |

### Cleanup

| Variable | Status |
|----------|--------|
| `extra_extensions` | YES |
| `extra_full_extensions` | YES |
| `includes_cusdep_generated` | YES |

### Dependency Output

| Variable | Status |
|----------|--------|
| `enabled`, `file`, `escape`, `phony` | YES |

### Output / Diagnostics

| Variable | Status |
|----------|--------|
| `silent`, `show_time`, `rc_report` | YES |
| `max_logfile_warnings`, `warnings_as_errors` | YES |

### Hooks / Callbacks

| Variable | Status | Notes |
|----------|--------|-------|
| Perl hook arrays (`@PRE_TEX`, `@TEX`, etc.) | NO | Intentional: config is TOML-only |

---

## 3. Build Rules / Tools

| Tool | Status | Notes |
|------|--------|-------|
| pdflatex | YES | |
| lualatex | YES | |
| xelatex | YES | |
| latex (DVI mode) | YES | |
| dvilualatex | YES | |
| bibtex | YES | |
| biber | YES | |
| makeindex | YES | |
| dvips | YES | |
| dvipdf | YES | |
| ps2pdf | YES | |
| xdvipdfmx | YES | |
| makeglossaries | YES | fallback rule |
| Print commands | NO | infrastructure absent |

### Custom Dependencies

| Feature | Status |
|---------|--------|
| `[[custom_dependency]]` TOML sections | YES |
| `from` / `to` extension matching | YES |
| Command template tokens (`%S %D %B %O %Y %Z %R %T`) | YES |
| `must` (always-run) field | YES |
| Cleanup of generated files | YES |

---

## 4. Major Features

### Dependency Tracking

| Feature | Status |
|---------|--------|
| `.fls` parsing (file recorder) | YES |
| `.log` parsing | YES |
| `.aux` parsing | YES |
| `.bcf` parsing (Biber) | YES |
| `.fdb_latexmk` read/write (version 4) | YES |
| MD5-based change detection | YES |
| Incremental rebuilds | YES |

### Continuous / Watch Mode (`-pvc`)

| Feature | Status |
|---------|--------|
| File-change polling | YES |
| Rebuild on change | YES |
| Timeout (`-pvctimeoutmins`) | YES |
| Convergence detection | YES |

### Viewer Launch (`-pv`, `-pvc`)

| Feature | Status |
|---------|--------|
| Platform-aware auto-detect | YES |
| Reuse existing viewer | YES |
| Multiple format support (PDF/DVI/PS) | YES |

### Clean Mode

| Feature | Status |
|---------|--------|
| `-c` intermediate files | YES |
| `-C` all generated files | YES |
| `-CF` fdb only | YES |
| Custom extension lists | YES |

### SyncTeX

| Feature | Status | Notes |
|---------|--------|-------|
| `.synctex.gz` tracked in cleanup | YES | |
| `-synctex=N` passed to engine | NO | must be set via `latex_extra_options` |

### Configuration File Loading

| Feature | Status |
|---------|--------|
| System config dir | YES |
| User config dir (platform-aware) | YES |
| Project `latexmk.toml` / `.latexmk.toml` | YES |
| `-r FILE` extra config | YES |
| Config merging (system → user → project → CLI) | YES |
| `-norc` skip all files | YES |

---

## 5. Behavioral Differences from Perl latexmk

### Configuration Format
Perl latexmk reads `latexmkrc` files containing arbitrary Perl code.
py-latexmk reads `latexmk.toml` files in TOML format — declarative only, no
code execution.  This is intentional for security.

### TeX Engine Passthrough Options
In Perl latexmk, unrecognised CLI options that appear in an allowlist (the
`-showextraoptions` list) are forwarded to all `*latex` engines verbatim.
**py-latexmk rejects every unrecognised option with an error.**  Options such
as `-synctex=1`, `-shell-escape`, `-halt-on-error`, `-max-print-line=N`,
`-file-line-error`, `-draftmode`, etc. must instead be placed in
`latex_extra_options` in `latexmk.toml` or appended to the engine command
string.

### `-latexoption=OPT` Not Implemented
Perl latexmk has `-latexoption=OPT` which appends OPT to every `*latex`
engine invocation.  py-latexmk has no equivalent CLI flag; use
`latex_extra_options` in `latexmk.toml` instead.

### Log-Line Wrapping Width
Perl latexmk reads the `max_print_line` environment variable and adjusts its
log-line-unwrapping heuristic accordingly.  py-latexmk uses a fixed value of
79 characters and does not read this environment variable.

### Error Codes
Both tools use the same exit codes: 10 (bad options), 11 (file not found),
12 (build failure), 13 (config error), 20 (internal error).

### Version String
- Perl: `latexmk version 4.88`
- Python: `latexmk version 4.88 (python package X.Y.Z)`

### Rebuild Triggering
Both use MD5-based change detection.  Perl additionally uses file stat times
as a quick pre-filter; py-latexmk computes MD5 unconditionally.

### CPU / Wall Time Reporting (`-time`)
Perl latexmk reports CPU time using `HiRes` where available.  py-latexmk
reports wall-clock elapsed time via `time.time()`.

### Timing: `$sleep_time` in `-pvc`
Both honour a configurable sleep interval between polls.  Values are in
seconds in both tools.

### Landscape Mode
Perl latexmk has `-l` / `-l-` and a `$landscape_mode` variable that appends
geometry options to the command string.  py-latexmk has no landscape mode.

### Print Support
Perl latexmk can print DVI/PS/PDF via configurable print commands.
py-latexmk parses `-p` / `-print=` but has no print implementation.

### Hook System
Perl latexmk supports per-rule code hooks (`@PRE_TEX`, `@POSTSCRIPT_TEX`,
etc.) defined in rc files.  py-latexmk has no hook mechanism — the TOML
config schema does not allow executable code.

### Kpsewhich Integration
Perl latexmk uses `kpsewhich` to locate files when `-use-make` is active.
py-latexmk does not call `kpsewhich`.

### XDV-Only Mode
Perl latexmk can stop the pipeline after producing XDV output.  py-latexmk
treats XDV as an intermediate step toward PDF only.

### HNT / HINT Mode
Perl latexmk (≥ 4.76) supports HiTeX / HiNT output.  py-latexmk does not.

---

## 6. Summary

| Area | Coverage |
|------|----------|
| Core build engines | ~100% |
| Bibliography (bibtex/biber) | ~100% |
| Index / glossaries | ~100% |
| PostScript pipeline | ~100% |
| Dependency tracking | ~100% |
| Continuous watch mode | ~100% |
| Viewer launch | ~100% |
| Cleanup | ~100% |
| Custom dependencies | ~100% |
| Configuration loading | ~100% |
| TeX passthrough options | **0%** (must use `latex_extra_options`) |
| `-latexoption` flag | **0%** |
| Print support | **0%** |
| Landscape mode | **0%** |
| HNT mode | **0%** |
| Hooks / code in config | **0%** (intentionally out of scope) |
| Kpsewhich / use-make | **0%** |
