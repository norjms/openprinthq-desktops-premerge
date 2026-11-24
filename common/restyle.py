"""The OpenPrintHQ restyle shared by every desktop app (docs in README.md), used by each app's convert.py.

Runs inside an image build (root "/"), or on a copy of an image's files for the tests. Only colours, fonts and
the desktop around the app change, and only where they are read from files at run time:

1. The web desktop's page: Selkies' dashboard copied to "artisanhub-dashboard" (selected with DASHBOARD) with
   ahi-dashboard.css after Selkies' own stylesheet, and the page's install colours.
2. The window manager: labwc's theme "ArtisanHub", title in Manrope.
3. GTK 3: the theme "ArtisanHub" (Adwaita dark under the openprinthq-ui colours), Manrope as the font.
4. The file panel page: the openprinthq-ui colours, dark only.
5. The browser: web addresses the app opens go to the desktop's Firefox, through ahi-open-url.
6. The start-up steps every app shares (common/files/s6): the app's own settings (init-ahi-app, from
   /etc/ahi/app.env), Files, the browser, the session bus and the farm's inbox.

Every edit names text that must be found a set number of times. When an upstream release changes it, or a file
is missing, the build stops and says which, rather than guessing.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

COMMON = Path(__file__).resolve().parent
FILES = COMMON / "files"

DASHBOARD_SRC = "usr/share/selkies/selkies-dashboard"
DASHBOARD = "usr/share/selkies/artisanhub-dashboard"
LABWC_RC = "defaults/labwc.xml"
INIT_NGINX = "etc/s6-overlay/s6-rc.d/init-nginx/run"
GTK_SETTINGS = "etc/gtk-3.0/settings.ini"
S6 = "etc/s6-overlay/s6-rc.d"
# Firefox as the base image has it: Mozilla's build (Ubuntu bases) or Debian's ESR.
FIREFOX_DIRS = ("usr/lib/firefox", "usr/lib/firefox-esr")
OPENER = "usr/local/bin/ahi-open-url"
XDG_OPEN = "usr/local/bin/xdg-open"
# Firefox with the web sign-ins every desktop shares (OPHQ-163), and the script that merges them.
FIREFOX = "usr/local/bin/ahi-firefox"
SIGNINS = "usr/local/lib/ahi/ahi_signins.py"
# The desktop's own menus, whose Firefox item becomes ahi-firefox when they have one.
MENUS = ("defaults/menu.xml", "defaults/menu_wayland.xml")
BROWSER_DESKTOP = "usr/share/applications/ahi-browser.desktop"
MIMEAPPS = "etc/xdg/mimeapps.list"
APP_ENV = "etc/ahi/app.env"

# Every upstream file the shared restyle reads or edits, and the folders it adds to. The file panel's path
# depends on the base image's Python; file_panel_path() finds it.
EDITED = (f"{DASHBOARD_SRC}/index.html", LABWC_RC, INIT_NGINX)
FOLDERS = (DASHBOARD_SRC, f"{DASHBOARD_SRC}/assets", "etc/gtk-3.0", "usr/share/themes", f"{S6}/init-config",
           f"{S6}/init-config-end/dependencies.d", f"{S6}/user/contents.d", f"{S6}/svc-de/dependencies.d",
           f"{S6}/init-selkies-config", "usr/share/applications", "etc/xdg")
ONESHOTS = ("init-ahi-app", "init-ahi-files", "init-ahi-browser")
LONGRUNS = ("svc-ahi-bus", "svc-ahi-inbox")

# openprinthq-ui v0.1.0 values (dist/theme.css), and the solid colours they make over the page where a
# native toolkit cannot blend (GTK and labwc paint opaque colours).
PAGE = "#172028"         # --ah-page
PAGE_MID = "#273642"     # --ah-page-mid: window and panel background, per the canvas's colour map
SOLID_PANEL = "#26343f"  # --ah-solid-panel
TEXT = "#f1f6fa"         # --ah-text
ACCENT = "#8fd3ff"       # --ah-accent
ON_ACCENT = "#1d2a34"    # --ah-on-accent
LINK = "#bfe6ff"         # --ah-link
ATTENTION = "#ffb38a"    # --ah-attention
FAILURE = "#e66767"      # --ah-failure
SIDEBAR = "#2a3239"      # --ah-glass (white 0.08) over the page: sidebar and tab bar
FIELD = "#1e2a34"        # --ah-field (rgba(20,30,38,0.5)) over the panel background
FIELD_LINE = "#525e68"   # --ah-field-line (white 0.2) over the panel background
ROW_LINE = "#384651"     # --ah-row-line (white 0.08) over the panel background
HOVER = "#3d4a55"        # --ah-track (white 0.1) over the panel background, a step up from the panel
MUTED = "#bbc4cb"        # --ah-text-3-large (0.75) over the panel background
TEXT_2 = "#cfd7dd"       # --ah-text-2 (0.85) over the panel background
DISABLED = "#7d8890"     # white 0.4 over the panel background, for disabled text only


class ConvertError(SystemExit):
    pass


def text(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise ConvertError(f"convert: {rel}: missing from the upstream image")
    return path.read_text(encoding="utf-8")


def edit(root: Path, rel: str, old: str, new: str, count: int = 1) -> None:
    body = text(root, rel)
    found = body.count(old)
    if found != count:
        raise ConvertError(f"convert: {rel}: expected {count} of {old[:80]!r}, found {found}")
    (root / rel).write_text(body.replace(old, new), encoding="utf-8")


def need(root: Path, rel: str, anchor: str, at_least: int = 1) -> None:
    found = text(root, rel).count(anchor)
    if found < at_least:
        raise ConvertError(f"convert: {rel}: expected {anchor[:80]!r}, found {found}")


def copy_tree(src: Path, dst: Path) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_file():
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def file_panel_path(root: Path) -> str:
    found = sorted(root.glob("lsiopy/lib/python3.*/site-packages/selkies/stream_server.py"))
    if len(found) != 1:
        raise ConvertError(f"convert: expected one Selkies stream_server.py, found {len(found)}")
    return str(found[0].relative_to(root))


def firefox_dir(root: Path) -> str:
    found = [d for d in FIREFOX_DIRS if (root / d / "application.ini").is_file()]
    if len(found) != 1:
        raise ConvertError(f"convert: expected one Firefox in {', '.join(FIREFOX_DIRS)}, found {len(found)}")
    return found[0]


def check(root: Path) -> None:
    for rel in EDITED:
        text(root, rel)
    file_panel_path(root)
    firefox_dir(root)
    for rel in FOLDERS:
        if not (root / rel).is_dir():
            raise ConvertError(f"convert: {rel}/: missing from the upstream image")


def dashboard(root: Path, title: str) -> None:
    src, dst = root / DASHBOARD_SRC, root / DASHBOARD
    text(root, f"{DASHBOARD_SRC}/index.html")
    sheets = sorted((src / "assets").glob("index-*.css"))
    if len(sheets) != 1:
        raise ConvertError(f"convert: {DASHBOARD_SRC}/assets: expected one index-*.css, found {len(sheets)}")
    sheet = str(sheets[0].relative_to(root))
    need(root, sheet, ".sidebar,.stream-strip,.sidebar-skin,:root[data-layout=default] [data-slot=dialog-content]{--sk-accent:")
    need(root, sheet, ":root:not(.dark) .sidebar,:root:not(.dark) .sidebar-skin,")
    for anchor in (".sidebar h2{", ".theme-pill", ".toggle-indicator{background-color:var(--sk-accent",
                   ".sidebar-section-header h3{", ".action-button", "--sk-wordmark-from", "--sk-surface-inset"):
        need(root, sheet, anchor)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
    rel = f"{DASHBOARD}/index.html"
    edit(root, rel, "<title>Selkies</title>", f"<title>{title}</title>")
    edit(root, rel, "</head>", '<link rel="stylesheet" href="./ahi/ahi-dashboard.css"></head>')
    copy_tree(FILES / "dashboard", dst / "ahi")
    css = (dst / "ahi" / "ahi-dashboard.css").read_text(encoding="utf-8")
    if os.environ.get("AHI_SKIP_FONTS") != "1":
        for font in re.findall(r"url\(\./fonts/([^)]+)\)", css):
            if not (dst / "ahi" / "fonts" / font).is_file():
                raise ConvertError(f"convert: font {font} is missing (the Dockerfile's fonts stage puts it there)")


def manifest(root: Path) -> None:
    edit(root, INIT_NGINX, '\\"background_color\\": \\"#000000\\",', f'\\"background_color\\": \\"{PAGE}\\",')
    edit(root, INIT_NGINX, '\\"theme_color\\": \\"#000000\\",', f'\\"theme_color\\": \\"{PAGE}\\",')


def window_manager(root: Path) -> None:
    edit(root, LABWC_RC, "<name>Clearlooks</name>", "<name>ArtisanHub</name>")
    edit(root, LABWC_RC, "    <cornerRadius>8</cornerRadius>\n  </theme>",
         "    <cornerRadius>10</cornerRadius>\n"
         '    <font place="ActiveWindow"><name>Manrope</name><size>10</size><weight>bold</weight></font>\n'
         '    <font place="InactiveWindow"><name>Manrope</name><size>10</size><weight>bold</weight></font>\n'
         '    <font place="MenuItem"><name>Manrope</name><size>10</size></font>\n'
         '    <font place="OnScreenDisplay"><name>Manrope</name><size>10</size></font>\n'
         "  </theme>")
    copy_tree(FILES / "themes", root / "usr/share/themes")


GTK_OURS = {"gtk-theme-name": "ArtisanHub", "gtk-application-prefer-dark-theme": "1",
            "gtk-font-name": "Manrope 10", "gtk-icon-theme-name": "Adwaita"}


def gtk(root: Path) -> None:
    """Our theme, font and icons in /etc/gtk-3.0/settings.ini: the file is ours where upstream has none, and
    upstream's (Ubuntu's Yaru, on some bases) has our four keys set where it has one; its other keys stay."""
    path = root / GTK_SETTINGS
    if not path.exists():
        shutil.copy2(FILES / "gtk-settings.ini", path)
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "[Settings]":
        raise ConvertError(f"convert: {GTK_SETTINGS}: expected a [Settings] section first")
    kept = [line for line in lines[1:] if line.split("=", 1)[0].strip() not in GTK_OURS]
    ours = [f"{k}={v}" for k, v in GTK_OURS.items()]
    path.write_text("\n".join(["[Settings]", *ours, *kept]) + "\n", encoding="utf-8")


# The file panel's page has its own copy of Selkies' palette. The OpenPrintHQ values go after it, for every
# theme a browser may have stored (the page is dark only here, like the dashboard).
FILE_PANEL_ANCHOR = (
    "            --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35);\n        }\n        * {\n"
)
FILE_PANEL_EXTRA = f"""            --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35);
        }}
        /* OpenPrintHQ: openprinthq-ui's glass-dark values, whatever theme is stored. */
        :root, :root[data-theme], :root:not([data-theme="light"]) {{
            --accent: {ACCENT};
            --accent-text: {ACCENT};
            --accent-soft: rgba(143, 211, 255, 0.14);
            --bg: {PAGE};
            --surface: {PAGE_MID};
            --surface-alt: {SOLID_PANEL};
            --border-soft: rgba(255, 255, 255, 0.16);
            --text: {TEXT};
            --text-muted: rgba(236, 243, 248, 0.85);
            --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35);
            --font-family: "Manrope", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
            --border-radius: 22px;
            color-scheme: dark;
        }}
        body {{
            background: radial-gradient(80% 75% at 55% 35%, #3f566a, {PAGE_MID} 50%, {PAGE}) fixed;
        }}
        * {{
"""


def file_panel(root: Path) -> None:
    edit(root, file_panel_path(root), FILE_PANEL_ANCHOR, FILE_PANEL_EXTRA)


def startup(root: Path, app_env: str) -> None:
    """The start-up steps every app shares, and the app's own settings for them (/etc/ahi/app.env)."""
    s6 = root / S6
    copy_tree(FILES / "s6", s6)
    for name in ONESHOTS:
        (s6 / f"init-config-end/dependencies.d/{name}").touch()
        (s6 / f"user/contents.d/{name}").touch()
        os.chmod(s6 / f"{name}/run", 0o755)
    for name in LONGRUNS:
        (s6 / f"user/contents.d/{name}").touch()
        os.chmod(s6 / f"{name}/run", 0o755)
    (s6 / "svc-de/dependencies.d/svc-ahi-bus").touch()
    target = root / APP_ENV
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(app_env, encoding="utf-8")


def browser(root: Path) -> None:
    """Web addresses the app opens go to the desktop's Firefox. The hardened desktop has no xdg-open;
    ahi-open-url (http and https only) stands in for it, and Firefox runs with policies that keep it a browser
    for the web alone."""
    firefox = firefox_dir(root)
    if "Name=Firefox" not in text(root, f"{firefox}/application.ini"):
        raise ConvertError(f"convert: {firefox}/application.ini: not Firefox")
    src = FILES / "browser"
    for name, rel, mode in (("ahi-open-url", OPENER, 0o755), ("ahi-open-url", XDG_OPEN, 0o755),
                            ("ahi-firefox", FIREFOX, 0o755), ("ahi_signins.py", SIGNINS, 0o755),
                            ("ahi-browser.desktop", BROWSER_DESKTOP, 0o644), ("mimeapps.list", MIMEAPPS, 0o644),
                            ("policies.json", f"{firefox}/distribution/policies.json", 0o644)):
        target = root / rel
        if target.exists():
            raise ConvertError(f"convert: {rel}: already in the upstream image")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / name, target)
        os.chmod(target, mode)
    for rel in MENUS:
        menu = root / rel
        if menu.is_file():
            body = menu.read_text(encoding="utf-8")
            menu.write_text(body.replace("<command>/usr/bin/firefox</command>", f"<command>/{FIREFOX}</command>"),
                            encoding="utf-8")


def apply(root: Path, title: str, app_env: str) -> None:
    """Everything shared, in order. Each app's convert.py calls this, then makes its own changes."""
    check(root)
    dashboard(root, title)
    manifest(root)
    window_manager(root)
    gtk(root)
    file_panel(root)
    startup(root, app_env)
    browser(root)
