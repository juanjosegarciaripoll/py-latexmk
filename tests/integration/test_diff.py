"""Differential integration tests vs Perl latexmk.

Requires a TeX install and LATEXMK_PERL pointing to the Perl latexmk binary.
Run with: pytest --runintegration --rundiff tests/integration/test_diff.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.differential]

_PERL_LATEXMK = os.environ.get("LATEXMK_PERL", "") or (shutil.which("latexmk") or "")
_SIMPLE_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "simple"
_MULTICHAPTER_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "multichapter"


@pytest.fixture
def workdir_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Create equivalent Python and Perl work directories from the simple fixture."""
    py_dir = tmp_path / "python"
    pl_dir = tmp_path / "perl"
    shutil.copytree(_SIMPLE_FIXTURE, py_dir)
    shutil.copytree(_SIMPLE_FIXTURE, pl_dir)
    return py_dir, pl_dir


@pytest.fixture
def multichapter_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Create equivalent Python and Perl work directories from the multichapter fixture."""
    py_dir = tmp_path / "python-multi"
    pl_dir = tmp_path / "perl-multi"
    shutil.copytree(_MULTICHAPTER_FIXTURE, py_dir)
    shutil.copytree(_MULTICHAPTER_FIXTURE, pl_dir)
    return py_dir, pl_dir


def _run_py(workdir: Path, tex_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "latexmk_py", "-pdf", "-norc", tex_name],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_perl(workdir: Path, tex_name: str) -> subprocess.CompletedProcess[str]:
    if not _PERL_LATEXMK:
        pytest.skip("LATEXMK_PERL is not set")
    return subprocess.run(  # noqa: S603
        [_PERL_LATEXMK, "-pdf", "-norc", tex_name],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_py_args(workdir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "latexmk_py", *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_perl_args(workdir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    if not _PERL_LATEXMK:
        pytest.skip("LATEXMK_PERL is not set")
    return subprocess.run(  # noqa: S603
        [_PERL_LATEXMK, *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


_RULE_RE = re.compile(r'^\["([^"]+)"\]\s+')
_RULE_TAIL_RE = re.compile(
    r'^\["([^"]+)"\]\s+\S+\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+\S+\s+(-?\d+)\s*$'
)
_SOURCE_RE = re.compile(r'^\s+"([^"]+)"\s+\S+\s+\S+\s+(\S+)\s+"([^"]*)"\s*$')
_SIMPLE_FILE_RE = re.compile(r'^\s+"([^"]+)"\s*$')


def _norm_path(p: str) -> str:
    return Path(p.replace("\\", "/")).name


def _normalize_fdb(
    path: Path,
) -> dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]]:
    """Normalize .fdb_latexmk into stable comparable components by rule."""
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].startswith("# Fdb version ")
    current_rule = ""
    sources_by_rule: dict[str, set[str]] = {}
    generated_by_rule: dict[str, set[str]] = {}
    rewritten_by_rule: dict[str, set[str]] = {}
    mode = "source"

    for raw in lines[1:]:
        if raw.startswith("(generated)") or raw.startswith("  (generated)"):
            mode = "generated"
            continue
        if raw.startswith("(rewritten before read)") or raw.startswith("  (rewritten before read)"):
            mode = "rewritten"
            continue
        if raw.startswith("(source)") or raw.startswith("  (source)"):
            mode = "source"
            continue
        if match := _RULE_RE.match(raw):
            current_rule = match.group(1)
            sources_by_rule.setdefault(current_rule, set())
            generated_by_rule.setdefault(current_rule, set())
            rewritten_by_rule.setdefault(current_rule, set())
            continue
        if not current_rule:
            continue
        if mode == "source":
            src_match = _SOURCE_RE.match(raw)
            if src_match:
                file_part, md5, from_rule = src_match.groups()
                entry = f"{_norm_path(file_part)}|{md5}|{from_rule}"
                sources_by_rule[current_rule].add(entry)
        else:
            file_match = _SIMPLE_FILE_RE.match(raw)
            if file_match:
                entry = _norm_path(file_match.group(1))
                if mode == "generated":
                    generated_by_rule[current_rule].add(entry)
                else:
                    rewritten_by_rule[current_rule].add(entry)

    normalized: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {}
    for rule in sources_by_rule:
        normalized[rule] = (
            tuple(sorted(sources_by_rule[rule])),
            tuple(sorted(generated_by_rule[rule])),
            tuple(sorted(rewritten_by_rule[rule])),
        )
    return normalized


def _normalize_depfile(path: Path) -> tuple[str, tuple[str, ...]]:
    """Normalize a Make-format depfile to (target, sorted deps)."""
    lines = [
        line.rstrip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    text = " ".join(lines)
    lhs, rhs = text.split(":", 1)
    target = _norm_path(lhs.strip().rstrip("\\"))
    deps = [token.strip().rstrip("\\") for token in rhs.split() if token.strip().rstrip("\\")]
    norm_deps = tuple(sorted(_norm_path(dep) for dep in deps if dep))
    return target, norm_deps


@pytest.mark.skipif(not _PERL_LATEXMK, reason="LATEXMK_PERL is not set")
def test_simple_pdf_size_close_to_perl(workdir_pair: tuple[Path, Path]) -> None:
    """Produced PDF size should be close to Perl latexmk output for simple fixture."""
    py_dir, pl_dir = workdir_pair
    py_result = _run_py(py_dir, "hello.tex")
    pl_result = _run_perl(pl_dir, "hello.tex")
    assert py_result.returncode == 0, py_result.stderr
    assert pl_result.returncode == 0, pl_result.stderr

    py_size = (py_dir / "hello.pdf").stat().st_size
    pl_size = (pl_dir / "hello.pdf").stat().st_size
    assert abs(py_size - pl_size) / max(py_size, pl_size) < 0.05


@pytest.mark.skipif(not _PERL_LATEXMK, reason="LATEXMK_PERL is not set")
def test_multichapter_outputs_created_in_both(multichapter_pair: tuple[Path, Path]) -> None:
    """Python and Perl both produce expected multichapter output artifacts."""
    py_dir, pl_dir = multichapter_pair
    py_result = _run_py(py_dir, "main.tex")
    pl_result = _run_perl(pl_dir, "main.tex")
    assert py_result.returncode == 0, py_result.stderr
    assert pl_result.returncode == 0, pl_result.stderr

    for stem in ("main", "ch1", "ch2"):
        assert (py_dir / f"{stem}.aux").exists()
        assert (pl_dir / f"{stem}.aux").exists()
    assert (py_dir / "main.pdf").exists()
    assert (pl_dir / "main.pdf").exists()


@pytest.mark.skipif(not _PERL_LATEXMK, reason="LATEXMK_PERL is not set")
def test_fdb_structure_matches_perl_simple(workdir_pair: tuple[Path, Path]) -> None:
    """Normalized .fdb_latexmk rule/source/generated structure matches Perl."""
    py_dir, pl_dir = workdir_pair
    py_result = _run_py(py_dir, "hello.tex")
    pl_result = _run_perl(pl_dir, "hello.tex")
    assert py_result.returncode == 0, py_result.stderr
    assert pl_result.returncode == 0, pl_result.stderr

    py_fdb = py_dir / "hello.fdb_latexmk"
    pl_fdb = pl_dir / "hello.fdb_latexmk"
    assert py_fdb.exists()
    assert pl_fdb.exists()
    assert _normalize_fdb(py_fdb) == _normalize_fdb(pl_fdb)


@pytest.mark.skipif(not _PERL_LATEXMK, reason="LATEXMK_PERL is not set")
def test_depfile_format_matches_perl_simple(workdir_pair: tuple[Path, Path]) -> None:
    """Normalized -M/-MF dependency output matches Perl for simple fixture."""
    py_dir, pl_dir = workdir_pair
    py_result = _run_py_args(py_dir, "-pdf", "-norc", "-M", "-MF", "deps.d", "hello.tex")
    pl_result = _run_perl_args(pl_dir, "-pdf", "-norc", "-M", "-MF", "deps.d", "hello.tex")
    assert py_result.returncode == 0, py_result.stderr
    assert pl_result.returncode == 0, pl_result.stderr

    py_deps = py_dir / "deps.d"
    pl_deps = pl_dir / "deps.d"
    assert py_deps.exists()
    assert pl_deps.exists()
    assert _normalize_depfile(py_deps) == _normalize_depfile(pl_deps)
