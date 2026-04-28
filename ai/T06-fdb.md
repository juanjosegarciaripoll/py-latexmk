# T06: .fdb_latexmk Read/Write
**Status:** `done`
**Depends on:** T01

## Goal
Read and write `.fdb_latexmk` files in exact binary-compatible format with
Perl latexmk 4.88. This allows editors (TeXstudio) and the Perl tool to
interoperate with our database.

## Files
- `latexmk_py/fdb.py`
- `tests/test_fdb.py`
- `tests/fixtures/logs/simple.fdb_latexmk` — a real fdb file from Perl latexmk

## Format (from latexmk.pl lines 8049–8350)

```
# Fdb version 4
["rule_name"] run_time "source" "dest" "base" check_time last_result
  "file" mtime size md5 "from_rule"
  "file" mtime size md5 "from_rule"
  ...
  (generated)
  "file"
  ...
  (rewritten before read)
  "file"
  ...
["next_rule"] ...
```

- Header must be exactly `# Fdb version 4\n`
- Rule header line regex: `^\["([^"]+)"\]\s+(\S+)\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+(\S+)\s+(\S+)`
  captures: name, run_time, source, dest, base, check_time, last_result
- File entry regex: `^\s+"([^"]*)"\s+(\S+)\s+(\S+)\s+(\S+)\s+"([^"]*)"`
  captures: file, mtime, size, md5, from_rule
- `(generated)` line starts the generated-files section (just file paths, no metadata)
- `(rewritten before read)` line starts that section
- Blank lines and comment lines (`#`) between rules are ignored

## Key interfaces

```python
@dataclass(slots=True)
class FdbFileEntry:
    path: Path
    mtime: float
    size: int
    md5: str
    from_rule: str   # empty string if not from another rule

@dataclass(slots=True)
class FdbRule:
    name: str
    run_time: float
    source: Path
    dest: Path
    base: Path
    check_time: float
    last_result: int
    files: list[FdbFileEntry]
    generated: list[Path]
    rewritten_before_read: list[Path]

def read_fdb(path: Path) -> dict[str, FdbRule]:
    """Parse .fdb_latexmk; return empty dict if file missing or corrupt."""

def write_fdb(path: Path, rules: Mapping[str, FdbRule]) -> None:
    """Write .fdb_latexmk in Perl-compatible format."""
```

## Writing format (exact)

```python
f'# Fdb version 4\n'
f'["{rule.name}"] {rule.run_time} "{rule.source}" "{rule.dest}" "{rule.base}" {rule.check_time} {rule.last_result}\n'
for entry in rule.files:
    f'  "{entry.path}" {entry.mtime} {entry.size} {entry.md5} "{entry.from_rule}"\n'
f'  (generated)\n'
for p in rule.generated:
    f'  "{p}"\n'
f'  (rewritten before read)\n'
for p in rule.rewritten_before_read:
    f'  "{p}"\n'
```

Floats for `run_time`/`mtime`/`check_time`: use `repr()` to preserve precision.

## Checklist
- [ ] Round-trip: write then read gives identical data
- [ ] Read a real `.fdb_latexmk` from Perl latexmk without error
- [ ] Missing file → empty dict (no exception)
- [ ] Corrupt/version-mismatch file → empty dict (logged warning, no exception)
- [ ] `write_fdb` output byte-matches Perl latexmk output for same input
  (compare using fixture from a real Perl latexmk run)
- [ ] `uv run pytest tests/test_fdb.py -q`
- [ ] Type-clean
