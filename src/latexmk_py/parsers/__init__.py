"""File parsers for latexmk_py: fls, log, aux, bcf.

Each parser is a pure function returning a frozen dataclass.
"""

from __future__ import annotations

from latexmk_py.parsers.bcf import BcfResult, parse_bcf
from latexmk_py.parsers.dotaux import AuxResult, parse_aux
from latexmk_py.parsers.fls import FlsResult, parse_fls
from latexmk_py.parsers.log import LogResult, parse_log

__all__ = [
    "AuxResult",
    "BcfResult",
    "FlsResult",
    "LogResult",
    "parse_aux",
    "parse_bcf",
    "parse_fls",
    "parse_log",
]
