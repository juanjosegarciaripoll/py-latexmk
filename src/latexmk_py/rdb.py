"""RuleDatabase: build loop for latexmk_py.

Mirrors the rdb (rule-database) layer of ``latexmk.pl``
(lines ~3600-3800, 8009-8354).
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from latexmk_py.errors import FileMissingError
from latexmk_py.fdb import FdbFileEntry, FdbRule, read_fdb, write_fdb
from latexmk_py.parsers.fls import parse_fls
from latexmk_py.parsers.log import parse_log
from latexmk_py.rules import compute_md5, init_rules, out_of_date, topo_sort
from latexmk_py.runner import run_command

if TYPE_CHECKING:
    from latexmk_py.config import Config
    from latexmk_py.rules import Rule

logger = logging.getLogger(__name__)


def _file_stat(p: Path) -> tuple[float, int]:
    """Return (mtime, size) for *p*, or (0.0, 0) on any OS error."""
    try:
        st = p.stat()
    except OSError:
        return 0.0, 0
    else:
        return st.st_mtime, st.st_size


class RuleDatabase:
    """Driver for the latexmk build and watch loops.

    Mirrors the rdb_* family of functions in ``latexmk.pl`` that coordinate
    rule execution, convergence detection, and ``.fdb_latexmk`` persistence
    (lines 3600-3800, 8009-8354).
    """

    def __init__(self, tex: Path, cfg: Config) -> None:
        """Initialise the database for *tex* with configuration *cfg*."""
        self.tex = tex
        self.cfg = cfg
        self.rules: list[Rule] = []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fdb_path(self) -> Path:
        """Return .fdb_latexmk path (in out_dir when set, else alongside .tex)."""
        name = f"{self.tex.stem}.fdb_latexmk"
        out = self.cfg.directories.out_dir
        return Path(out) / name if out else self.tex.parent / name

    def _build_extra_opts(self, rule: Rule) -> list[str]:
        """Assemble extra CLI options for a rule invocation."""
        opts: list[str] = []
        if rule.kind == "primary" and self.cfg.build.recorder:
            opts.append("-recorder")
        # Normalise to forward slashes: TeX accepts / on all platforms and
        # shlex.quote wraps backslash-containing paths in POSIX single quotes
        # which TeX's kpathsea does not strip.
        out = self.cfg.directories.out_dir.replace("\\", "/")
        if out and rule.kind in ("primary", "postprocess"):
            opts.append(f"-output-directory={out}")
        opts.extend(self.cfg.build.latex_extra_options)
        return opts

    def _run_rule(self, rule: Rule) -> None:
        """Execute *rule*, stream subprocess output, and update rule state.

        Mirrors ``Run_rule`` in ``latexmk.pl`` (lines ~9800-9950).
        """
        if not self.cfg.output.silent:
            print(f"Latexmk: applying rule '{rule.name}'...")  # noqa: T201

        result = run_command(
            rule.command,
            source=rule.source,
            dest=rule.dest,
            base=rule.base,
            root=self.tex,
            main_tex=self.tex,
            extra_opts=self._build_extra_opts(rule),
            aux_dir=self.cfg.directories.aux_dir,
            out_dir=self.cfg.directories.out_dir,
            cwd=self.tex.parent if self.cfg.build.cd else None,
        )

        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)

        rule.last_result = result.exit_code
        rule.run_time = time.time()
        rule.last_message = result.stderr[-500:] if result.stderr else ""
        rule.out_of_date = False

        # Always track the primary source so content changes trigger reruns.
        if rule.source.exists():
            rule.source_md5[rule.source] = compute_md5(rule.source)

        for p in [rule.dest, *rule.extra_dests]:
            if p.exists():
                rule.dest_md5[p] = compute_md5(p)

    def _update_deps(self, rule: Rule) -> None:
        """Parse .fls and .log to update discovered dependency sets.

        Mirrors ``rdb_set_dependences`` in ``latexmk.pl`` (lines ~9350-9550).
        """
        if self.cfg.build.recorder:
            fls_path = rule.dest.with_suffix(".fls")
            fls_result = parse_fls(fls_path)
            tex_dir = self.tex.parent
            for p in fls_result.inputs:
                rule.extra_sources.add(p if p.is_absolute() else tex_dir / p)
            rule.extra_dests.update(fls_result.outputs)

        log_path = rule.dest.with_suffix(".log")
        log_result = parse_log(log_path)
        if log_result.rerun_needed:
            rule.out_of_date = True

        for p in rule.extra_sources:
            if p.exists():
                rule.source_md5[p] = compute_md5(p)

    def _rules_to_fdb(self) -> dict[str, FdbRule]:
        """Snapshot current rules as an FdbRule mapping for persistence."""
        now = time.time()
        result: dict[str, FdbRule] = {}
        for rule in self.rules:
            files: list[FdbFileEntry] = []
            for p, md5 in rule.source_md5.items():
                mtime, size = _file_stat(p)
                files.append(FdbFileEntry(path=p, mtime=mtime, size=size, md5=md5, from_rule=""))
            result[rule.name] = FdbRule(
                name=rule.name,
                run_time=rule.run_time,
                source=rule.source,
                dest=rule.dest,
                base=rule.base,
                check_time=now,
                last_result=rule.last_result,
                files=files,
                generated=list(rule.extra_dests),
            )
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> int:
        """Run full build loop; return exit code (0=success, 12=error).

        Mirrors the main convergence loop in ``latexmk.pl`` (lines ~3600-3800).
        """
        if not self.tex.exists():
            raise FileMissingError(f"latexmk: file not found: {self.tex}")

        fdb_path = self._fdb_path()
        fdb = read_fdb(fdb_path)
        self.rules = init_rules(self.tex, self.cfg, fdb)

        if not self.rules:
            logger.warning("latexmk: no rules to run for %s", self.tex)
            return 0

        for _iteration in range(self.cfg.build.max_runs):
            stale = [r for r in self.rules if r.out_of_date or out_of_date(r, force=self.cfg.force)]
            if not stale:
                break
            for rule in topo_sort(stale):
                self._run_rule(rule)
                if rule.last_result != 0 and not self.cfg.force:
                    write_fdb(fdb_path, self._rules_to_fdb())
                    return 12
                self._update_deps(rule)
        else:
            logger.warning(
                "latexmk: did not converge after %d runs",
                self.cfg.build.max_runs,
            )

        write_fdb(fdb_path, self._rules_to_fdb())
        return 0

    def watch(self) -> int:
        """Run -pvc continuous-preview loop (implemented in T16).

        Mirrors the pvc loop in ``latexmk.pl`` (lines ~4000-4200).
        """
        raise NotImplementedError("latexmk: -pvc not yet implemented (T16)")
