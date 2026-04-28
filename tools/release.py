"""Build release artifacts from a PyInstaller binary output."""

from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import sys
import tarfile
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
    renamed_binary: Path
    relocatable_archive: Path
    checksums_file: Path


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

    archive_path = output_dir / f"{artifact_stem}.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        archive.add(binary, arcname=binary.name)
    return archive_path


def write_checksums(paths: list[Path], output_path: Path) -> None:
    """Write a sha256sum-style manifest for provided artifact paths."""
    lines = [f"{sha256_hex(path)}  {path.name}" for path in paths]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_release_artifacts(dist_dir: Path) -> ReleaseArtifacts:
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
    suffix = ".exe" if sys.platform == "win32" else ""
    artifact_stem = f"latexmk-{os_label}-{arch}"

    renamed_binary = dist_dir / f"{artifact_stem}{suffix}"
    shutil.copy2(source_binary, renamed_binary)

    archive = create_relocatable_archive(renamed_binary, dist_dir, artifact_stem)

    checksums_file = dist_dir / "SHA256SUMS.txt"
    write_checksums([renamed_binary, archive], checksums_file)

    return ReleaseArtifacts(
        binary=source_binary,
        renamed_binary=renamed_binary,
        relocatable_archive=archive,
        checksums_file=checksums_file,
    )


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
    artifacts = build_release_artifacts(args.dist_dir)
    print(f"Binary: {artifacts.binary}")
    print(f"Artifact: {artifacts.renamed_binary}")
    print(f"Relocatable: {artifacts.relocatable_archive}")
    print(f"Checksums: {artifacts.checksums_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
