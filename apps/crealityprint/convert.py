#!/usr/bin/env python3
"""Restyle the Creality Print desktop for OpenPrintHQ.

    python3 apps/crealityprint/convert.py [root]

Run in the Dockerfile's last stage, after Creality Print's own Linux build is in /opt/crealityprint on
linuxserver.io's Selkies base. The shared restyle (common/restyle.py); Creality Print's own pages are left as its
makers drew them. Creality Print itself is not changed or rebuilt.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "common"))
import restyle as r  # noqa: E402

TITLE = "Creality Print"
EDITED: tuple[str, ...] = ()
APP = "opt/crealityprint/AppRun"
# For the tests' extraction only (from the Dockerfile's "prepared" stage); the build finds them itself.
FILE_PANEL = "lsiopy/lib/python3.14/site-packages/selkies/stream_server.py"
UPSTREAM_FILES = (*r.EDITED, FILE_PANEL, "usr/lib/firefox/application.ini", APP)
UPSTREAM_FOLDERS = r.FOLDERS


def main(argv: list[str]) -> None:
    root = Path(argv[1] if len(argv) > 1 else "/").resolve()
    if not (root / APP).exists():
        raise r.ConvertError(f"convert: {APP}: missing; is Creality Print in /opt/crealityprint?")
    r.apply(root, TITLE, (HERE / "app.env").read_text(encoding="utf-8"))
    print("convert: done")


if __name__ == "__main__":
    main(sys.argv)
