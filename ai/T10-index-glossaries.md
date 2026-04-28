# T10: Makeindex & Glossaries
**Status:** `done`
**Depends on:** T09

## Goal
Extend `rdb.py` to run makeindex and makeglossaries when .idx / .glo files
are produced by *latex.

## Files
- `latexmk_py/rdb.py` (extend `_add_secondary_rules`)
- `tests/fixtures/makeindex/` — .tex with `\makeindex`
- `tests/fixtures/glossaries/` — .tex with `\makeglossaries`
- `tests/integration/test_makeindex.py`
- `tests/integration/test_glossaries.py`

## Fixtures

**tests/fixtures/makeindex/main.tex**
```latex
\documentclass{article}
\usepackage{makeidx}
\makeindex
\begin{document}
Some text \index{word}.
\printindex
\end{document}
```

**tests/fixtures/glossaries/main.tex**
```latex
\documentclass{article}
\usepackage[acronym]{glossaries}
\makeglossaries
\newacronym{latex}{LaTeX}{Lamport \TeX}
\begin{document}
\gls{latex}
\printglossaries
\end{document}
```

## makeindex detection

```python
def _maybe_add_makeindex_rule(self, primary: Rule) -> None:
    idx = self._aux_path(primary).with_suffix('.idx')
    if not idx.exists():
        return
    name = f"makeindex_{primary.base.name}"
    if name in self._rule_map:
        return
    ind = idx.with_suffix('.ind')
    rule = Rule(
        name=name,
        kind='secondary',
        command=self.cfg.commands.makeindex,
        source=idx,
        dest=ind,
        base=primary.base,
    )
    self.rules.append(rule)
    self._rule_map[name] = rule
```

Call `_maybe_add_makeindex_rule` from `_add_secondary_rules`.

## makeglossaries detection

makeglossaries is configured as a TOML `[[custom_dependency]]` — no
hard-coded rule. However, if a `makeglossaries` cusdep is not in the
config, add a built-in fallback that fires when `.glo` exists:

```python
def _maybe_add_glossaries_rule(self, primary: Rule) -> None:
    glo = self._aux_path(primary).with_suffix('.glo')
    if not glo.exists():
        return
    # Check if a cusdep glo→gls is already configured
    if any(cd.from_ext == 'glo' and cd.to_ext == 'gls'
           for cd in self.cfg.custom_deps):
        return  # will be handled by T11
    name = f"makeglossaries_{primary.base.name}"
    if name in self._rule_map:
        return
    gls = glo.with_suffix('.gls')
    rule = Rule(
        name=name,
        kind='secondary',
        command=self.cfg.commands.makeglossaries,
        source=glo,
        dest=gls,
        base=primary.base,
    )
    self.rules.append(rule)
    self._rule_map[name] = rule
```

## Rerun

Same as bibliography: after makeindex produces `.ind`, primary is out-of-date
and reruns automatically.

## Checklist
- [ ] `makeindex` rule added when `.idx` produced
- [ ] `makeglossaries` fallback rule added when `.glo` produced and no cusdep configured
- [ ] After makeindex runs, primary reruns and index appears in PDF
- [ ] `[integration] uv run pytest tests/integration/test_makeindex.py -q --runintegration`
- [ ] `[integration] uv run pytest tests/integration/test_glossaries.py -q --runintegration`
- [ ] Type-clean
