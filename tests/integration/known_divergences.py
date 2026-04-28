"""Known intentional divergences from Perl latexmk.

Each tuple entry is: (description, reason).
"""

from __future__ import annotations

DIVERGENCES: list[tuple[str, str]] = [
    (
        "No programmable .latexmkrc",
        "Security risk; replaced by declarative TOML config.",
    ),
    (
        "No -e CODE / Perl-eval -r FILE behavior",
        "Code execution features are intentionally removed.",
    ),
    (
        "No PostScript banner overlay flags (-bm/-bi/-bs/-d)",
        "Obsolete feature; external tooling should be used instead.",
    ),
]
