# T11: Custom Dependencies
**Status:** `todo`
**Depends on:** T08, T10

## Goal
Implement TOML `[[custom_dependency]]` rules. When *latex produces a "missing
file" with extension `to`, and a file with extension `from` exists, run the
`command` template to generate the target.

## Files
- `latexmk_py/rdb.py` (extend `_add_secondary_rules`)
- `tests/test_rdb.py` (extend with cusdep mock tests)

## Config shape (from T02)

```python
@dataclass(slots=True, frozen=True)
class CustomDep:
    from_ext: str    # e.g. "fig"
    to_ext: str      # e.g. "eps"
    must: bool       # error if source file missing
    command: str     # template e.g. "fig2dev -Leps %S %D"
```

## Detection

After parsing `.log` with `parse_log()`, `LogResult.missing_files` contains
file stems that *latex could not find. For each missing stem:

```python
def _add_cusdep_rules(self, primary: Rule, log: LogResult) -> None:
    for missing in log.missing_files:
        stem = Path(missing).stem
        for cusdep in self.cfg.custom_deps:
            # Does the missing file match this cusdep's to_ext?
            if not missing.endswith(f'.{cusdep.to_ext}'):
                continue
            source = primary.source.parent / f'{stem}.{cusdep.from_ext}'
            dest   = primary.source.parent / f'{stem}.{cusdep.to_ext}'
            if not source.exists():
                if cusdep.must:
                    raise FileMissingError(
                        f"latexmk: custom dep source {source} not found"
                    )
                continue
            name = f"cusdep_{cusdep.from_ext}_{cusdep.to_ext}_{stem}"
            if name in self._rule_map:
                continue
            rule = Rule(
                name=name,
                kind='cusdep',
                command=cusdep.command,
                source=source,
                dest=dest,
                base=primary.source.parent / stem,
            )
            self.rules.append(rule)
            self._rule_map[name] = rule
```

Cusdep rules run before the primary rule in the next iteration (topo sort
puts cusdep before primary).

## Cleanup integration

When `cfg.cleanup.includes_cusdep_generated` is True, `cleaner.py` (T13)
removes files in `rule.extra_dests` for all cusdep rules.

## Checklist
- [ ] Missing `.eps` + `.fig` source present → cusdep rule created
- [ ] Cusdep command runs with correct `%S` / `%D` expansion
- [ ] After cusdep run, primary reruns (`.eps` now exists)
- [ ] `must=True` + missing source → `FileMissingError`
- [ ] `must=False` + missing source → skip silently
- [ ] `includes_cusdep_generated=True` → generated files removed by `-c`
- [ ] Type-clean
