# AGENTS.md — Conventions for this repository

Source of truth for developing, testing, and shipping the Python port of `latexmk`.
Applies to human contributors and automated agents. Read before making changes; obey strictly.

Spec: [`PLAN.md`](./PLAN.md). Task files: [`ai/`](./ai/). Reference impl: [`latexmk/latexmk.pl`](./latexmk/latexmk.pl) (read-only). Reference manual: [`latexmk/latexmk.1`](./latexmk/latexmk.1) (read-only). Never modify anything under `latexmk/`.

## 0. Active Task

<!-- AGENTS: update this block when starting or finishing a task -->
**Current task:** T16 — Preview & -pvc
**Task file:** [`ai/T16-preview-pvc.md`](./ai/T16-preview-pvc.md)
**Status:** `todo`

Before starting: read `PLAN.md` for overall structure, then the task file above (interfaces, requirements, checklist). Read `ai/config-schema.md` if the task touches configuration. Verify all **Depends on** tasks are `done`.

When finishing or switching tasks: set **Status** to `in-progress` while working, `done` when the checklist passes. Mirror the status change in the task file's own `**Status:**` line and in the `PLAN.md` task table. Advance **Current task** to the next entry.

Task order: T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18

## 1. Goal

Re-implement `latexmk.pl` in Python with **zero runtime third-party dependencies** (stdlib only). Match Perl's user-visible behavior. Document divergences in `CHANGES.md`.

Runtime: `python >= 3.13`. Dev tooling may use third-party packages.

## 2. Toolchain

All tooling via [`uv`](https://docs.astral.sh/uv/). Never use `pip`, `python -m venv`, `pyenv`, `poetry`, or `pip-tools`.

| Purpose | Invocation |
|---|---|
| Env / deps / lock | `uv sync`, `uv lock`, `uv add` |
| Format + lint + fix | `uv run ruff format && uv run ruff check --fix` |
| Type check | `uv run basedpyright` and `uv run mypy .` (both must pass) |
| Tests | `uv run pytest -q` |

Two type checkers: basedpyright is strict/fast/IDE-friendly; mypy catches stdlib edge cases that differ.

First-time setup: `uv sync --all-extras --dev`

Adding a dependency:
- Runtime: **don't.** Pure stdlib is the goal. Argue in a PR if genuinely needed.
- Dev: `uv add --dev <pkg>` — commit `pyproject.toml` + `uv.lock` together.
- Optional feature: `uv add --optional process <pkg>` — code must `try/except ImportError` and degrade gracefully.

## 3. Quality Gates

Run and pass all before every commit:
```bash
uv run ruff format
uv run ruff check --fix
uv run basedpyright
uv run mypy .
uv run pytest -q
```
Never disable a check to make the pipeline pass. Fix the root cause.

`pyproject.toml` holds all tool config. Do not change it without a separate `chore(config):` commit.

## 4. Coding Standards

**Types:** strictly typed; `from __future__ import annotations` in every module; `Path` not `str` for filesystem paths; `Mapping`/`Sequence` for read-only inputs; `Literal[...]` for enum-shaped strings; `dataclass`/`TypedDict`/`NamedTuple` for records; no `Any`; no `# type: ignore` without `# type: ignore[error-code]  # reason`.

**Style:** Python 3.13 (`match`, PEP 695 type params, `type X = ...`); `dataclass(slots=True, frozen=True)` for records; composition over inheritance; one public class/function-group per module; `pathlib.Path` everywhere; `subprocess.run([...], check=False)` — never `shell=True` except in `runner.py`; `print()` for user output, `logging` for diagnostics; `encoding="utf-8"` on all file I/O.

**Errors** — hierarchy in `src/latexmk_py/errors.py`:
```
LatexmkError(Exception)
  ConfigError       # exit 13
  BadOptionsError   # exit 10
  FileMissingError  # exit 11
  BuildError        # exit 12
  InternalError     # exit 20
```
Never `except Exception:` except in top-level `main()`. Messages start with `latexmk:`.

**Docstrings:** one-line summary, blank line, optional details. Always cite the Perl source:
```python
def parse_fls(path: Path) -> FlsResult:
    """Parse a *.fls* recorder file.

    Mirrors ``parse_fls`` in ``latexmk.pl`` (lines 7153–7387).
    """
```

## 5. Tests

- Unit: `tests/test_<module>.py`
- Integration (needs TeX): `tests/integration/test_<scenario>.py` — run with `--runintegration`
- Fixtures: `tests/fixtures/<category>/`
- Target ≥ 90% line coverage on `src/latexmk_py/` (excluding `cli.py` and `__main__.py`)
- Differential vs Perl: `LATEXMK_PERL=/usr/bin/latexmk uv run pytest tests/integration/test_diff.py`
- Perl bug that we diverge from: write a test, document in `CHANGES.md`, add to `known_divergences.py`

## 6. CI Gates

1. `uv sync --all-extras --dev`
2. `uv run ruff format --check .`
3. `uv run ruff check .`
4. `uv run basedpyright`
5. `uv run mypy .`
6. `uv run pytest -q --cov=latexmk_py --cov-fail-under=85`

Red CI blocks merge.

## 7. Workflow

1. Check **§0 Active Task** — confirm the right task and its dependencies are done.
2. Read the task file (`ai/TXX-*.md`). Implement exactly what the checklist requires; nothing more.
3. Read `latexmk.pl` and `latexmk.1` for the relevant subroutine. Cite line numbers in commit messages.
4. Write or update tests first. Use fixtures for inputs > ~5 lines.
5. Implement in small, type-clean increments.
6. Run the full local pipeline (§3).
7. Update `CHANGES.md` with a one-line user-facing summary.
8. Commit: `feat(parser): port parse_fls` / `fix(rules): handle epstopdf cusdep` / `chore(deps): bump ruff`. No LLM attribution in commit messages (no `Co-Authored-By:` or similar lines).
9. Mark task `done`: update §0, the task file, and the `PLAN.md` table. Advance to next task.

## 8. Performance

- No re-reading the same file twice. Cache per-build in `Config`/`BuildState`, never module globals.
- No global mutable state. Replace Perl `our $foo` with `BuildState` passed explicitly.
- MD5: `hashlib.file_digest` (3.11+) with `BufferedReader`. No full-file reads.
- `.fdb_latexmk`: line-by-line parsing.
- All subprocess calls go through `runner.py`.

## 9. Security

- Never `shell=True` outside `runner.py`. Inside `runner.py`: `shlex.split` → `subprocess.run([...], shell=False)`. Fall back to `shell=True` only for user commands containing `|`/`&&` — document it.
- Never interpolate untrusted strings into a shell. Filenames from `.log`/`.fls` are untrusted.
- The TOML config parser accepts only the declared schema; never eval/exec user-supplied strings.

## 10. Non-Goals

No output-byte-identity with Perl latexmk except `--help`, `--version`, `-commands`, and `.fdb_latexmk`. No embedded Perl interpreter. No Python < 3.13. No `latexmk.pl` subprocess fallback. No vendored third-party packages.

## 11. When in Doubt

1. Re-read `PLAN.md` and the relevant `latexmk.1` section.
2. Check `latexmk.pl` for the subroutine; obey its semantics over your intuition.
3. Perl genuinely buggy: write a test, document under "Intentional divergences" in `CHANGES.md`, proceed.
4. Still unsure: leave `TODO(name): question` and open a discussion. Don't silently guess.
