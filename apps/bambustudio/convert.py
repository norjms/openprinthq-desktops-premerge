#!/usr/bin/env python3
"""Restyle linuxserver.io's Bambu Studio image for OpenPrintHQ.

    python3 apps/bambustudio/convert.py [root]

The shared restyle (common/restyle.py) first, then Bambu Studio's own pages: the backgrounds, lines and text
of the dark sheets of its setup wizard and home page mapped to the openprinthq-ui colours, and Manrope as their
font. Bambu green stays Bambu Studio's action colour: it is in some twenty of its stylesheets and drawn by its
own (compiled) buttons, so changing it in a few pages would leave the app in two colours. Bambu Studio's dark mode is turned on for a new /config by init-ahi-app (app.env), as are
"single instance" (so files the farm sends open in the running window) and the Files defaults. Bambu Studio
itself is not changed or rebuilt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "common"))
import restyle as r  # noqa: E402

WEB = "opt/bambustudio/resources/web"
GUIDE_DARK = f"{WEB}/guide/css/dark.css"
HOME_DARK = f"{WEB}/homepage3/css/dark.css"
FONT_FILES = (f"{WEB}/guide/css/common.css", f"{WEB}/homepage3/css/common.css", f"{WEB}/homepage3/css/left.css")
EDITED = (GUIDE_DARK, HOME_DARK, *FONT_FILES)
TITLE = "Bambu Studio"
# For the tests' extraction only; the build finds it with restyle.file_panel_path().
FILE_PANEL = "lsiopy/lib/python3.14/site-packages/selkies/stream_server.py"
UPSTREAM_FILES = (*r.EDITED, FILE_PANEL, "usr/lib/firefox/application.ini", *EDITED)
UPSTREAM_FOLDERS = r.FOLDERS

# The setup wizard's dark sheet: each Bambu Studio colour, and its OpenPrintHQ colour. Every one must be there.
GUIDE_COLOURS = {
    "#efeff0": r.TEXT, "#B9B9BC": r.FIELD_LINE, "#3E3E45": r.PAGE_MID, "#939594": r.MUTED, "#161817": r.PAGE,
    "#4A4A51": r.FIELD, "#BEBEC0": r.TEXT_2, "#4C4C55": r.HOVER, "#535353": r.HOVER,
}
# The home page's dark sheet.
HOME_COLOURS = {
    "#efeff0": r.TEXT, "#242428": r.PAGE, "#3E3E45": r.PAGE_MID, "#333337": r.SOLID_PANEL, "#343436": r.SOLID_PANEL,
    "rgba(48, 48, 51, 1)": r.SOLID_PANEL, "#818183": r.MUTED,
    "#939594": r.MUTED, "#B3B3B5": r.TEXT_2, "#4C4C55": r.HOVER, "#575757": r.ROW_LINE, "#161817": r.PAGE,
}
FONT_OLD = 'font-family: "system-ui",'
FONT_NEW = 'font-family: Manrope, "system-ui",'


def recolour(root: Path, rel: str, colours: dict[str, str]) -> None:
    body = r.text(root, rel)
    for old, new in colours.items():
        body, n = re.subn(re.escape(old) + r"(?![0-9A-Fa-f])", new, body, flags=re.I)
        if n == 0:
            raise r.ConvertError(f"convert: {rel}: expected {old}, found none")
    (root / rel).write_text(body, encoding="utf-8")


def bambu_web(root: Path) -> None:
    recolour(root, GUIDE_DARK, GUIDE_COLOURS)
    recolour(root, HOME_DARK, HOME_COLOURS)
    for rel in FONT_FILES:
        r.edit(root, rel, FONT_OLD, FONT_NEW)


def main(argv: list[str]) -> None:
    root = Path(argv[1] if len(argv) > 1 else "/").resolve()
    for rel in EDITED:
        r.text(root, rel)
    r.apply(root, TITLE, (HERE / "app.env").read_text(encoding="utf-8"))
    bambu_web(root)
    print("convert: done")


if __name__ == "__main__":
    main(sys.argv)
