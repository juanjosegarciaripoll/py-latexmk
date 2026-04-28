"""RuleDatabase: build loop for latexmk_py.

Mirrors the rdb (rule-database) layer of ``latexmk.pl``
(lines ~3600-3800, 8009-8354).
"""

from __future__ import annotations

import logging
import shutil
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from latexmk_py.deps import write_deps
from latexmk_py.errors import FileMissingError
from latexmk_py.fdb import FdbFileEntry, FdbRule, read_fdb, write_fdb
from latexmk_py.parsers.bcf import parse_bcf
from latexmk_py.parsers.dotaux import parse_aux
from latexmk_py.parsers.fls import parse_fls
from latexmk_py.parsers.log import parse_log
from latexmk_py.rules import Rule, compute_md5, init_rules, out_of_date, topo_sort
from latexmk_py.runner import run_command
from latexmk_py.viewer import open_viewer, refresh_viewer

if TYPE_CHECKING:
    from latexmk_py.config import Config
    from latexmk_py.parsers.dotaux import AuxResult
    from latexmk_py.parsers.log import LogResult

logger = logging.getLogger(__name__)

# Auxiliary file extensions moved to aux_dir during TeX Live emulation.
_AUX_EXTS: frozenset[str] = frozenset(
    {".aux", ".bbl", ".bcf", ".blg", ".idx", ".ilg", ".ind", ".log", ".lof", ".lot", ".toc", ".fls"}
)


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
        self._rule_map: dict[str, Rule] = {}
        self._stat_cache: dict[Path, tuple[float, int]] = {}

    # ------------------------------------------------------------------
    # Private helpers — directory resolution
    # ------------------------------------------------------------------

    def _out_dir(self) -> Path:
        """Resolve out_dir from config; defaults to the .tex file's directory."""
        d = self.cfg.directories.out_dir
        if not d:
            return self.tex.parent
        p = Path(d)
        return p if p.is_absolute() else self.tex.parent / p

    def _aux_dir(self) -> Path:
        """Resolve aux_dir from config; defaults to out_dir when unset."""
        d = self.cfg.directories.aux_dir
        if not d:
            return self._out_dir()
        p = Path(d)
        return p if p.is_absolute() else self.tex.parent / p

    def _out2_dir(self) -> Path | None:
        """Resolve out2_dir from config; returns None when unset."""
        d = self.cfg.directories.out2_dir
        if not d:
            return None
        p = Path(d)
        return p if p.is_absolute() else self.tex.parent / p

    # ------------------------------------------------------------------
    # Private helpers — derived file paths
    # ------------------------------------------------------------------

    def _fdb_path(self) -> Path:
        """Return .fdb_latexmk path (in out_dir when set, else alongside .tex)."""
        name = f"{self.tex.stem}.fdb_latexmk"
        out = self.cfg.directories.out_dir
        return Path(out) / name if out else self.tex.parent / name

    def _aux_path(self, primary: Rule) -> Path:
        """Return the .aux path: in aux_dir when set, else from primary's dest."""
        if self.cfg.directories.aux_dir:
            return self._aux_dir() / f"{primary.base.name}.aux"
        return primary.dest.with_suffix(".aux")

    def _bcf_path(self, primary: Rule) -> Path:
        """Return the .bcf path: in aux_dir when set, else from primary's dest."""
        if self.cfg.directories.aux_dir:
            return self._aux_dir() / f"{primary.base.name}.bcf"
        return primary.dest.with_suffix(".bcf")

    def _log_path(self, rule: Rule) -> Path:
        """Return the .log path: in aux_dir when set, else from rule's dest."""
        if self.cfg.directories.aux_dir:
            return self._aux_dir() / f"{rule.base.name}.log"
        return rule.dest.with_suffix(".log")

    def _fls_path(self, rule: Rule) -> Path:
        """Return the .fls path: in aux_dir when set, else from rule's dest."""
        if self.cfg.directories.aux_dir:
            return self._aux_dir() / f"{rule.base.name}.fls"
        return rule.dest.with_suffix(".fls")

    # ------------------------------------------------------------------
    # Private helpers — command options and working directory
    # ------------------------------------------------------------------

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
        # -aux-directory is a MiKTeX extension; skip when emulating (TeX Live).
        if not self.cfg.directories.emulate_aux_dir:
            aux = self.cfg.directories.aux_dir.replace("\\", "/")
            if aux and rule.kind in ("primary", "postprocess"):
                opts.append(f"-aux-directory={aux}")
        # latex_extra_options are for *latex only, not bibtex/biber/makeindex.
        if rule.kind in ("primary", "postprocess"):
            opts.extend(self.cfg.build.latex_extra_options)
        return opts

    def _rule_cwd(self, rule: Rule) -> Path | None:
        """Return the working directory for running *rule*.

        Secondary rules run from the .tex directory so tools like bibtex and
        makeindex can write outputs using relative paths under TeX's
        ``openout_any = p`` restrictions.
        """
        if self.cfg.build.cd:
            return self.tex.parent
        if rule.kind == "secondary":
            return self.tex.parent
        return None

    @staticmethod
    def _rel_if_under(path: Path, cwd: Path | None) -> Path:
        """Return path relative to cwd when possible; else unchanged absolute path."""
        if cwd is None:
            return path
        try:
            return path.relative_to(cwd)
        except ValueError:
            return path

    # ------------------------------------------------------------------
    # Private helpers — .bib resolution
    # ------------------------------------------------------------------

    def _resolve_bib_files(self, bib_names: frozenset[str]) -> set[Path]:
        """Return the subset of *bib_names* found alongside the .tex source."""
        found: set[Path] = set()
        for name in bib_names:
            p = self.tex.parent / name
            if p.exists():
                found.add(p)
        return found

    # ------------------------------------------------------------------
    # Private helpers — secondary rule management
    # ------------------------------------------------------------------

    def _ensure_bibtex_rule(self, primary: Rule, aux: AuxResult) -> None:
        """Register a bibtex secondary rule if one is not already present.

        Mirrors ``rdb_add_generated_bibtex_rule`` in ``latexmk.pl``
        (lines ~9550-9620).
        """
        name = f"bibtex_{primary.base.name}"
        if name in self._rule_map:
            return
        bib_paths = self._resolve_bib_files(aux.bib_files)
        # use == 1.0: skip if .bib files are not accessible on disk.
        # use >= 1.5: add rule even without .bib (use existing .bbl).
        _use_requires_bib = 1.5
        if self.cfg.bibtex.use < _use_requires_bib and not bib_paths:
            return
        # .bbl goes to the .tex directory: bibtex writes to its cwd.
        bbl = self.tex.parent / f"{primary.base.name}.bbl"
        rule = Rule(
            name=name,
            kind="secondary",
            command=self.cfg.commands.bibtex,
            source=self._aux_path(primary),
            dest=bbl,
            base=primary.base,
        )
        rule.extra_sources.update(bib_paths)
        self.rules.append(rule)
        self._rule_map[name] = rule

    def _ensure_biber_rule(self, primary: Rule, bcf_path: Path) -> None:
        """Register a biber secondary rule if one is not already present.

        Mirrors ``rdb_add_generated_biber_rule`` in ``latexmk.pl``
        (lines ~9620-9680).
        """
        name = f"biber_{primary.base.name}"
        if name in self._rule_map:
            return
        bcf_result = parse_bcf(bcf_path)
        bbl = self.tex.parent / f"{primary.base.name}.bbl"
        rule = Rule(
            name=name,
            kind="secondary",
            command=self.cfg.commands.biber,
            source=bcf_path,
            dest=bbl,
            base=primary.base,
        )
        rule.extra_sources.update(self._resolve_bib_files(bcf_result.data_sources))
        self.rules.append(rule)
        self._rule_map[name] = rule

    def _maybe_add_makeindex_rule(self, primary: Rule) -> None:
        """Register a makeindex rule when the primary produced a .idx file.

        Mirrors the makeindex trigger in ``latexmk.pl`` (lines ~9700-9730).
        """
        idx = self._aux_path(primary).with_suffix(".idx")
        if not idx.exists():
            return
        name = f"makeindex_{primary.base.name}"
        if name in self._rule_map:
            return
        rule = Rule(
            name=name,
            kind="secondary",
            command=self.cfg.commands.makeindex,
            source=idx,
            dest=idx.with_suffix(".ind"),
            base=primary.base,
        )
        self.rules.append(rule)
        self._rule_map[name] = rule

    def _has_gls_cusdep(self) -> bool:
        """Return True if a custom dependency already covers glo→gls."""
        return any(cd.from_ext == "glo" and cd.to_ext == "gls" for cd in self.cfg.custom_deps)

    def _maybe_add_glossaries_rule(self, primary: Rule) -> None:
        """Register a makeglossaries fallback when .glo exists and no cusdep covers it.

        Mirrors the glossaries fallback in ``latexmk.pl`` (lines ~9730-9760).
        """
        glo = self._aux_path(primary).with_suffix(".glo")
        if not glo.exists():
            return
        if self._has_gls_cusdep():
            return  # cusdep (T11) will handle this
        name = f"makeglossaries_{primary.base.name}"
        if name in self._rule_map:
            return
        rule = Rule(
            name=name,
            kind="secondary",
            command=self.cfg.commands.makeglossaries,
            source=glo,
            dest=glo.with_suffix(".gls"),
            base=primary.base,
        )
        self.rules.append(rule)
        self._rule_map[name] = rule

    def _add_secondary_rules(self, primary: Rule) -> None:
        """Detect and register all secondary rules after a primary run.

        Bibliography (bibtex/biber), index, and glossaries are independent;
        index/glossaries fire regardless of bibtex.use.
        Mirrors secondary-rule triggers in ``latexmk.pl`` (lines ~9540-9760).
        """
        if self.cfg.bibtex.use != 0.0:
            bcf_path = self._bcf_path(primary)
            if bcf_path.exists() and bcf_path.stat().st_size > 0:
                self._ensure_biber_rule(primary, bcf_path)
            elif (aux := parse_aux(self._aux_path(primary))).bib_files:
                self._ensure_bibtex_rule(primary, aux)
        self._maybe_add_makeindex_rule(primary)
        self._maybe_add_glossaries_rule(primary)

    def _add_cusdep_rules(self, primary: Rule, log: LogResult) -> None:
        """Create cusdep rules for missing files that match a configured custom dependency.

        Mirrors ``rdb_check_for_cusdep`` in ``latexmk.pl`` (lines ~9800-9870).
        """
        for missing in log.missing_files:
            stem = Path(missing).stem
            for cusdep in self.cfg.custom_deps:
                if not missing.endswith(f".{cusdep.to_ext}"):
                    continue
                source = primary.source.parent / f"{stem}.{cusdep.from_ext}"
                dest = primary.source.parent / f"{stem}.{cusdep.to_ext}"
                if not source.exists():
                    if cusdep.must:
                        raise FileMissingError(f"latexmk: custom dep source not found: {source}")
                    continue
                name = f"cusdep_{cusdep.from_ext}_{cusdep.to_ext}_{stem}"
                if name in self._rule_map:
                    continue
                rule = Rule(
                    name=name,
                    kind="cusdep",
                    command=cusdep.command,
                    source=source,
                    dest=dest,
                    base=primary.source.parent / stem,
                )
                self.rules.append(rule)
                self._rule_map[name] = rule

    def _mark_primary_stale(self, secondary: Rule) -> None:
        """Mark primary rules stale after a secondary or cusdep rule produces output.

        Ensures pdflatex reruns to incorporate the fresh generated file.
        """
        for r in self.rules:
            if r.kind == "primary" and r.base == secondary.base:
                r.out_of_date = True

    # ------------------------------------------------------------------
    # Private helpers — directory setup and file movement
    # ------------------------------------------------------------------

    def _setup_dirs(self) -> None:
        """Create out_dir, aux_dir, and out2_dir before the first rule runs."""
        self._out_dir().mkdir(parents=True, exist_ok=True)
        if self.cfg.directories.aux_dir:
            self._aux_dir().mkdir(parents=True, exist_ok=True)
        out2 = self._out2_dir()
        if out2 is not None:
            out2.mkdir(parents=True, exist_ok=True)

    def _emulate_aux_dir(self) -> None:
        """Move auxiliary files from out_dir to aux_dir after a primary run.

        Mirrors the TeX Live aux-dir emulation in ``latexmk.pl``
        (``$emulate_aux_dir``, lines ~4800-4850).  TeX Live's pdflatex ignores
        ``-aux-directory`` so we move the files ourselves after each run.
        """
        if not self.cfg.directories.aux_dir or not self.cfg.directories.emulate_aux_dir:
            return
        out = self._out_dir()
        aux = self._aux_dir()
        if out == aux:
            return
        for p in list(out.iterdir()):
            if p.suffix in _AUX_EXTS:
                p.rename(aux / p.name)

    def _copy_out2dir(self) -> None:
        """Copy primary/postprocess output files to out2_dir after a build.

        Mirrors ``copy_files_to_out2`` in ``latexmk.pl``.
        """
        out2 = self._out2_dir()
        if out2 is None:
            return
        out2.mkdir(parents=True, exist_ok=True)
        for rule in self.rules:
            if rule.kind in ("primary", "postprocess"):
                for p in [rule.dest, *rule.extra_dests]:
                    if p.exists():
                        shutil.copy2(p, out2 / p.name)

    # ------------------------------------------------------------------
    # Private helpers — run and dependency update
    # ------------------------------------------------------------------

    def _run_rule(self, rule: Rule) -> None:
        """Execute *rule*, stream subprocess output, and update rule state.

        Mirrors ``Run_rule`` in ``latexmk.pl`` (lines ~9800-9950).
        """
        if not self.cfg.output.silent:
            print(f"Latexmk: applying rule '{rule.name}'...")  # noqa: T201

        cwd = self._rule_cwd(rule)
        source = self._rel_if_under(rule.source, cwd)
        dest = self._rel_if_under(rule.dest, cwd)
        root = self._rel_if_under(self.tex, cwd)
        main_tex = self._rel_if_under(self.tex, cwd)

        result = run_command(
            rule.command,
            source=source,
            dest=dest,
            base=rule.base,
            root=root,
            main_tex=main_tex,
            extra_opts=self._build_extra_opts(rule),
            aux_dir=self.cfg.directories.aux_dir,
            out_dir=self.cfg.directories.out_dir,
            cwd=cwd,
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

        # TeX Live emulation: move aux files to aux_dir after each primary run.
        if rule.kind == "primary":
            self._emulate_aux_dir()

    def _update_deps(self, rule: Rule) -> None:
        """Parse .fls / .log (primary) or mark primaries stale (secondary/cusdep).

        Mirrors ``rdb_set_dependences`` in ``latexmk.pl`` (lines ~9350-9550).
        """
        if rule.kind == "primary":
            self._update_primary_deps(rule)
            self._add_secondary_rules(rule)
        elif rule.kind in ("secondary", "cusdep"):
            self._mark_primary_stale(rule)

    def _update_primary_deps(self, rule: Rule) -> None:
        """Parse .fls and .log to update a primary rule's dependency sets."""
        if self.cfg.build.recorder:
            fls_result = parse_fls(self._fls_path(rule))
            tex_dir = self.tex.parent
            for p in fls_result.inputs:
                rule.extra_sources.add(p if p.is_absolute() else tex_dir / p)
            rule.extra_dests.update(fls_result.outputs)

        log_result = parse_log(self._log_path(rule))
        if log_result.rerun_needed:
            rule.out_of_date = True
        if self.cfg.custom_deps:
            self._add_cusdep_rules(rule, log_result)

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

    def _run_convergence_loop(self, fdb_path: Path) -> int | None:
        """Run primary/secondary/cusdep rules to convergence; return 12 on failure.

        Postprocess rules are deliberately excluded: they run once after this
        loop settles.  Mirrors ``Run_all_rules`` in ``latexmk.pl`` (lines ~3600).
        """
        force = self.cfg.force
        for _iteration in range(self.cfg.build.max_runs):
            stale = [
                r
                for r in self.rules
                if r.kind != "postprocess" and (r.out_of_date or out_of_date(r, force=force))
            ]
            if not stale:
                return None  # converged cleanly
            for rule in topo_sort(stale):
                self._run_rule(rule)
                if rule.last_result != 0 and not force:
                    write_fdb(fdb_path, self._rules_to_fdb())
                    return 12
                self._update_deps(rule)
        logger.warning(
            "latexmk: did not converge after %d runs",
            self.cfg.build.max_runs,
        )
        return None

    def _run_postprocess(self, fdb_path: Path) -> int | None:
        """Run postprocess rules once after primary convergence; return 12 on failure.

        Postprocess rules (dvips, ps2pdf, xdvipdfmx …) run at most once per
        build; they are stale when their source (the primary's output) changed.
        Mirrors the post-convergence step in ``latexmk.pl`` (lines ~3800-3820).
        """
        force = self.cfg.force
        for rule in (r for r in self.rules if r.kind == "postprocess"):
            if rule.out_of_date or out_of_date(rule, force=force):
                self._run_rule(rule)
                if rule.last_result != 0 and not force:
                    write_fdb(fdb_path, self._rules_to_fdb())
                    return 12
        return None

    def _final_output(self) -> Path:
        """Return final output path for the current build mode."""
        suffix = ".pdf"
        if self.cfg.build.pdf_mode == 0:
            if self.cfg.build.postscript_mode:
                suffix = ".ps"
            elif self.cfg.build.dvi_mode:
                suffix = ".dvi"
        return self._out_dir() / f"{self.tex.stem}{suffix}"

    def _any_source_changed(self) -> bool:
        """Stat known sources and confirm changed candidates via MD5."""
        for rule in self.rules:
            for path in [rule.source, *rule.extra_sources]:
                if not path.exists():
                    continue
                stat = path.stat()
                key = (stat.st_mtime, stat.st_size)
                if self._stat_cache.get(path) == key:
                    continue
                old_md5 = rule.source_md5.get(path, "")
                new_md5 = compute_md5(path)
                self._stat_cache[path] = key
                if new_md5 != old_md5:
                    return True
        return False

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
        self._rule_map = {r.name: r for r in self.rules}
        self._setup_dirs()

        if not self.rules:
            logger.warning("latexmk: no rules to run for %s", self.tex)
            return 0

        if (rc := self._run_convergence_loop(fdb_path)) is not None:
            return rc
        if (rc := self._run_postprocess(fdb_path)) is not None:
            return rc

        write_fdb(fdb_path, self._rules_to_fdb())
        self._copy_out2dir()
        if self.cfg.deps.enabled:
            write_deps(self.rules, self.cfg.deps, self.tex)
        return 0

    def watch(self) -> int:
        """Run -pvc continuous-preview loop (implemented in T16).

        Mirrors the pvc loop in ``latexmk.pl`` (lines ~4000-4200).
        """
        rc = self.build()
        if rc != 0 and not self.cfg.force:
            return rc

        output = self._final_output()
        proc = open_viewer(output, self.cfg) if self.cfg.preview_mode else None
        start_time = time.monotonic()
        print("Latexmk: Watching for updated files (press Ctrl+C to stop) ...")  # noqa: T201

        try:
            while True:
                time.sleep(self.cfg.preview.sleep_time)
                if self._any_source_changed():
                    rc = self.build()
                    if rc == 0 or self.cfg.force:
                        proc = refresh_viewer(output, proc, self.cfg)
                    elif not self.cfg.force:
                        return rc
                timeout = self.cfg.preview.timeout_mins
                if timeout > 0 and time.monotonic() - start_time > timeout * 60:
                    print("Latexmk: Timeout. Exiting.")  # noqa: T201
                    break
        except KeyboardInterrupt:
            print("\nLatexmk: Interrupt received. Exiting.")  # noqa: T201

        return 0
