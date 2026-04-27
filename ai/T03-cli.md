# T03: CLI / argparse
**Status:** `done`
**Depends on:** T01, T02

## Goal
Implement `cli.py`: parse all CLI flags, map them onto `Config`, load config
files, then dispatch to build / clean / info actions. After this task
`latexmk --help` and `latexmk --version` work; all other paths exit with a
stub message.

## Files
- `latexmk_py/cli.py`

## Entry point

```python
def main() -> None:
    """Parse args, load config, dispatch."""
```

Exit codes: see PLAN.md §Exit Codes. Top-level `main()` catches all
`LatexmkError` subclasses, prints `latexmk: <msg>` to stderr, exits with
the matching code. Catches bare `Exception` → exit 20.

## Argument mapping

Build a two-phase parser:
1. Pre-parse for `-norc` and `-r FILE` (affects config loading).
2. Load `Config` via `load_config()`.
3. Full argparse with config defaults.
4. Override config fields from parsed args, produce final `Config`.

### All flags (map to Config field)

```
Output format:
  -pdf              build.pdf_mode=1
  -pdfdvi           build.pdf_mode=2
  -pdflua           build.pdf_mode=4
  -pdfxe            build.pdf_mode=5
  -pdf-             build.pdf_mode=0
  -dvi              build.dvi_mode=1
  -dvilua           build.dvi_mode=2
  -dvi-             build.dvi_mode=0
  -ps               build.postscript_mode=1
  -ps-              build.postscript_mode=0
  -output-format=F  shorthand (pdf/dvi/ps/dvilua/pdfxe)

Engine commands (optional =CMD):
  -latex[=CMD]      commands.latex
  -pdflatex[=CMD]   commands.pdflatex
  -lualatex[=CMD]   commands.lualatex
  -xelatex[=CMD]    commands.xelatex
  -bibtex[=CMD]     commands.bibtex
  -biber[=CMD]      commands.biber
  -stdtexcmds       reset commands to defaults

Directories:
  -auxdir=D / -aux-directory=D    directories.aux_dir
  -outdir=D / -output-directory=D directories.out_dir
  -out2dir=D                      directories.out2_dir
  -cd / -cd-                      build.cd
  -jobname=N                      build.jobname
  -emulate-aux-dir / -emulate-aux-dir-   directories.emulate_aux_dir

BibTeX/Biber:
  -bibtex           bibtex.use=2
  -bibtex-          bibtex.use=0
  -nobibtex         bibtex.use=0
  -bibtex-cond      bibtex.use=1
  -bibtex-cond1     bibtex.use=1.5
  -bibtexfudge      bibtex.fudge=True
  -bibtexfudge-     bibtex.fudge=False
  -nobibtexfudge    bibtex.fudge=False

Processing:
  -f / -f-          force (not in Config; stored as config.force)
  -g / -g-          force rerun (go_mode=1/0)
  -gg               clean+build (go_mode=2)
  -gt               regen all (go_mode=3)
  -recorder / -recorder-   build.recorder
  -interaction=MODE         appended to build.latex_extra_options
  -pretex=CODE / -usepretex[=CODE]   stored for prepending to source

Preview:
  -pv               preview_mode=True
  -pvc / -pvc-      preview_continuous=True/False
  -view=WHAT        preview.view
  -pvctimeout       preview.timeout_mins enable
  -pvctimeoutmins=N preview.timeout_mins
  -new-viewer / -new-viewer-   preview.new_viewer_always
  -p                print_mode=True
  -print=WHAT       print_what

Cleanup:
  -c                cleanup_mode=1
  -C / -CA          cleanup_mode=2
  -CF               cleanup_fdb=True
  -gg               also cleanup_mode=2 then build

Deps:
  -deps / -dependents  deps.enabled=True
  -deps-               deps.enabled=False
  -deps-out=F          deps.file
  -deps-escape=K       deps.escape
  -M                   deps.enabled=True
  -MF F                deps.file
  -MP                  deps.phony=True

Config:
  -norc             norc=True
  -r FILE           extra_rc_files += [FILE]

Diagnostics:
  -h / -help        print help, exit 0
  -v / -version     print "latexmk version X.Y", exit 0
  -commands         print resolved commands, exit 0
  -diagnostics      output.silent=False + verbose flag
  -dir-report       print resolved dir paths
  -dir-report-only  print dirs, exit 0
  -time / -time-    output.show_time
  -rc-report / -rc-report-   output.rc_report
  -rules / -rules-  rules_list flag
  -quiet / -silent  output.silent=True
  -logfilewarnings  log_warnings flag
  -Werror           output.warnings_as_errors=True
  -showextraoptions show extra *latex options, exit 0
```

## Dispatch logic

```python
match action:
    case "help":    print_help(); sys.exit(0)
    case "version": print(f"latexmk version {VERSION}"); sys.exit(0)
    case "commands": print_commands(cfg); sys.exit(0)
    case "cleanup": clean(tex_files, cfg); sys.exit(0)
    case "build":   build_all(tex_files, cfg)
    case "pvc":     watch_all(tex_files, cfg)
```

`tex_files` defaults to glob of `cfg.build.default_files` minus
`cfg.build.default_excluded_files` if no positional args given.

## Checklist
- [ ] `latexmk --help` exits 0 with usage
- [ ] `latexmk --version` exits 0 with version string
- [ ] All flags parse without error
- [ ] Unknown flag exits 10 with `latexmk: unknown option` message
- [ ] No .tex file found exits 11
- [ ] `-norc` suppresses config loading
- [ ] `-r FILE` (TOML) overrides config
- [ ] Type-clean
