# T19: TeX Engine Passthrough Options
**Status:** `done`
**Depends on:** T18

## Goal

Accept TeX engine options on the CLI and forward them to `*latex` via
`latex_extra_options`, instead of raising `BadOptionsError`.  Also fix
`-output-format=pdfxe` and update `-showextraoptions`.

## Problem

`cli.py`'s `case _: raise BadOptionsError` rejects all unknown options.
Perl latexmk maintains an explicit allowlist (`%allowed_latex_options` /
`%allowed_latex_options_with_arg`, lines 549–668 of `latexmk.pl`) and silently
forwards matching options to every `*latex` engine.  Editor integrations
(LaTeX Workshop, vimtex) rely on this — they pass flags like
`-synctex=1 -file-line-error -shell-escape` directly on the CLI.

PLAN.md already says: "`-file-line-error` passes through to `*latex` via `%O` unchanged."

## Changes

### `src/latexmk_py/cli.py`

**1. Add the allowlist** (constant at module level):

```python
# Options recognised but not interpreted by latexmk; forwarded to *latex.
# Source: latexmk.pl lines 549-668.
_PASSTHROUGH_FLAGS: frozenset[str] = frozenset({
    "-cnf-line", "-draftmode", "-enc", "-etex",
    "-file-line-error", "-no-file-line-error",
    "-fmt", "-halt-on-error",
    "-ipc", "-ipc-start",
    "-kpathsea-debug",
    "-mktex", "-no-mktex", "-mltex",
    "-output-comment",
    "-parse-first-line", "-no-parse-first-line",
    "-progname",
    "-shell-escape", "-no-shell-escape", "-shell-restricted",
    "-src-specials",
    "-synctex",
    "-translate-file",
    "-8bit",
    # MiKTeX
    "-alias", "-buf-size", "-c-style-errors", "-no-c-style-errors",
    "-disable-installer", "-enable-installer",
    "-disable-pipes", "-enable-pipes",
    "-disable-write18", "-enable-write18", "-restrict-write18",
    "-dont-parse-first-line", "-enable-enctex", "-enable-mltex",
    "-error-line", "-extra-mem-bot", "-extra-mem-top",
    "-font-max", "-font-mem-size", "-half-error-line",
    "-hash-extra", "-job-time", "-main-memory",
    "-max-in-open", "-max-print-line", "-max-strings",
    "-nest-size", "-param-size", "-pool-size",
    "-record-package-usages", "-save-size", "-stack-size",
    "-string-vacancies", "-tcx", "-time-statistics",
    "-trace", "-trie-size", "-undump",
})
```

**2. Replace the `case _` handler** in `_parse()`:

```python
case _:
    # Check passthrough allowlist (bare flag or flag=value).
    bare = flag  # flag already has leading '-'
    if bare in _PASSTHROUGH_FLAGS or (
        _OPT_ASSIGN.match(raw) and bare in _PASSTHROUGH_FLAGS
    ):
        build = replace(build, latex_extra_options=(*build.latex_extra_options, raw))
    else:
        raise BadOptionsError(f"latexmk: unknown option {raw!r}")
```

**3. Add `-latexoption=OPT`** (adds OPT to every `*latex` command — equivalent
to appending to `latex_extra_options`):

```python
case "-latexoption":
    if not has_val:
        val_str, i = _take(argv, i, flag)
    build = replace(build, latex_extra_options=(*build.latex_extra_options, val_str))
```

**4. Fix `-output-format=pdfxe`** — currently absent from the match:

```python
case "-output-format":
    ...
    match val_str:
        ...
        case "pdfxe":
            build = replace(build, pdf_mode=5)
        ...
```

**5. Update `-showextraoptions`** output:

```python
if flags.want_showextraoptions:
    _out("Options forwarded to *latex (not interpreted by latexmk):\n")
    for opt in sorted(_PASSTHROUGH_FLAGS):
        _out(f"  {opt}")
    sys.exit(0)
```

### `src/latexmk_py/parsers/log.py`

The log parser unwraps lines at column 79 (Perl's `$log_wrap`).  TeXLive
respects the `max_print_line` environment variable.  Match that behaviour:

```python
import os
_LOG_WRAP = int(os.environ.get("max_print_line", 79))
```

Replace any hardcoded `79` / `_LOG_WRAP` constant with this.

## Tests

`tests/test_cli.py`:
- `-synctex=1` is accepted and lands in `latex_extra_options`
- `-file-line-error` (bare flag) is accepted
- `-max-print-line=200` is accepted
- `-latexoption=-shell-escape` appends to `latex_extra_options`
- `-output-format=pdfxe` sets `pdf_mode=5`
- A truly unknown flag still raises `BadOptionsError`

## Checklist
- [ ] All listed passthrough options accepted without error
- [ ] `-latexoption=OPT` appends OPT to `latex_extra_options`
- [ ] `-output-format=pdfxe` sets `pdf_mode=5`
- [ ] `-showextraoptions` lists the allowlist
- [ ] `max_print_line` env var controls log unwrap column
- [ ] Unknown options still raise `BadOptionsError`
- [ ] `uv run pytest tests/test_cli.py -q`
- [ ] Type-clean (`uv run basedpyright && uv run mypy .`)
