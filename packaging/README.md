# Packaging Artifacts

Release artifacts produced by `tools/release.py` are intended to be consumed by
package managers.

## Windows (winget local manifest)

1. Build artifacts for Windows:
   - `uv run pyinstaller latexmk.spec`
   - `python tools/release.py`
2. Copy templates from `packaging/winget/`.
3. Replace placeholders:
   - `__IDENTIFIER__` (for example `Latexmk.Latexmk`)
   - `__VERSION__`
   - `__URL__` (artifact URL or file path)
   - `__SHA256__` (from `dist/SHA256SUMS.txt`)
4. Install locally:
   - `winget install --manifest .\packaging\winget\`

## macOS (Homebrew)

1. Build artifacts on macOS host.
2. Use `packaging/homebrew/latexmk.rb.in` as formula template.
3. Fill `__VERSION__`, `__URL__`, and `__SHA256__`.

## Linux

1. Build artifacts on Linux host.
2. Use `dist/latexmk-linux-<arch>.tar.gz` as relocatable payload.
3. Consume directly or as input to distro-specific packaging scripts.
