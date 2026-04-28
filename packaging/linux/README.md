# Linux Packaging Notes

`tools/release.py` emits `dist/latexmk-linux-<arch>.tar.gz` on Linux hosts.

This archive is relocatable and intended as packaging input for distro tooling.
At minimum, package builders should:

1. Extract the archive.
2. Install `latexmk` into a `bin` path on `PATH`.
3. Verify `latexmk --version` during package test/install steps.
