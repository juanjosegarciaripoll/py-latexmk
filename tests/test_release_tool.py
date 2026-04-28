"""Tests for release artifact generation tooling."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from types import ModuleType

    import pytest


class ReleaseArtifactsLike(Protocol):
    binary: Path
    release_binary: Path
    relocatable_archive: Path
    checksums_file: Path
    winget_manifest_files: tuple[Path, ...]


class ReleaseModule(Protocol):
    sys: ModuleType
    platform: ModuleType

    def build_release_artifacts(self, dist_dir: Path) -> ReleaseArtifactsLike: ...


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _load_release_module() -> ReleaseModule:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "release.py"
    spec = importlib.util.spec_from_file_location("release_tool_under_test", module_path)
    if spec is None or spec.loader is None:
        msg = f"Could not load module spec from {module_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("ReleaseModule", module)


def _build_artifacts(release: ReleaseModule, dist_dir: Path) -> ReleaseArtifactsLike:
    return release.build_release_artifacts(dist_dir)


def test_build_release_artifacts_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "win32")
    monkeypatch.setattr(release.platform, "machine", lambda: "AMD64")

    monkeypatch.setenv("WINGET_INSTALLER_URL", "https://example.com/latexmk-windows-x86_64.exe")
    dist_dir = tmp_path / "dist"
    binary = dist_dir / "latexmk.exe"
    _write_file(binary, b"windows-binary")

    artifacts = _build_artifacts(release, dist_dir)

    assert artifacts.binary == binary
    assert artifacts.release_binary.name == "latexmk.exe"
    assert artifacts.relocatable_archive.name == "latexmk-windows-x86_64.zip"
    assert artifacts.checksums_file.name == "SHA256SUMS.txt"

    with zipfile.ZipFile(artifacts.relocatable_archive) as archive:
        assert artifacts.release_binary.name in archive.namelist()


def test_build_release_artifacts_linux(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "linux")
    monkeypatch.setattr(release.platform, "machine", lambda: "aarch64")

    dist_dir = tmp_path / "dist"
    binary = dist_dir / "latexmk"
    _write_file(binary, b"linux-binary")

    artifacts = _build_artifacts(release, dist_dir)

    assert artifacts.release_binary.name == "latexmk"
    assert artifacts.relocatable_archive.name == "latexmk-linux-arm64.tar.gz"

    with tarfile.open(artifacts.relocatable_archive, mode="r:gz") as archive:
        names = archive.getnames()
    assert artifacts.release_binary.name in names


def test_checksums_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "linux")
    monkeypatch.setattr(release.platform, "machine", lambda: "x86_64")

    dist_dir = tmp_path / "dist"
    _write_file(dist_dir / "latexmk", b"abc123")
    artifacts = _build_artifacts(release, dist_dir)

    lines = artifacts.checksums_file.read_text(encoding="utf-8").strip().splitlines()
    checksum_map = {line.split("  ")[1]: line.split("  ")[0] for line in lines}

    renamed_digest = hashlib.sha256(artifacts.release_binary.read_bytes()).hexdigest()
    archive_digest = hashlib.sha256(artifacts.relocatable_archive.read_bytes()).hexdigest()
    assert checksum_map[artifacts.release_binary.name] == renamed_digest
    assert checksum_map[artifacts.relocatable_archive.name] == archive_digest


def test_winget_manifests_are_generated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    release = _load_release_module()
    monkeypatch.setattr(release.sys, "platform", "win32")
    monkeypatch.setattr(release.platform, "machine", lambda: "AMD64")

    templates_dir = tmp_path / "packaging" / "winget"
    templates_dir.mkdir(parents=True)
    (templates_dir / "latexmk.version.yaml.in").write_text(
        "PackageIdentifier: __IDENTIFIER__\nPackageVersion: __VERSION__\n",
        encoding="utf-8",
    )
    (templates_dir / "latexmk.installer.yaml.in").write_text(
        "InstallerUrl: __URL__\nInstallerSha256: __SHA256__\nArchitecture: __ARCH__\n",
        encoding="utf-8",
    )
    (templates_dir / "latexmk.locale.en-US.yaml.in").write_text(
        "PackageName: latexmk\n",
        encoding="utf-8",
    )

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "latexmk"\nversion = "1.2.3"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WINGET_INSTALLER_URL", "https://example.com/latexmk.exe")

    dist_dir = tmp_path / "dist"
    _write_file(dist_dir / "latexmk.exe", b"windows-binary")
    artifacts = release.build_release_artifacts(dist_dir)
    assert artifacts.winget_manifest_files
    installer_manifest = (dist_dir / "latexmk.installer.yaml").read_text(
        encoding="utf-8",
    )
    assert "https://example.com/latexmk.exe" in installer_manifest
    assert "Architecture: x64" in installer_manifest
    assert "__SHA256__" not in installer_manifest
