# T22: Small Missing Options
**Status:** `todo`
**Depends on:** T19

## Goal

Add several small CLI options and config variables that are missing from
py-latexmk: warning-list aliases, bibtex crossref threshold, and XDV-only
output mode.

---

## 1. `-logfilewarninglist` alias

Perl latexmk treats `-logfilewarninglist` / `-logfilewarnings` as synonyms
(both set `silence_logfile_warnings=0`), and `-logfilewarninglist-` /
`-logfilewarnings-` as synonyms (silence=1).
`latexmk.pl` lines 2137–2140.

**`cli.py`** — in `_parse()`:
```python
case "-logfilewarninglist" | "-logfilewarnings":
    flags.log_warnings = True
case "-logfilewarninglist-" | "-logfilewarnings-":
    flags.log_warnings = False
```

Replace the existing `-logfilewarnings` case with the above.

---

## 2. `-bibtex-min-crossrefs=N`

Perl's `$bibtex_min_crossrefs` is passed as `-min-crossrefs=N` to bibtex
(`latexmk.pl` lines 2200–2205).

### `config.py` — `BibtexConfig`
```python
min_crossrefs: int = 0   # 0 = do not pass -min-crossrefs (use bibtex default)
```

### `config.py` — TOML loading
Map `[bibtex] min_crossrefs = N`.

### `cli.py`
```python
case "-bibtex-min-crossrefs":
    if not has_val:
        val_str, i = _take(argv, i, flag)
    try:
        bibtex = replace(bibtex, min_crossrefs=int(val_str))
    except ValueError:
        raise BadOptionsError(f"latexmk: -bibtex-min-crossrefs requires an integer")
```

### `rdb.py` — bibtex rule construction
When building the bibtex command, if `cfg.bibtex.min_crossrefs > 0`, prepend
`-min-crossrefs={N}` to the `%O` expansion (i.e., add it to the options list
that fills `%O`).  Follow the existing pattern for how `%O` is populated for
bibtex calls in `rdb.py`.

---

## 3. XDV-only mode (`-xdv` / `-xdv-`)

`xdv_mode=1` already exists in `BuildConfig` (default 0).  The CLI has no
flag for it, and the rule database probably ignores it.

### `cli.py`
```python
case "-xdv":
    build = replace(build, xdv_mode=1, pdf_mode=0)
case "-xdv-":
    build = replace(build, xdv_mode=0)
```

### `rules.py` — `init_rules()`

When `cfg.build.xdv_mode == 1` and `cfg.build.pdf_mode == 0`:
- Add the xelatex primary rule with `.xdv` as the destination.
- Do **not** add the `xdvipdfmx` postprocess rule.

This mirrors Perl's treatment: `xdv_mode=1` means "produce XDV, stop there"
(`latexmk.pl` line 1405 and rule-construction logic).

Check `rules.py` for how the xelatex→xdvipdfmx chain is currently wired and
add the `xdv_mode==1` branch that omits the second step.

### Help text (`cli.py`)

```
  -xdv / -xdv-       XDV-only output on/off (xelatex without xdvipdfmx)
```

---

## Tests

`tests/test_cli.py`:
- `-logfilewarninglist` sets `flags.log_warnings = True`
- `-logfilewarninglist-` sets `flags.log_warnings = False`
- `-bibtex-min-crossrefs=2` sets `bibtex.min_crossrefs=2`
- bad value raises `BadOptionsError`
- `-xdv` sets `xdv_mode=1` and `pdf_mode=0`

`tests/test_rdb.py` or `tests/test_rules.py`:
- with `xdv_mode=1, pdf_mode=0`, `init_rules()` includes the xelatex rule
  but not xdvipdfmx
- with `bibtex.min_crossrefs=3`, the bibtex command contains `-min-crossrefs=3`

## Checklist
- [ ] `-logfilewarninglist` / `-logfilewarninglist-` aliases work
- [ ] `bibtex.min_crossrefs` config field; CLI flag; injected into bibtex command
- [ ] `-xdv` / `-xdv-` CLI flags
- [ ] `xdv_mode=1` rule: xelatex runs, xdvipdfmx does not
- [ ] TOML key `[bibtex] min_crossrefs` loaded
- [ ] Help text updated
- [ ] Tests pass; type-clean
