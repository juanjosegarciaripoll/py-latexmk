# T13: Cleanup (-c, -C, -CF)
**Status:** `done`
**Depends on:** T02, T07

## Goal
Implement `cleaner.py`: remove generated files for a given .tex source,
respecting cleanup mode.

## Files
- `latexmk_py/cleaner.py`
- `tests/test_cleaner.py`

## Interface

```python
def clean(
    tex: Path,
    cfg: Config,
    mode: Literal[1, 2],   # 1=-c  2=-C
    *,
    fdb_only: bool = False, # True for -CF
    rules: Sequence[Rule] | None = None,
) -> None:
    """Remove generated files for tex."""
```

## Extension lists

```python
INTERMEDIATE_EXTS: frozenset[str] = frozenset({
    'acn', 'acr', 'alg', 'aux', 'bbl', 'bcf', 'blg', 'brf',
    'fdb_latexmk', 'fls', 'glg', 'glo', 'gls', 'idx', 'ilg',
    'ind', 'ist', 'lof', 'log', 'lot', 'nav', 'out', 'run.xml',
    'snm', 'synctex', 'synctex.gz', 'toc', 'vrb', 'xdy',
})

FINAL_EXTS: frozenset[str] = frozenset({
    'dvi', 'hnt', 'pdf', 'ps', 'xdv',
})
```

## Deletion logic

```python
def _exts_to_remove(cfg: Config, mode: int) -> frozenset[str]:
    exts = INTERMEDIATE_EXTS | frozenset(cfg.cleanup.extra_extensions)
    if mode == 2:
        exts |= FINAL_EXTS | frozenset(cfg.cleanup.extra_full_extensions)
    return exts

def clean(tex, cfg, mode, *, fdb_only=False, rules=None):
    base = tex.stem
    search_dirs = _affected_dirs(tex, cfg)  # out_dir + aux_dir + tex.parent

    if fdb_only:
        for d in search_dirs:
            p = d / f'{base}.fdb_latexmk'
            _try_remove(p)
        return

    exts = _exts_to_remove(cfg, mode)
    for d in search_dirs:
        for ext in exts:
            _try_remove(d / f'{base}.{ext}')

    # cusdep-generated files
    if cfg.cleanup.includes_cusdep_generated and rules:
        for rule in rules:
            if rule.kind == 'cusdep':
                _try_remove(rule.dest)
                for p in rule.extra_dests:
                    _try_remove(p)

def _try_remove(p: Path) -> None:
    try:
        p.unlink()
        logging.info('latexmk: removing %s', p)
    except FileNotFoundError:
        pass
```

## -gg mode

`-gg` = cleanup mode 2 then build. Implemented in `cli.py` / `rdb.py`:
call `clean(..., mode=2)` before starting `build()`.

## Checklist
- [ ] `-c` removes aux/log/fls but keeps PDF
- [ ] `-C` removes PDF as well
- [ ] `-CF` removes only `.fdb_latexmk`
- [ ] Extra extensions from config are removed
- [ ] cusdep-generated files removed when `includes_cusdep_generated=True`
- [ ] Missing files silently skipped (no exception)
- [ ] Searches both out_dir and aux_dir
- [ ] `uv run pytest tests/test_cleaner.py -q`
- [ ] Type-clean
