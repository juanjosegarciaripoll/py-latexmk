# T08: Primary Build Loop (pdflatex / lualatex / xelatex)
**Status:** `todo`
**Depends on:** T02, T03, T04, T05, T06, T07

## Goal
Implement `rdb.py` `build()` function for the primary PDF modes (pdf_mode 1,
4, 5 = pdflatex, lualatex, xelatex). Multi-pass convergence loop, dependency
update from .fls/.log, .fdb_latexmk persistence. No secondary rules yet (T09).

This is the milestone where `latexmk -pdf simple.tex` works end-to-end.

## Files
- `latexmk_py/rdb.py`
- `tests/test_rdb.py`
- `tests/fixtures/simple/` — minimal hello-world .tex

## simple/ fixture

```
tests/fixtures/simple/
  hello.tex
```

`hello.tex`:
```latex
\documentclass{article}
\begin{document}
Hello, world!
\end{document}
```

## rdb.py key interface

```python
class RuleDatabase:
    def __init__(self, tex: Path, cfg: Config) -> None: ...

    def build(self) -> int:
        """Run full build loop. Return exit code (0=success, 12=error)."""

    def watch(self) -> int:
        """Run -pvc loop. Return exit code. Implemented in T16."""
```

## build() algorithm

```python
def build(self) -> int:
    fdb_path = self._fdb_path()
    fdb = read_fdb(fdb_path)
    self.rules = init_rules(self.tex, self.cfg, fdb)

    for iteration in range(self.cfg.build.max_runs):
        stale = [r for r in self.rules if out_of_date(r, force=self.cfg.force)]
        if not stale:
            break
        for rule in topo_sort(stale):
            self._run_rule(rule)
            if rule.last_result != 0 and not self.cfg.force:
                write_fdb(fdb_path, self._rules_to_fdb())
                return 12
            self._update_deps(rule)    # parse fls/log
            # secondary rule triggers handled in T09
    else:
        logging.warning("latexmk: did not converge after %d runs",
                        self.cfg.build.max_runs)

    write_fdb(fdb_path, self._rules_to_fdb())
    return 0

def _run_rule(self, rule: Rule) -> None:
    result = run_command(rule.command, source=rule.source, ...)
    rule.last_result = result.exit_code
    rule.run_time = time.time()
    rule.last_message = result.stderr[-500:] if result.stderr else ""
    rule.out_of_date = False
    # update dest md5s
    for p in [rule.dest] + list(rule.extra_dests):
        if p.exists():
            rule.dest_md5[p] = compute_md5(p)

def _update_deps(self, rule: Rule) -> None:
    """Parse .fls (primary) + .log (always) to update rule.extra_sources."""
    if self.cfg.build.recorder:
        fls = rule.dest.with_suffix('.fls')  # or in aux_dir
        result = parse_fls(fls)
        rule.extra_sources.update(result.inputs)
        rule.extra_dests.update(result.outputs)
    log = rule.dest.with_suffix('.log')
    log_result = parse_log(log)
    if log_result.rerun_needed:
        rule.out_of_date = True  # force next iteration
    # update source md5s for all discovered inputs
    for p in rule.extra_sources:
        if p.exists():
            rule.source_md5[p] = compute_md5(p)
```

## .fdb path

`<tex_stem>.fdb_latexmk` alongside the .tex file, or in `out_dir` if set.

## Output

On each rule run, print (unless silent):
```
Latexmk: applying rule 'pdflatex'...
Rule 'pdflatex': File changes, etc:
```
Mirror Perl latexmk message style.

Pass through all *latex stdout/stderr to our stdout/stderr unchanged so that
editor error parsers (LaTeX Workshop) can read them.

## Checklist
- [ ] `latexmk -pdf tests/fixtures/simple/hello.tex` produces `hello.pdf`
- [ ] Second run with no changes: 0 rules run (reads fdb, all up to date)
- [ ] Touch `hello.tex` → reruns pdflatex
- [ ] `-g` forces rerun even with no changes
- [ ] Non-zero pdflatex exit → returns 12 (without `-f`)
- [ ] Non-zero pdflatex exit + `-f` → continues
- [ ] `.fdb_latexmk` written after build
- [ ] `.fdb_latexmk` read on second run correctly
- [ ] `uv run pytest tests/test_rdb.py -q` (mock runner)
- [ ] Type-clean
