# T09: Bibliography (BibTeX + Biber)
**Status:** `todo`
**Depends on:** T08

## Goal
Extend `rdb.py` to automatically detect and run bibtex or biber when needed.
This is the most common secondary-rule use case.

## Files
- `latexmk_py/rdb.py` (extend `_update_deps`, add `_add_secondary_rules`)
- `tests/test_rdb.py` (extend)
- `tests/fixtures/biblatex/` — .tex + .bib using BibLaTeX/Biber
- `tests/fixtures/bibtex/` — .tex + .bib using classic BibTeX
- `tests/integration/test_bibtex.py`
- `tests/integration/test_biber.py`

## Fixtures

**tests/fixtures/bibtex/**
```latex
% main.tex
\documentclass{article}
\begin{document}
\cite{ref1}
\bibliographystyle{plain}
\bibliography{refs}
\end{document}
```
```bibtex
% refs.bib
@article{ref1, author={A. Author}, title={A Title}, year={2020}, journal={J}}
```

**tests/fixtures/biblatex/**
```latex
% main.tex
\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
\cite{ref1}
\printbibliography
\end{document}
```
Same `refs.bib`.

## Detection logic

After parsing `.aux` with `parse_aux()` and `.bcf` with `parse_bcf()`:

```python
def _add_secondary_rules(self, primary: Rule) -> None:
    aux_path = self._aux_path(primary)
    aux = parse_aux(aux_path)
    bcf_path = self._bcf_path(primary)

    if bcf_path.exists() and bcf_path.stat().st_size > 0:
        self._ensure_biber_rule(primary, bcf_path)
    elif aux.bib_files:
        self._ensure_bibtex_rule(primary, aux)
```

`cfg.bibtex.use` controls whether to actually run:
- `0`: never add bibtex/biber rules
- `1` (default): add rule only if `.bib` files are accessible on disk
- `1.5`: add rule; treat `.bbl` as precious if `.bib` not found
- `2`: always add rule when bibliography detected

## bibtex rule

```python
def _ensure_bibtex_rule(self, primary: Rule, aux: AuxResult) -> None:
    name = f"bibtex_{primary.base.name}"
    if name in self._rule_map:
        return
    # resolve .bib paths: kpsewhich or search alongside .tex
    bib_paths = self._resolve_bib_files(aux.bib_files)
    if cfg.bibtex.use == 1 and not bib_paths:
        return  # .bib not found, skip
    bbl = self._aux_path(primary).with_suffix('.bbl')
    rule = Rule(
        name=name,
        kind='secondary',
        command=cfg.commands.bibtex,
        source=self._aux_path(primary).with_suffix('.aux'),
        dest=bbl,
        base=primary.base,
    )
    rule.extra_sources.update(bib_paths)
    self.rules.append(rule)
    self._rule_map[name] = rule
```

If `cfg.bibtex.fudge` is True, run bibtex with `cwd` set to the aux dir
(so bibtex can find .bib files without full paths).

## biber rule

```python
def _ensure_biber_rule(self, primary: Rule, bcf_path: Path) -> None:
    name = f"biber_{primary.base.name}"
    if name in self._rule_map:
        return
    bcf_result = parse_bcf(bcf_path)
    bbl = bcf_path.with_suffix('.bbl')
    rule = Rule(
        name=name,
        kind='secondary',
        command=cfg.commands.biber,
        source=bcf_path,
        dest=bbl,
        base=primary.base,
    )
    rule.extra_sources.update(
        self._resolve_bib_files(bcf_result.data_sources)
    )
    self.rules.append(rule)
    self._rule_map[name] = rule
```

## Rerun logic

After bibtex/biber runs and produces/updates `.bbl`, the primary rule is
marked out-of-date (source `.bbl` changed) and reruns automatically in the
next iteration. No special handling needed — it falls out of the out-of-date
detection in T07.

## Checklist
- [ ] bibtex rule added when `\bibdata` found in `.aux` and `.bib` exists
- [ ] bibtex NOT run when `bibtex.use=0`
- [ ] biber rule added when `.bcf` non-empty
- [ ] bibtex runs with `cwd=aux_dir` when `bibtex.fudge=True`
- [ ] After bibtex run, primary reruns (because `.bbl` changed)
- [ ] Final PDF contains bibliography
- [ ] `[integration] uv run pytest tests/integration/test_bibtex.py -q --runintegration`
- [ ] `[integration] uv run pytest tests/integration/test_biber.py -q --runintegration`
- [ ] Type-clean
