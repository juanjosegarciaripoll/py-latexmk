# TOML Configuration Schema

Full schema with all keys, types, defaults, and allowed values.
Consumed by `T02-config.md` (implementation) and `config.py`.

## [build]

| Key | Type | Default | Notes |
|---|---|---|---|
| `pdf_mode` | int | 1 | 0=none 1=pdflatex 2=latex+dvips+ps2pdf 3=latex+dvipdf 4=lualatex 5=xelatex |
| `dvi_mode` | int | 0 | 0=none 1=latex 2=dvilualatex |
| `postscript_mode` | int | 0 | 0=none 1=dvips |
| `xdv_mode` | int | 0 | 0=none 1=xelatex→xdv |
| `recorder` | bool | true | pass -recorder to *latex, generates .fls |
| `max_runs` | int | 10 | max *latex reruns before declaring non-convergence |
| `cd` | bool | false | cd to source file directory before building |
| `jobname` | str | "" | empty = use .tex stem |
| `latex_extra_options` | str[] | [] | appended to %O in all *latex commands |
| `default_files` | str[] | ["*.tex"] | glob patterns if no source args given |
| `default_excluded_files` | str[] | [] | excluded from default glob |

## [commands]

All values are command templates. Placeholders:

| Token | Expands to |
|---|---|
| `%S` | source file path (quoted if spaces) |
| `%D` | dest file path (quoted if spaces) |
| `%B` | basename of source (no ext, no dir) |
| `%R` | root stem (jobname or .tex stem) |
| `%T` | main .tex path (quoted) |
| `%O` | `latex_extra_options` joined + dir flags |
| `%Y` | aux_dir with trailing `/` (empty if unset) |
| `%Z` | out_dir with trailing `/` (empty if unset) |

| Key | Default |
|---|---|
| `latex` | `"latex -interaction=nonstopmode %O %S"` |
| `pdflatex` | `"pdflatex -interaction=nonstopmode %O %S"` |
| `lualatex` | `"lualatex -interaction=nonstopmode %O %S"` |
| `xelatex` | `"xelatex -interaction=nonstopmode %O %S"` |
| `dvilualatex` | `"dvilualatex -interaction=nonstopmode %O %S"` |
| `bibtex` | `"bibtex %O %S"` |
| `biber` | `"biber %O %S"` |
| `makeindex` | `"makeindex %O -o %D %S"` |
| `dvips` | `"dvips %O -o %D %S"` |
| `dvipdf` | `"dvipdf %O %S %D"` |
| `ps2pdf` | `"ps2pdf %O %S %D"` |
| `makeglossaries` | `"makeglossaries %O %B"` |
| `print_pdf` | `""` |
| `print_ps` | `""` |
| `print_dvi` | `""` |

## [directories]

| Key | Type | Default | Notes |
|---|---|---|---|
| `aux_dir` | str | "" | empty = same as out_dir |
| `out_dir` | str | "" | empty = source file directory |
| `out2_dir` | str | "" | empty = no copy; if set, final output copied here |
| `emulate_aux_dir` | bool | true | move aux files post-run when engine ignores -aux-directory |

## [bibtex]

| Key | Type | Default | Notes |
|---|---|---|---|
| `use` | float | 1.0 | 0=never 1=if-.bib-found 1.5=cond1 2=always |
| `fudge` | bool | true | cd to aux_dir before running bibtex |

## [preview]

| Key | Type | Default | Notes |
|---|---|---|---|
| `view` | str | "default" | "default"\|"pdf"\|"dvi"\|"ps"\|"none" |
| `sleep_time` | float | 2.0 | seconds between polls in -pvc |
| `timeout_mins` | float | 0.0 | 0=no timeout |
| `new_viewer_always` | bool | false | always start new viewer window |
| `pdf_previewer` | str | "auto" | "auto"=platform default or command template |
| `dvi_previewer` | str | "auto" | |
| `ps_previewer` | str | "auto" | |

`"auto"` resolution: macOS → `open %S`, Windows → `start "" %S`, Linux → `xdg-open %S`

## [cleanup]

| Key | Type | Default | Notes |
|---|---|---|---|
| `extra_extensions` | str[] | [] | additional exts removed by -c |
| `extra_full_extensions` | str[] | [] | additional exts removed by -C |
| `includes_cusdep_generated` | bool | false | also remove cusdep output files |

Built-in lists:
- `-c`: `acn acr alg aux bbl bcf blg brf fdb_latexmk fls glg glo gls idx ilg ind ist lof log lot nav out run.xml snm synctex synctex.gz toc vrb xdy`
- `-C` adds: `dvi hnt pdf ps xdv`

## [deps]

| Key | Type | Default | Notes |
|---|---|---|---|
| `enabled` | bool | false | write make-format dep list |
| `file` | str | "-" | output file; "-" = stdout |
| `escape` | str | "none" | "none"\|"unix"\|"nmake" |
| `phony` | bool | false | emit phony targets (like gcc -MP) |

## [output]

| Key | Type | Default | Notes |
|---|---|---|---|
| `silent` | bool | false | suppress progress messages |
| `show_time` | bool | false | show elapsed time per rule |
| `max_logfile_warnings` | int | 7 | 0=unlimited |
| `warnings_as_errors` | bool | false | |
| `rc_report` | bool | true | print loaded config file paths |

## [[custom_dependency]]

Array of tables. Each entry:

| Key | Type | Required | Notes |
|---|---|---|---|
| `from` | str | yes | source extension, e.g. `"fig"` |
| `to` | str | yes | target extension, e.g. `"eps"` |
| `must` | bool | no (default false) | error if source missing |
| `command` | str | yes | command template; `%S`=source `%D`=dest `%B`=base |

Examples:
```toml
[[custom_dependency]]
from = "glo"
to   = "gls"
must = false
command = "makeglossaries %B"

[[custom_dependency]]
from = "acn"
to   = "acr"
must = false
command = "makeglossaries %B"

[[custom_dependency]]
from = "fig"
to   = "eps"
must = true
command = "fig2dev -Leps %S %D"

[[custom_dependency]]
from = "svg"
to   = "pdf"
must = false
command = "inkscape --export-pdf=%D %S"
```

## Config file locations

| Level | Linux/macOS | Windows |
|---|---|---|
| System | `/etc/latexmk/config.toml` | `%ProgramData%\latexmk\config.toml` |
| User | `$XDG_CONFIG_HOME/latexmk/config.toml` (default `~/.config/latexmk/config.toml`) | `%APPDATA%\latexmk\config.toml` |
| Project | `./latexmk.toml` or `./.latexmk.toml` | same |
| CLI | `-r FILE` (TOML) | |

`-norc` skips system+user+project. CLI flags override everything.
`LATEXMKRCSYS` env var overrides the system config path.
