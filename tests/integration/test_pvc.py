"""Integration tests for -pv / -pvc behavior."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from latexmk_py.config import Config, DirectoriesConfig
from latexmk_py.rdb import RuleDatabase

_FIXTURES_SIMPLE = Path(__file__).resolve().parents[1] / "fixtures" / "simple"


@pytest.mark.integration
def test_pv_opens_viewer_after_build(tmp_path: Path) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(directories=DirectoriesConfig(out_dir=str(tmp_path)), preview_mode=True)
    rdb = RuleDatabase(tex, cfg)
    with (
        patch("latexmk_py.rdb.open_viewer", return_value=None) as mock_open,
        patch.object(rdb, "_any_source_changed", side_effect=KeyboardInterrupt),
    ):
        assert rdb.watch() == 0
    assert mock_open.call_count == 1


@pytest.mark.integration
def test_pvc_timeout_minutes_exits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = _FIXTURES_SIMPLE / "hello.tex"
    tex = tmp_path / "hello.tex"
    shutil.copy(src, tex)
    cfg = Config(
        directories=DirectoriesConfig(out_dir=str(tmp_path)),
        preview=replace(Config().preview, sleep_time=0.01, timeout_mins=0.0005),
    )
    assert RuleDatabase(tex, cfg).watch() == 0
    assert "Timeout. Exiting." in capsys.readouterr().out
