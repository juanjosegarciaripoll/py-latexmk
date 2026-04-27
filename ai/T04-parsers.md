# T04: Parsers (fls, log, aux, bcf)
**Status:** `todo`
**Depends on:** T01

## Goal
Implement the four file parsers that discover dependencies after each *latex
run. Each returns a typed result dataclass. All are pure functions — no
subprocess calls, no global state.

## Files
- `latexmk_py/parsers/__init__.py`
- `latexmk_py/parsers/fls.py`
- `latexmk_py/parsers/log.py`
- `latexmk_py/parsers/aux.py`
- `latexmk_py/parsers/bcf.py`
- `tests/test_fls.py`
- `tests/test_log.py`
- `tests/test_aux.py`
- `tests/test_bcf.py`
- `tests/fixtures/logs/` — recorded .fls / .log / .aux / .bcf files

---

## parsers/fls.py

Mirrors `parse_fls` in `latexmk.pl` lines 7153–7384.

```python
@dataclass(slots=True, frozen=True)
class FlsResult:
    pwd: str                  # PWD line from .fls (empty if absent)
    inputs: frozenset[Path]   # INPUT lines, relative to pwd
    outputs: frozenset[Path]  # OUTPUT lines

def parse_fls(path: Path) -> FlsResult:
    """Parse a .fls recorder file."""
```

Line grammar:
```
PWD <directory>
INPUT <filepath>
OUTPUT <filepath>
```
- Strip leading/trailing whitespace per line.
- Convert `\\` → `/` in paths.
- Strip the `PWD` prefix from INPUT/OUTPUT paths when present.
- Skip blank lines and comment lines.
- Non-existent file: return `FlsResult(pwd="", inputs=frozenset(), outputs=frozenset())`.

---

## parsers/log.py

Mirrors `parse_log` in `latexmk.pl` lines 6119–6550.

```python
@dataclass(slots=True, frozen=True)
class LogResult:
    rerun_needed: bool
    missing_files: frozenset[str]    # file names/stems (no extension guaranteed)
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    bad_references: int
    bad_citations: int

def parse_log(path: Path) -> LogResult:
    """Parse a *latex .log file for build signals."""
```

Key patterns (from latexmk.pl):

**Rerun signal:**
```python
re.search(r'Rerun to get', line)
```

**Missing files** (check each line against these patterns):
```python
MISSING_FILE_PATTERNS = [
    r'^No file\s+(.*)\.$',
    r'^No file\s+(.+)\s*$',
    r"^! LaTeX Error: File `([^'\\']*)' not found\.",
    r"^! I can't find file `([^'\\']*)'\.",
    r".*?:\d*: LaTeX Error: File `([^'\\']*)' not found\.",
    r"^LaTeX Warning: File `([^'\\']*)' not found",
    r"^Package .* [fF]ile `([^'\\']*)' not found",
    r"^Package .* No file `([^'\\']*)'",
    r'Error: pdflatex \(file ([^)]*)\): cannot find image file',
    r'cannot open\s+([^:]+): No such file or directory',
    r': File (.*) not found:\s*$',
    r"! Unable to load picture or PDF file '([^']+)'\.",
]
```

**Warnings:**
```python
WARNING_PATTERNS = [
    r"^LaTeX Warning: ((?:Hyper reference|Reference) `[^']+' on page .+ undefined on input line .*)\.?$",
    r"^Package natbib Warning: (Citation[^\001]*undefined on input line .*)\.?$",
    r"^LaTeX Warning: (Label `[^']+' multiply defined.*)\.?$",
    r"^LaTeX Warning: (Citation [`'][^']+' on page .* undefined on input line .*)\.?$",
]
```

**Errors:** lines starting with `! ` or `.*:\d+: `.

Return `LogResult` with all accumulated findings.

---

## parsers/aux.py

Mirrors `parse_aux` / `parse_aux1` in `latexmk.pl` lines 7570–7721.

```python
@dataclass(slots=True, frozen=True)
class AuxResult:
    bib_files: frozenset[str]   # from \bibdata{...}
    bst_files: frozenset[str]   # from \bibstyle{...}
    aux_inputs: frozenset[str]  # from \@input{...}

def parse_aux(path: Path) -> AuxResult:
    """Parse .aux file(s) recursively for bibliography info."""
```

Patterns:
```python
r'^\\bibdata\{([^}]+)\}'    # comma-separated, append .bib if missing
r'^\\bibstyle\{([^}]+)\}'
r'^\\\@input\{([^}]+)\}'    # recurse into this .aux file
```

`\bibdata` values: split on `,`, strip whitespace, append `.bib` if no `.bib`
suffix. Recurse into `\@input` relative to the directory of the top-level aux.
Missing included aux file: skip silently (not an error at this stage).

---

## parsers/bcf.py

```python
@dataclass(slots=True, frozen=True)
class BcfResult:
    data_sources: frozenset[str]  # .bib file paths from <bcf:datasource>

def parse_bcf(path: Path) -> BcfResult:
    """Parse a Biber .bcf control file for data sources."""
```

The `.bcf` file is XML. Use `xml.etree.ElementTree`. Namespace:
`http://biblatex-biber.sourceforge.net/biblatexml`. Look for:
```xml
<bcf:datasources>
  <bcf:datasource type="file" datatype="bibtex">refs.bib</bcf:datasource>
</bcf:datasources>
```
Extract text content of each `<bcf:datasource>` element. Non-existent or
malformed file → return empty `BcfResult`.

---

## Test fixtures

Create minimal recorded files under `tests/fixtures/logs/`:
- `simple.fls` — a few INPUT/OUTPUT lines
- `simple.log` — includes "Rerun to get cross-references", a missing-file
  warning, and a reference warning
- `simple.aux` — `\bibdata{refs}`, `\bibstyle{plain}`, `\@input{ch1.aux}`
- `ch1.aux` — empty or minimal
- `simple.bcf` — minimal XML with one datasource

Write these by hand (copy/trim from a real latexmk run if available).

---

## Checklist
- [ ] `parse_fls` extracts PWD, inputs, outputs correctly
- [ ] `parse_fls` on missing file returns empty result (no exception)
- [ ] `parse_log` detects "Rerun to get"
- [ ] `parse_log` extracts missing file names
- [ ] `parse_log` extracts warnings
- [ ] `parse_aux` splits `\bibdata` comma list, appends .bib
- [ ] `parse_aux` recurses into `\@input`
- [ ] `parse_bcf` extracts datasource paths
- [ ] `parse_bcf` on malformed XML returns empty (no exception)
- [ ] `uv run pytest tests/test_fls.py tests/test_log.py tests/test_aux.py tests/test_bcf.py -q`
- [ ] Type-clean
