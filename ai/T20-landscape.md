# T20: Landscape Mode
**Status:** `todo`
**Depends on:** T19

## Goal

Implement `-l` / `-l-` (landscape mode).  When active, use a landscape-aware
`dvips` command and viewer commands.  Mirrors `$landscape_mode` in
`latexmk.pl` (line 1406).

## Changes

### `src/latexmk_py/config.py`

Add to `BuildConfig`:
```python
landscape: bool = False
```

Add to `CommandsConfig`:
```python
dvips_landscape: str = "dvips -tlandscape %O -o %D %S"
```

Add to `PreviewConfig`:
```python
ps_previewer_landscape: str = "auto"
dvi_previewer_landscape: str = "auto"
```

These default to the same value as `ps_previewer` / `dvi_previewer` at
runtime (resolved in `viewer.py`), matching Perl's behaviour on Windows/macOS
(same command) and Unix (`dvi_previewer_landscape = 'start xdvi -paper usr %O %S'`).

### `src/latexmk_py/cli.py`

Add two cases in `_parse()`:
```python
case "-l":
    build = replace(build, landscape=True)
case "-l-":
    build = replace(build, landscape=False)
```

### `src/latexmk_py/config.py` — TOML loading

In the `_apply_build` (or equivalent) section that reads TOML keys into
`BuildConfig`, map `"landscape"` → `build.landscape`.

In `CommandsConfig` TOML section, map `"dvips_landscape"`.

### `src/latexmk_py/rules.py` — dvips rule selection

`init_rules()` currently always uses `cfg.commands.dvips` for the
DVI→PS rule.  Change it to:

```python
dvips_cmd = cfg.commands.dvips_landscape if cfg.build.landscape else cfg.commands.dvips
```

### `src/latexmk_py/viewer.py` — landscape viewer selection

When resolving the PS or DVI previewer, check `cfg.build.landscape` and
prefer `cfg.preview.ps_previewer_landscape` / `cfg.preview.dvi_previewer_landscape`
if set to something other than `"auto"`.

Platform defaults for landscape (where they differ from portrait):

| Platform | `dvi_previewer_landscape` |
|----------|--------------------------|
| Unix | `start xdvi -paper usr %O %S` |
| Windows / macOS | same as `dvi_previewer` |

## Help text

Add to `_HELP` in `cli.py`:
```
  -l / -l-           Landscape mode on/off
```

## Tests

`tests/test_cli.py`:
- `-l` sets `build.landscape=True`; `-l-` resets to `False`

`tests/test_rdb.py` (or `test_rules.py`):
- when `landscape=True`, the dvips rule uses `dvips_landscape` command template

## Checklist
- [ ] `BuildConfig.landscape` field; `CommandsConfig.dvips_landscape`
- [ ] `-l` / `-l-` CLI flags
- [ ] TOML `landscape` and `dvips_landscape` keys loaded
- [ ] dvips rule uses `dvips_landscape` when `landscape=True`
- [ ] Landscape viewer logic in `viewer.py`
- [ ] Help text updated
- [ ] Tests pass; type-clean
