"""Integration tests for basic CLI build/cleanup behavior.

Requires pdflatex on PATH (--runintegration).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "simple"


def _run_latexmk(workdir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "latexmk_py", "-pdf", "-norc", *args, "hello.tex"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Copy the simple fixture into a temporary working directory."""
    shutil.copytree(_FIXTURE, tmp_path / "src")
    return tmp_path / "src"


@pytest.mark.integration
def test_simple_build(workdir: Path) -> None:
    """Single build succeeds and produces hello.pdf."""
    result = _run_latexmk(workdir)
    assert result.returncode == 0
    assert (workdir / "hello.pdf").exists()


@pytest.mark.integration
def test_incremental_no_rerun(workdir: Path) -> None:
    """Second unchanged build is a no-op."""
    first = _run_latexmk(workdir)
    second = _run_latexmk(workdir)
    assert first.returncode == 0
    assert second.returncode == 0
    assert "applying rule" not in second.stdout.lower()


@pytest.mark.integration
def test_force_rerun(workdir: Path) -> None:
    """-f forces a rerun even when inputs are unchanged."""
    first = _run_latexmk(workdir)
    second = _run_latexmk(workdir, "-f")
    assert first.returncode == 0
    assert second.returncode == 0
    assert "applying rule" in second.stdout.lower()


@pytest.mark.integration
def test_cleanup_c_keeps_pdf(workdir: Path) -> None:
    """-c removes auxiliary files but keeps the PDF."""
    build = _run_latexmk(workdir)
    clean = subprocess.run(
        [sys.executable, "-m", "latexmk_py", "-c", "-norc", "hello.tex"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0
    assert clean.returncode == 0
    assert (workdir / "hello.pdf").exists()
    assert not (workdir / "hello.aux").exists()
    assert not (workdir / "hello.log").exists()
