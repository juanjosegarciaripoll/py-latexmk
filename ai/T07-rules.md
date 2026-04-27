# T07: Rule Engine
**Status:** `todo`
**Depends on:** T01, T02, T06

## Goal
Implement `rules.py`: the `Rule` dataclass (mutable build state), `init_rules()`
to create the initial rule set from config, out-of-date detection, and
topological sort. No subprocess calls here.

## Files
- `latexmk_py/rules.py`
- `tests/test_rules.py`

## Rule dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass(slots=True)
class Rule:
    name: str
    kind: Literal['primary', 'secondary', 'postprocess', 'cusdep']
    command: str            # template before expansion
    source: Path
    dest: Path
    base: Path              # stem, no ext, no dir
    extra_sources: set[Path] = field(default_factory=set)
    extra_dests: set[Path]   = field(default_factory=set)
    source_md5: dict[Path, str] = field(default_factory=dict)
    dest_md5: dict[Path, str]   = field(default_factory=dict)
    run_time: float = 0.0   # 0.0 = never run
    last_result: int = 0
    last_message: str = ""
    out_of_date: bool = True
```

## init_rules()

```python
def init_rules(
    tex: Path,
    cfg: Config,
    fdb: dict[str, FdbRule] | None = None,
) -> list[Rule]:
    """Build the initial rule set for one .tex source file.

    Creates the primary rule (pdflatex/lualatex/etc.) and any
    postprocess rules (dvips/ps2pdf). Secondary rules (bibtex etc.)
    are added dynamically by rdb.py after parsing .aux.
    Restores run_time and md5s from fdb if available.
    """
```

Rules created:
- `primary`: determined by `cfg.build.pdf_mode` / `dvi_mode`
- `postprocess`: e.g. if `pdf_mode=2` create `latex`, `dvips`, `ps2pdf` in chain

File paths follow `cfg.directories.aux_dir` / `cfg.directories.out_dir`.

## out_of_date()

```python
def out_of_date(rule: Rule, *, force: bool = False) -> bool:
    """Return True if rule needs to run."""
```

Conditions (any one is sufficient):
1. `rule.run_time == 0.0`
2. `force is True`
3. Any key in `rule.source_md5` whose file now has a different MD5
4. Any key in `rule.source_md5` whose file no longer exists
5. `rule.dest` missing or its MD5 differs from `rule.dest_md5.get(rule.dest)`
6. Any key in `rule.dest_md5` whose file is missing

MD5 fast-path: compute MD5 only if `os.stat()` shows changed mtime+size.

```python
def compute_md5(path: Path) -> str:
    """Compute MD5 hex digest using hashlib.file_digest."""
```

Use `hashlib.file_digest(f, "md5")` with a `BufferedReader`. Never read whole
file into memory.

## topo_sort()

```python
def topo_sort(rules: Sequence[Rule]) -> list[Rule]:
    """Return rules in dependency order (primary before secondary before postprocess)."""
```

Simple approach: sort by kind priority `primary < secondary < cusdep < postprocess`,
then by name for determinism. Full graph sort not needed for current rule set
because the dependency structure is a DAG with at most 3 levels.

## Checklist
- [ ] `init_rules` creates correct rule for `pdf_mode=1` (pdflatex)
- [ ] `init_rules` creates correct rule chain for `pdf_mode=2` (latex→dvips→ps2pdf)
- [ ] `out_of_date` returns True on first call (never run)
- [ ] `out_of_date` returns False when md5s match and files exist
- [ ] `out_of_date` returns True when source MD5 changes
- [ ] `out_of_date` returns True when dest missing
- [ ] `compute_md5` produces correct hash
- [ ] `topo_sort` puts primaries before postprocess
- [ ] FDB restoration: `init_rules` with fdb populates run_time and md5s
- [ ] `uv run pytest tests/test_rules.py -q`
- [ ] Type-clean
