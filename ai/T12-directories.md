# T12: Output & Auxiliary Directories
**Status:** `done`
**Depends on:** T08

## Goal
Support `-outdir` / `-auxdir` / `-out2dir`. Handle the TeXLive emulation
workaround where `pdflatex` ignores `-aux-directory`.

## Files
- `latexmk_py/rdb.py` (extend `_run_rule`, add `_setup_dirs`, `_copy_out2dir`)
- `latexmk_py/platform.py` (add `mkdir_p`)
- `tests/test_rdb.py` (extend)

## Directory logic

```python
def _resolve_paths(self, tex: Path, cfg: Config) -> DirPaths:
    """Compute all working paths given the tex file and config."""
    out_dir  = Path(cfg.directories.out_dir)  if cfg.directories.out_dir  else tex.parent
    aux_dir  = Path(cfg.directories.aux_dir)  if cfg.directories.aux_dir  else out_dir
    out2_dir = Path(cfg.directories.out2_dir) if cfg.directories.out2_dir else None
    return DirPaths(out_dir=out_dir, aux_dir=aux_dir, out2_dir=out2_dir)
```

Create directories before first run:
```python
out_dir.mkdir(parents=True, exist_ok=True)
aux_dir.mkdir(parents=True, exist_ok=True)
```

## Passing dirs to *latex

The primary rule command gets `%Y` (aux dir) and `%Z` (out dir). After
placeholder expansion:
- `-output-directory=<out_dir>` is in the command if `out_dir != tex.parent`
- `-aux-directory=<aux_dir>` is in the command if supported

This is already handled by `%Y` / `%Z` in the command template. The default
pdflatex command template already includes `-output-directory=%Z` when
`out_dir` is set (runner.py expands `%Z`).

Wait — the default command template is `"pdflatex -interaction=nonstopmode %O %S"`.
The `-output-directory` and `-aux-directory` flags must be injected into `%O`
or added explicitly. Approach: build `extra_opts` list that includes these
flags when dirs are set, and runner.py joins them into `%O`.

```python
def _build_extra_opts(self, cfg: Config, dirs: DirPaths, tex: Path) -> list[str]:
    opts = list(cfg.build.latex_extra_options)
    if dirs.out_dir != tex.parent:
        opts += [f'-output-directory={dirs.out_dir}']
    if dirs.aux_dir != dirs.out_dir:
        opts += [f'-aux-directory={dirs.aux_dir}']
    return opts
```

## TeXLive emulation

TeX Live's `pdflatex` does not support `-aux-directory`. After the first run,
check if `.log` appeared in `out_dir` (not `aux_dir`). If aux_dir ≠ out_dir
and `cfg.directories.emulate_aux_dir=True`:

1. Remove `-aux-directory` from `%O`.
2. After each *latex run, move auxiliary files from `out_dir` to `aux_dir`:
   ```python
   AUX_EXTS = {'.aux', '.bbl', '.bcf', '.blg', '.idx', '.ilg',
               '.ind', '.log', '.lof', '.lot', '.toc', '.fls'}
   for p in out_dir.iterdir():
       if p.suffix in AUX_EXTS:
           p.rename(aux_dir / p.name)
   ```
3. Set `TEXINPUTS` and `BIBINPUTS` environment variables to include `aux_dir`
   so that subsequent *latex runs find the moved files.

Detection: after first run, if `(out_dir / f'{base}.log').exists()` and
`aux_dir != out_dir`, emulation is active.

## out2_dir copying

```python
def _copy_out2dir(self, rules: list[Rule], dirs: DirPaths) -> None:
    if dirs.out2_dir is None:
        return
    dirs.out2_dir.mkdir(parents=True, exist_ok=True)
    for rule in rules:
        if rule.kind in ('primary', 'postprocess'):
            for p in [rule.dest] + list(rule.extra_dests):
                if p.exists():
                    shutil.copy2(p, dirs.out2_dir / p.name)
```

## Checklist
- [ ] `latexmk -pdf -outdir=build hello.tex` → PDF in `build/`
- [ ] `latexmk -pdf -auxdir=aux hello.tex` → aux files in `aux/`
- [ ] Emulation: aux files moved after each run when TeXLive doesn't support -aux-directory
- [ ] `out2_dir`: final output copied after successful build
- [ ] Dirs created if they don't exist
- [ ] Type-clean
