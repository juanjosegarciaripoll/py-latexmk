# T05: Runner (placeholder expansion + subprocess)
**Status:** `done`
**Depends on:** T01, T02

## Goal
Implement `runner.py`: expand command templates and execute them as
subprocesses. This is the only place that calls `subprocess.run`.

## Files
- `latexmk_py/runner.py`
- `tests/test_runner.py`

## Key interfaces

```python
@dataclass(slots=True, frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    elapsed: float   # wall-clock seconds

def expand_placeholders(
    template: str,
    *,
    source: Path,
    dest: Path,
    base: Path,
    root: Path,
    main_tex: Path,
    extra_opts: Sequence[str],
    aux_dir: str,
    out_dir: str,
) -> str:
    """Substitute %S %D %B %R %T %O %Y %Z in template."""

def run_command(
    template: str,
    *,
    source: Path,
    dest: Path,
    base: Path,
    root: Path,
    main_tex: Path,
    extra_opts: Sequence[str],
    aux_dir: str,
    out_dir: str,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Expand template and execute; return RunResult."""
```

## Placeholder rules

| Token | Value |
|---|---|
| `%S` | `str(source)` |
| `%D` | `str(dest)` |
| `%B` | `source.stem` |
| `%R` | `root.stem` |
| `%T` | `str(main_tex)` |
| `%O` | `shlex.join(extra_opts)` |
| `%Y` | `aux_dir + "/"` if aux_dir else `""` |
| `%Z` | `out_dir + "/"` if out_dir else `""` |

Expansion is plain string replace in order `%S %D %B %R %T %O %Y %Z`.
Paths containing spaces are handled by quoting the whole token value only
when the token appears unquoted in the template. Simple rule: if the
expanded value contains a space, wrap it in double-quotes unless it is
already inside quotes in the template.

## Execution

After expansion, detect shell operators:
```python
SHELL_OPERATORS = re.compile(r'(?<![\\])[|&;]')
```
If found → `subprocess.run(cmd_str, shell=True, ...)`.
Otherwise → `subprocess.run(shlex.split(cmd_str), shell=False, ...)` on POSIX;
use `shlex.split(cmd_str, posix=False)` on Windows.

Always capture stdout and stderr. Always set `encoding="utf-8"`.
Set `cwd=cwd` if provided.

## Error handling

`run_command` never raises on non-zero exit code — it returns the code in
`RunResult`. Callers decide whether to raise `BuildError`.
`subprocess.TimeoutExpired` is caught and re-raised as `BuildError`.

## Checklist
- [ ] `%S` `%D` `%B` `%R` `%T` `%O` `%Y` `%Z` all expand correctly
- [ ] Path with spaces gets quoted
- [ ] Shell operators detected → shell=True
- [ ] No shell operators → shell=False, list form
- [ ] `run_command` returns stdout/stderr/exit_code/elapsed
- [ ] `uv run pytest tests/test_runner.py -q` (use `echo` as the command in tests)
- [ ] Type-clean
