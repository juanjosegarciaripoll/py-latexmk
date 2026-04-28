# T15: Dependency Output (-M, -deps)
**Status:** `done`
**Depends on:** T08

## Goal
Implement `deps.py`: write a make-compatible dependency file after a
successful build.

## Files
- `latexmk_py/deps.py`
- `tests/test_deps.py`

## Interface

```python
def write_deps(
    rules: Sequence[Rule],
    cfg: DepsConfig,
    tex: Path,
) -> None:
    """Write make-format dependency list to cfg.file ('-'=stdout)."""
```

## Output format

```
target: dep1 dep2 dep3 \
    dep4 dep5
```

- Target: the final output file (primary rule's dest, or last postprocess dest)
- Deps: all unique source paths across all rules
- If `cfg.phony`: also emit `dep1:\n dep2:\n ...` (phony targets)
- Escape spaces in filenames according to `cfg.escape`:
  - `"none"`: no escaping
  - `"unix"`: backslash before space → `file\ name`
  - `"nmake"`: caret before space → `file^ name`

## Escape function

```python
def _escape(path: str, mode: str) -> str:
    match mode:
        case "unix":  return path.replace(' ', r'\ ')
        case "nmake": return path.replace(' ', '^ ')
        case _:       return path
```

## File writing

```python
def write_deps(rules, cfg, tex):
    target = _final_output(rules)
    all_deps: set[Path] = set()
    for rule in rules:
        all_deps.update(rule.extra_sources)
        all_deps.add(rule.source)
    all_deps.discard(target)

    lines = [f'{_escape(str(target), cfg.escape)}: \\']
    dep_strs = [_escape(str(d), cfg.escape) for d in sorted(all_deps)]
    lines += [f'    {d} \\' for d in dep_strs[:-1]]
    if dep_strs:
        lines.append(f'    {dep_strs[-1]}')

    if cfg.phony:
        lines.append('')
        for d in dep_strs:
            lines.append(f'{d}:')

    content = '\n'.join(lines) + '\n'

    if cfg.file == '-':
        sys.stdout.write(content)
    else:
        Path(cfg.file).write_text(content, encoding='utf-8')
```

## CLI mapping (from T03)

| Flag | Effect |
|---|---|
| `-deps` / `-dependents` / `-M` | `deps.enabled=True` |
| `-deps-` | `deps.enabled=False` |
| `-deps-out=F` / `-MF F` | `deps.file=F` |
| `-deps-escape=K` | `deps.escape=K` |
| `-MP` | `deps.phony=True` |

`write_deps` is called at the end of `build()` when `cfg.deps.enabled`.

## Checklist
- [x] Output matches `make` dependency syntax
- [x] Space escaping: `none`, `unix`, `nmake`
- [x] Phony targets emitted when `phony=True`
- [x] `-MF FILE` writes to file not stdout
- [x] All rule sources included in dep list
- [x] `uv run pytest tests/test_deps.py -q`
- [x] Type-clean
