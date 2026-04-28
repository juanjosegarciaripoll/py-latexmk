"""Tests for release artifact generation tooling."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _load_release_module():
    module_path = Path(__file__).resolve().parents[1] / "tools" / "release.py"
    spec = importlib.util.spec_from_file_location("release_tool_under_test", module_path)
    if spec is None or spec.loader is None:
        msg = f"Could not load module spec from {module_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_release_artifacts_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "win32")
    monkeypatch.setattr(release.platform, "machine", lambda: "AMD64")

    dist_dir = tmp_path / "dist"
    binary = dist_dir / "latexmk.exe"
    _write_file(binary, b"windows-binary")

    artifacts = release.build_release_artifacts(dist_dir)

    assert artifacts.binary == binary
    assert artifacts.renamed_binary.name == "latexmk-windows-x86_64.exe"
    assert artifacts.relocatable_archive.name == "latexmk-windows-x86_64.zip"
    assert artifacts.checksums_file.name == "SHA256SUMS.txt"

    with zipfile.ZipFile(artifacts.relocatable_archive) as archive:
        assert artifacts.renamed_binary.name in archive.namelist()


def test_build_release_artifacts_linux(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "linux")
    monkeypatch.setattr(release.platform, "machine", lambda: "aarch64")

    dist_dir = tmp_path / "dist"
    binary = dist_dir / "latexmk"
    _write_file(binary, b"linux-binary")

    artifacts = release.build_release_artifacts(dist_dir)

    assert artifacts.renamed_binary.name == "latexmk-linux-arm64"
    assert artifacts.relocatable_archive.name == "latexmk-linux-arm64.tar.gz"

    with tarfile.open(artifacts.relocatable_archive, mode="r:gz") as archive:
        names = archive.getnames()
    assert artifacts.renamed_binary.name in names


def test_checksums_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "linux")
    monkeypatch.setattr(release.platform, "machine", lambda: "x86_64")

    dist_dir = tmp_path / "dist"
    _write_file(dist_dir / "latexmk", b"abc123")
    artifacts = release.build_release_artifacts(dist_dir)

    lines = artifacts.checksums_file.read_text(encoding="utf-8").strip().splitlines()
    checksum_map = {line.split("  ")[1]: line.split("  ")[0] for line in lines}

    renamed_digest = hashlib.sha256(artifacts.renamed_binary.read_bytes()).hexdigest()
    archive_digest = hashlib.sha256(artifacts.relocatable_archive.read_bytes()).hexdigest()
    assert checksum_map[artifacts.renamed_binary.name] == renamed_digest
    assert checksum_map[artifacts.relocatable_archive.name] == archive_digest
