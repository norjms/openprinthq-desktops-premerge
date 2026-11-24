#!/usr/bin/env python3
"""Restyle the PrusaSlicer desktop for OpenPrintHQ.

    python3 apps/prusaslicer/convert.py [root]

Run in the Dockerfile's last stage, after Debian's PrusaSlicer and Firefox ESR are installed on linuxserver.io's
Selkies base. Only the shared restyle (common/restyle.py): PrusaSlicer draws itself with GTK, so the desktop's
OpenPrintHQ GTK theme and Manrope are its look, and it has no web pages of its own to change. PrusaSlicer itself is
not changed or rebuilt.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "common"))
import restyle as r  # noqa: E402

TITLE = "PrusaSlicer"
EDITED: tuple[str, ...] = ()
APP = "usr/bin/prusa-slicer"
# For the tests' extraction only (from the Dockerfile's "prepared" stage); the build finds them itself.
FILE_PANEL = "lsiopy/lib/python3.13/site-packages/selkies/stream_server.py"
UPSTREAM_FILES = (*r.EDITED, FILE_PANEL, "usr/lib/firefox-esr/application.ini", APP)
UPSTREAM_FOLDERS = r.FOLDERS


def main(argv: list[str]) -> None:
    root = Path(argv[1] if len(argv) > 1 else "/").resolve()
    if not (root / APP).exists():
        raise r.ConvertError(f"convert: {APP}: missing; is prusa-slicer installed?")
    r.apply(root, TITLE, (HERE / "app.env").read_text(encoding="utf-8"))
    print("convert: done")


if __name__ == "__main__":
    main(sys.argv)
