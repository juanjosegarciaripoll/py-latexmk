"""Platform detection and OS-specific path helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    """Return True when running on Windows."""
    return sys.platform == "win32"


def is_macos() -> bool:
    """Return True when running on macOS."""
    return sys.platform == "darwin"


def default_viewer(fmt: str) -> str:
    r"""Return a viewer command template for *fmt* (e.g. ``'pdf'``).

    The token ``%S`` is the source file placeholder used by runner.py.
    Returns ``'open %S'`` on macOS, ``'start "" %S'`` on Windows,
    ``'xdg-open %S'`` elsewhere.
    """
    _ = fmt  # viewer selection by format is deferred to config; platform only picks the opener
    if is_macos():
        return "open %S"
    if is_windows():
        return 'start "" %S'
    return "xdg-open %S"


def user_config_dir() -> Path:
    r"""Return the user-level latexmk config directory.

    ``%APPDATA%\latexmk`` on Windows; ``$XDG_CONFIG_HOME/latexmk`` elsewhere.
    """
    if is_windows():
        appdata = os.environ.get("APPDATA", "")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "latexmk"
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "latexmk"


def system_config_dir() -> Path:
    r"""Return the system-level latexmk config directory.

    ``%ProgramData%\latexmk`` on Windows; ``/etc/latexmk`` elsewhere.
    """
    if is_windows():
        programdata = os.environ.get("PROGRAMDATA", "")
        systemdrive = os.environ.get("SYSTEMDRIVE", "C:")
        base = Path(programdata) if programdata else Path(systemdrive) / "ProgramData"
        return base / "latexmk"
    return Path("/etc/latexmk")
