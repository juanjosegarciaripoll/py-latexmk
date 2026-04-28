"""Tests for viewer.py."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from latexmk_py.config import Config
from latexmk_py.viewer import open_viewer, refresh_viewer, viewer_running

if TYPE_CHECKING:
    from pathlib import Path


def test_open_viewer_returns_none_when_output_missing(tmp_path: Path) -> None:
    assert open_viewer(tmp_path / "missing.pdf", Config()) is None


def test_open_viewer_auto_uses_platform_default(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with (
        patch("latexmk_py.viewer.default_viewer", return_value="xdg-open %S"),
        patch("latexmk_py.viewer.subprocess.Popen") as mock_popen,
    ):
        open_viewer(pdf, Config())
    cmd = cast("list[str]", mock_popen.call_args.args[0])
    assert cmd[0] == "xdg-open"


def test_viewer_running_true_when_poll_none() -> None:
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    try:
        assert viewer_running(proc) is True
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_refresh_viewer_reuses_running_proc(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    cfg = Config()
    try:
        assert refresh_viewer(pdf, proc, cfg) is proc
    finally:
        proc.terminate()
        proc.wait(timeout=5)
