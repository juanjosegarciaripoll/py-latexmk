"""Parser for Biber .bcf control files.

Mirrors ``parse_bcf`` in ``latexmk.pl`` (lines 7729-7810).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_BCF_NS = "http://biblatex-biber.sourceforge.net/biblatexml"
_DATASOURCE_TAG = f"{{{_BCF_NS}}}datasource"
_REMOTE_PREFIXES = ("http:", "https:", "ftp:", "ftps:")


@dataclass(slots=True, frozen=True)
class BcfResult:
    """Parsed data sources from a Biber .bcf control file."""

    data_sources: frozenset[str]  # .bib file paths from <bcf:datasource>


def parse_bcf(path: Path) -> BcfResult:
    """Parse a Biber .bcf control file for data sources.

    Mirrors ``parse_bcf`` in ``latexmk.pl`` (lines 7729-7810).

    Returns an empty ``BcfResult`` when *path* does not exist or is malformed.
    """
    if not path.exists():
        return BcfResult(data_sources=frozenset())

    try:
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError:
        return BcfResult(data_sources=frozenset())

    root = tree.getroot()
    sources: set[str] = set()

    for elem in root.iter(_DATASOURCE_TAG):
        if elem.get("type") != "file" or elem.get("datatype") != "bibtex":
            continue
        text = (elem.text or "").strip()
        if not text:
            continue
        # Skip remote URLs (mirrors latexmk.pl lines 7784-7785).
        if any(text.startswith(p) for p in _REMOTE_PREFIXES):
            continue
        sources.add(text)

    return BcfResult(data_sources=frozenset(sources))
