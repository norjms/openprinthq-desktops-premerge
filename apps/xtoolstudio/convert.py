#!/usr/bin/env python3
"""Restyle the xTool Studio desktop for OpenPrintHQ.

    python3 apps/xtoolstudio/convert.py [root]

Run in the Dockerfile's last stage, after Wine and Firefox ESR are installed on linuxserver.io's Selkies base.
Only the shared restyle (common/restyle.py). xTool Studio is xTool's Windows software, which the image does not
contain: common/wine/ahi-wine-app installs it from xTool on the desktop's first start and runs it under Wine.
It draws its own windows, so the OpenPrintHQ look covers the desktop, the window frames and the browser around it.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "common"))
import restyle as r  # noqa: E402

TITLE = "xTool Studio"
EDITED: tuple[str, ...] = ()
WINE = "opt/wine-stable/bin/wine"
LAUNCHER = "usr/local/bin/ahi-wine-app"
# For the tests' extraction only (from the Dockerfile's "prepared" stage); the build finds them itself.
FILE_PANEL = "lsiopy/lib/python3.13/site-packages/selkies/stream_server.py"
UPSTREAM_FILES = (*r.EDITED, FILE_PANEL, "usr/lib/firefox-esr/application.ini", WINE, LAUNCHER)
UPSTREAM_FOLDERS = r.FOLDERS


def main(argv: list[str]) -> None:
    root = Path(argv[1] if len(argv) > 1 else "/").resolve()
    for rel in (WINE, LAUNCHER):
        if not (root / rel).exists():
            raise r.ConvertError(f"convert: {rel}: missing; are Wine and the launcher installed?")
    r.apply(root, TITLE, (HERE / "app.env").read_text(encoding="utf-8"))
    print("convert: done")


if __name__ == "__main__":
    main(sys.argv)
