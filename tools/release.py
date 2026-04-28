"""Build release artifacts from a PyInstaller binary output."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SYSTEM_LABELS: Final[dict[str, str]] = {
    "win32": "windows",
    "darwin": "macos",
    "linux": "linux",
}

ARCH_LABELS: Final[dict[str, str]] = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "arm64": "arm64",
    "aarch64": "arm64",
}


@dataclass(slots=True, frozen=True)
class ReleaseArtifacts:
    """Paths for generated release artifacts."""

    binary: Path
    release_binary: Path
    relocatable_archive: Path
    checksums_file: Path
    winget_manifest_files: tuple[Path, ...]


def normalize_arch(machine: str) -> str:
    """Normalize host architecture to release naming."""
    return ARCH_LABELS.get(machine.lower(), machine.lower())


def system_label(platform_id: str) -> str:
    """Normalize Python platform identifier to release naming."""
    return SYSTEM_LABELS.get(platform_id, platform_id)


def sha256_hex(path: Path) -> str:
    """Return SHA-256 checksum for file at path."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binary_name_for_platform(platform_id: str) -> str:
    """Return expected executable name for a platform."""
    return "latexmk.exe" if platform_id == "win32" else "latexmk"


def create_relocatable_archive(binary: Path, output_dir: Path, artifact_stem: str) -> Path:
    """Create a platform-appropriate relocatable archive containing the executable."""
    if sys.platform == "win32":
        archive_path = output_dir / f"{artifact_stem}.zip"
        with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(binary, arcname=binary.name)
        return archive_path

    archive_path = output_dir / f"{artifact_stem}.tar.gz"  # type: ignore[unreachable]
    with tarfile.open(archive_path, mode="w:gz") as archive:
        archive.add(binary, arcname=binary.name)
    return archive_path


def write_checksums(paths: list[Path], output_path: Path) -> None:
    """Write a sha256sum-style manifest for provided artifact paths."""
    lines = [f"{sha256_hex(path)}  {path.name}" for path in paths]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def winget_architecture(arch: str) -> str:
    """Map normalized architecture to winget architecture enum."""
    if arch == "x86_64":
        return "x64"
    if arch == "arm64":
        return "arm64"
    return arch


def render_winget_manifest(
    *,
    templates_dir: Path,
    output_dir: Path,
    package_identifier: str,
    package_version: str,
    installer_url: str,
    installer_sha256: str,
    architecture: str,
) -> None:
    """Render winget manifests from templates with release values."""
    replacements = {
        "__IDENTIFIER__": package_identifier,
        "__VERSION__": package_version,
        "__URL__": installer_url,
        "__SHA256__": installer_sha256,
        "__ARCH__": architecture,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for template in templates_dir.glob("*.yaml.in"):
        text = template.read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace(key, value)
        target_name = template.name.removesuffix(".in")
        (output_dir / target_name).write_text(text, encoding="utf-8")


def release_version_from_pyproject(pyproject_path: Path) -> str:
    """Read package version from pyproject.toml."""
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        msg = "Missing [project] section in pyproject.toml"
        raise TypeError(msg)
    version = project.get("version")
    if not isinstance(version, str) or not version:
        msg = "Missing or invalid project.version in pyproject.toml"
        raise ValueError(msg)
    return version


def winget_installer_url_from_env(binary_name: str, version: str) -> str:
    """Build installer URL from environment for release automation."""
    override = os.environ.get("WINGET_INSTALLER_URL")
    if override:
        return override
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        msg = (
            "Missing installer URL context. Set WINGET_INSTALLER_URL or "
            "GITHUB_REPOSITORY in the environment."
        )
        raise ValueError(msg)
    return f"https://github.com/{repo}/releases/download/v{version}/{binary_name}"


def build_release_artifacts(
    dist_dir: Path,
) -> ReleaseArtifacts:
    """Produce renamed binary, relocatable archive, and checksum manifest."""
    binary_name = binary_name_for_platform(sys.platform)
    source_binary = dist_dir / binary_name
    if not source_binary.is_file():
        msg = (
            f"Expected PyInstaller binary at '{source_binary}'. "
            "Run: uv run pyinstaller latexmk.spec"
        )
        raise FileNotFoundError(msg)

    arch = normalize_arch(platform.machine())
    os_label = system_label(sys.platform)
    artifact_stem = f"latexmk-{os_label}-{arch}"
    release_binary = source_binary
    archive = create_relocatable_archive(release_binary, dist_dir, artifact_stem)

    checksums_file = dist_dir / "SHA256SUMS.txt"
    write_checksums([release_binary, archive], checksums_file)

    winget_manifest_files: tuple[Path, ...] = ()
    if sys.platform == "win32":
        release_version = release_version_from_pyproject(Path("pyproject.toml"))
        installer_url = winget_installer_url_from_env(release_binary.name, release_version)
        templates_dir = Path("packaging") / "winget"
        render_winget_manifest(
            templates_dir=templates_dir,
            output_dir=dist_dir,
            package_identifier="Latexmk.PyLatexmk",
            package_version=release_version,
            installer_url=installer_url,
            installer_sha256=sha256_hex(release_binary),
            architecture=winget_architecture(arch),
        )
        winget_manifest_files = tuple(sorted(dist_dir.glob("latexmk.*.yaml")))

    return ReleaseArtifacts(
        binary=source_binary,
        release_binary=release_binary,
        relocatable_archive=archive,
        checksums_file=checksums_file,
        winget_manifest_files=winget_manifest_files,
    )


def run_pyinstaller() -> None:
    """Build standalone executable with PyInstaller."""
    command = ["pyinstaller", "latexmk.spec"]
    result = subprocess.run(command, check=False)  # noqa: S603 - fixed trusted command
    if result.returncode != 0:
        msg = f"PyInstaller failed with exit code {result.returncode}"
        raise RuntimeError(msg)


def parse_args() -> argparse.Namespace:
    """Parse CLI options."""
    parser = argparse.ArgumentParser(
        description="Generate release artifacts from PyInstaller dist output.",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
        help="Directory containing PyInstaller output (default: dist).",
    )
    return parser.parse_args()


def main() -> int:
    """Run artifact generation and print generated paths."""
    args = parse_args()
    run_pyinstaller()
    artifacts = build_release_artifacts(args.dist_dir)
    print(f"Binary: {artifacts.binary}")
    print(f"Artifact: {artifacts.release_binary}")
    print(f"Relocatable: {artifacts.relocatable_archive}")
    print(f"Checksums: {artifacts.checksums_file}")
    for path in artifacts.winget_manifest_files:
        print(f"Winget manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
