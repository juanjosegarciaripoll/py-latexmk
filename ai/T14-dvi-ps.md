# T14: DVI and PostScript Modes
**Status:** `done`
**Depends on:** T08

## Goal
Add support for the remaining build modes:
- `pdf_mode=2`: latex → dvips → ps2pdf
- `pdf_mode=3`: latex → dvipdf
- `dvi_mode=1`: latex → DVI only
- `dvi_mode=2`: dvilualatex → DVI
- `postscript_mode=1`: dvips (from DVI)
- `xdv_mode=1`: xelatex → XDV

These are postprocess rules chained after the primary latex rule.

## Files
- `latexmk_py/rules.py` (extend `init_rules`)
- `latexmk_py/rdb.py` (extend postprocess execution)

## Rule chains

```python
def init_rules(tex: Path, cfg: Config, fdb=None) -> list[Rule]:
    match cfg.build.pdf_mode:
        case 1:
            return [_make_primary(tex, cfg, 'pdflatex', '.pdf')]
        case 2:
            latex = _make_primary(tex, cfg, 'latex', '.dvi')
            dvips = _make_postprocess(tex, cfg, 'dvips', '.dvi', '.ps')
            ps2pdf = _make_postprocess(tex, cfg, 'ps2pdf', '.ps', '.pdf')
            return [latex, dvips, ps2pdf]
        case 3:
            latex = _make_primary(tex, cfg, 'latex', '.dvi')
            dvipdf = _make_postprocess(tex, cfg, 'dvipdf', '.dvi', '.pdf')
            return [latex, dvipdf]
        case 4:
            return [_make_primary(tex, cfg, 'lualatex', '.pdf')]
        case 5:
            primary = _make_primary(tex, cfg, 'xelatex', '.xdv')
            # xelatex produces PDF directly in most configs; xdv is intermediate
            return [primary]
        case _:
            pass

    match cfg.build.dvi_mode:
        case 1:
            return [_make_primary(tex, cfg, 'latex', '.dvi')]
        case 2:
            return [_make_primary(tex, cfg, 'dvilualatex', '.dvi')]

    if cfg.build.postscript_mode:
        latex = _make_primary(tex, cfg, 'latex', '.dvi')
        dvips = _make_postprocess(tex, cfg, 'dvips', '.dvi', '.ps')
        return [latex, dvips]

    raise ConfigError("latexmk: no output mode configured")
```

## Postprocess execution

Postprocess rules run after all primary+secondary rules converge. They are
not subject to the convergence loop — they run once. In `rdb.py build()`:

```python
# After convergence loop:
for rule in [r for r in self.rules if r.kind == 'postprocess']:
    if out_of_date(rule):
        self._run_rule(rule)
        if rule.last_result != 0 and not self.cfg.force:
            return 12
```

Postprocess rules are out-of-date if their source (previous rule's dest) changed.

## Checklist
- [ ] `latexmk -dvi hello.tex` → `hello.dvi`
- [ ] `latexmk -ps hello.tex` → `hello.ps` (via latex+dvips)
- [ ] `latexmk -pdfdvi hello.tex` → `hello.pdf` (via latex+dvips+ps2pdf)
- [ ] `latexmk -pdflua hello.tex` → `hello.pdf` (via lualatex)
- [ ] `latexmk -pdfxe hello.tex` → `hello.pdf` (via xelatex)
- [ ] Second run with no changes: postprocess rules skip
- [ ] DVI change triggers ps2pdf rerun without re-running latex
- [ ] Type-clean
