# T16: Preview & Continuous Mode (-pv, -pvc)
**Status:** `todo`
**Depends on:** T08, T12

## Goal
Implement `viewer.py` and `rdb.py watch()`: open a PDF/DVI/PS viewer and
watch source files for changes, rebuilding on each change.

## Files
- `latexmk_py/viewer.py`
- `latexmk_py/rdb.py` (add `watch()`)
- `tests/integration/test_pvc.py`

## viewer.py

```python
def open_viewer(output: Path, cfg: Config) -> subprocess.Popen[bytes] | None:
    """Launch viewer for output file; return process handle or None."""

def viewer_running(proc: subprocess.Popen[bytes] | None) -> bool:
    """True if proc is still alive."""

def refresh_viewer(
    output: Path,
    proc: subprocess.Popen[bytes] | None,
    cfg: Config,
) -> subprocess.Popen[bytes] | None:
    """Reuse existing viewer or start a new one."""
```

### Viewer command resolution

`cfg.preview.pdf_previewer` (or dvi/ps) = `"auto"` maps to:
- macOS: `open %S`
- Windows: `start "" %S`
- Linux: `xdg-open %S`

Non-`"auto"` values are used verbatim as a command template (same `%S` etc.).

### Process launch

POSIX:
```python
subprocess.Popen(cmd_list, start_new_session=True,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

Windows:
```python
subprocess.Popen(cmd_list,
                 creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

`viewer_running`: `proc.poll() is None`.

If `cfg.preview.new_viewer_always` is False and `viewer_running(proc)`:
don't launch a new one; the existing viewer detects file changes itself
(e.g. SumatraPDF, Skim).

## watch() — the -pvc loop

```python
def watch(self) -> int:
    rc = self.build()
    if rc != 0 and not self.cfg.force:
        return rc

    output = self._final_output()
    proc = open_viewer(output, self.cfg) if self.cfg.preview_mode else None
    start_time = time.monotonic()

    print(f'Latexmk: Watching for updated files (press Ctrl+C to stop) ...')

    try:
        while True:
            time.sleep(self.cfg.preview.sleep_time)
            if self._any_source_changed():
                rc = self.build()
                if rc == 0 or self.cfg.force:
                    proc = refresh_viewer(output, proc, self.cfg)
            timeout = self.cfg.preview.timeout_mins
            if timeout > 0:
                if time.monotonic() - start_time > timeout * 60:
                    print('Latexmk: Timeout. Exiting.')
                    break
    except KeyboardInterrupt:
        print('\nLatexmk: Interrupt received. Exiting.')

    return 0
```

### Change detection

```python
def _any_source_changed(self) -> bool:
    """Stat all known sources; return True if any size/mtime changed."""
    for rule in self.rules:
        for path in [rule.source] + list(rule.extra_sources):
            if not path.exists():
                continue
            stat = path.stat()
            key = (stat.st_mtime, stat.st_size)
            if self._stat_cache.get(path) != key:
                # Confirm with MD5
                new_md5 = compute_md5(path)
                if new_md5 != rule.source_md5.get(path, ''):
                    return True
                self._stat_cache[path] = key
    return False
```

## Checklist
- [ ] `-pv` opens viewer after single build
- [ ] `-pvc` watches and rebuilds on source change
- [ ] Existing viewer not relaunched if still running (default)
- [ ] `-new-viewer` always launches new viewer
- [ ] `"auto"` maps to correct viewer per platform
- [ ] SIGINT exits cleanly (no traceback)
- [ ] `-pvctimeoutmins=1` exits after 1 minute inactivity
- [ ] `[integration] uv run pytest tests/integration/test_pvc.py -q --runintegration`
- [ ] Type-clean
