"""Tests for common/restyle.py and every app's convert.py, run on the files tests/extract-upstream.sh took out
of each app's pinned image.

    tests/run.sh            (or: APPS="bambustudio" python3 -m unittest discover -s tests)

They fail when a pinned upstream image lacks a file or folder a conversion edits, when an anchor no longer
matches, and when a conversion would carry on past a missing file instead of stopping.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "common"))
import restyle  # noqa: E402

os.environ.setdefault("AHI_SKIP_FONTS", "1")  # the fonts come from each Dockerfile's fonts stage


def app_names() -> list[str]:
    named = os.environ.get("APPS", "").split()
    if named == ["none"]:  # the shared tests alone (CI's common job)
        return []
    return named or sorted(p.parent.name for p in (REPO / "apps").glob("*/convert.py"))


def load(app: str):
    spec = importlib.util.spec_from_file_location(f"app_{app}", REPO / "apps" / app / "convert.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_file(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            out[key] = value.strip('"')
    return out


_LOCAL: dict[str, Path] = {}


def fresh_root(app: str) -> Path:
    """A from-scratch copy of an app's upstream files, on local disk (one read of tests/.upstream/<app>)."""
    upstream = HERE / ".upstream" / app
    if not upstream.is_dir():
        raise unittest.SkipTest(f"run tests/extract-upstream.sh {app} first (tests/run.sh does)")
    if app not in _LOCAL:
        _LOCAL[app] = Path(tempfile.mkdtemp(prefix=f"ahi-{app}-upstream-"))
        shutil.copytree(upstream, _LOCAL[app], dirs_exist_ok=True, symlinks=True)
    root = Path(tempfile.mkdtemp(prefix=f"ahi-{app}-"))
    shutil.copytree(_LOCAL[app], root, dirs_exist_ok=True, symlinks=True)
    return root


class EachApp(unittest.TestCase):
    """Every app folder: pinned, complete, and converting its pinned image."""

    def test_upstream_has_everything(self):
        for app in app_names():
            with self.subTest(app=app):
                mod, upstream = load(app), HERE / ".upstream" / app
                if not upstream.is_dir():
                    self.skipTest("no extracted upstream files")
                self.assertEqual([r for r in mod.UPSTREAM_FILES if not (upstream / r).is_file()], [])
                self.assertEqual([r for r in mod.UPSTREAM_FOLDERS if not (upstream / r).is_dir()], [])

    def test_dockerfile_defaults_match_upstream_env(self):
        for app in app_names():
            with self.subTest(app=app):
                env = env_file(REPO / "apps" / app / "upstream.env")
                docker = (REPO / "apps" / app / "Dockerfile").read_text()
                for key in ("UPSTREAM_IMAGE", "UPSTREAM_VERSION", "UPSTREAM_DIGEST", "FONTSOURCE_VERSION"):
                    self.assertIn(f"ARG {key}={env[key]}\n", docker, key)
                self.assertRegex(env["UPSTREAM_DIGEST"], r"^sha256:[0-9a-f]{64}$")
                self.assertNotEqual(env["UPSTREAM_VERSION"], "latest")
                for key in ("APP_PACKAGE_VERSION", "APP_VERSION", "APP_URL", "APP_SHA256"):
                    if key in env:
                        self.assertIn(f"ARG {key}={env[key]}\n", docker, key)
                platforms = env["PLATFORMS"].split(",")
                self.assertTrue(platforms and set(platforms) <= {"linux/amd64", "linux/arm64"}, platforms)

    def test_app_env_names_what_the_start_up_steps_need(self):
        for app in app_names():
            with self.subTest(app=app):
                path = REPO / "apps" / app / "app.env"
                done = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)
                env = env_file(path)
                for key in ("APP_TITLE", "APP_PROCESS"):
                    self.assertTrue(env.get(key), key)
                if env.get("APP_SINGLE_INSTANCE") or env.get("APP_FILES_DEFAULTS"):
                    self.assertTrue(env.get("APP_CONF", "").startswith("/config/"))

    def test_converts_the_pinned_image(self):
        for app in app_names():
            with self.subTest(app=app):
                mod = load(app)
                root = fresh_root(app)
                try:
                    mod.main(["convert.py", str(root)])
                    self.shared_changes(root, mod.TITLE, app)
                    getattr(self, f"changes_{app}")(root, mod)
                finally:
                    shutil.rmtree(root, ignore_errors=True)

    def shared_changes(self, root: Path, title: str, app: str) -> None:
        index = (root / restyle.DASHBOARD / "index.html").read_text()
        self.assertIn(f"<title>{title}</title>", index)
        self.assertIn("./ahi/ahi-dashboard.css", index)
        self.assertIn("<name>ArtisanHub</name>", (root / restyle.LABWC_RC).read_text())
        self.assertTrue((root / "usr/share/themes/ArtisanHub/labwc/themerc").is_file())
        gtk = (root / restyle.GTK_SETTINGS).read_text().splitlines()
        self.assertEqual(gtk[0], "[Settings]")
        for key, value in restyle.GTK_OURS.items():
            self.assertEqual([line for line in gtk if line.startswith(f"{key}=")], [f"{key}={value}"])
        self.assertIn(restyle.PAGE, (root / restyle.INIT_NGINX).read_text())
        self.assertIn("openprinthq-ui's glass-dark values", (root / restyle.file_panel_path(root)).read_text())
        s6 = root / restyle.S6
        for name in (*restyle.ONESHOTS, *restyle.LONGRUNS):
            self.assertTrue(os.access(s6 / name / "run", os.X_OK), name)
            self.assertTrue((s6 / "user/contents.d" / name).exists(), name)
        self.assertEqual((root / restyle.APP_ENV).read_text(), (REPO / "apps" / app / "app.env").read_text())
        for rel in (restyle.OPENER, restyle.XDG_OPEN):
            self.assertTrue(os.access(root / rel, os.X_OK), rel)

    def changes_bambustudio(self, root: Path, mod) -> None:
        for rel in (mod.GUIDE_DARK, mod.HOME_DARK):
            body = (root / rel).read_text()
            self.assertIn(restyle.PAGE_MID, body)
            for old in ("#3E3E45", "#efeff0", "#161817"):
                self.assertNotIn(old.lower(), body.lower(), (rel, old))
            # Bambu green stays Bambu Studio's action colour.
            self.assertNotIn(restyle.ACCENT, body)
        for rel in mod.FONT_FILES:
            self.assertIn('font-family: Manrope, "system-ui",', (root / rel).read_text())

    def changes_prusaslicer(self, root: Path, mod) -> None:
        # Its look is the desktop's GTK theme: only the shared restyle, with Debian's Firefox ESR.
        self.assertTrue((root / "usr/lib/firefox-esr/distribution/policies.json").is_file())

    def changes_crealityprint(self, root: Path, mod) -> None:
        self.assertTrue((root / "usr/lib/firefox/distribution/policies.json").is_file())

    def wine_app(self, root: Path, app: str) -> None:
        # Wine apps: the image holds Wine and the launcher only; the vendor's installer comes at first start.
        self.assertTrue((root / "usr/lib/firefox-esr/distribution/policies.json").is_file())
        env = env_file(REPO / "apps" / app / "app.env")
        self.assertEqual(env["APP_RUN"], "/usr/local/bin/ahi-wine-app")
        self.assertEqual(env["WINE_APP_ID"], app)
        self.assertTrue(env["WINE_APP_URL"].startswith("https://"), env["WINE_APP_URL"])
        self.assertIn(env["WINE_APP_INSTALL"], ("inno", "nsis"))
        if "WINE_APP_SHA256" in env:
            self.assertRegex(env["WINE_APP_SHA256"], r"^[0-9a-f]{64}$")
        for name in ("autostart", "autostart_wayland"):
            self.assertIn("\n/usr/local/bin/ahi-wine-app\n", (REPO / "apps" / app / "root/defaults" / name).read_text())

    def changes_bambusuite(self, root: Path, mod) -> None:
        self.wine_app(root, "bambusuite")

    def changes_eufymakestudio(self, root: Path, mod) -> None:
        self.wine_app(root, "eufymakestudio")

    def test_each_missing_file_stops_the_conversion(self):
        for app in app_names():
            mod = load(app)
            for rel in mod.UPSTREAM_FILES:
                with self.subTest(app=app, rel=rel):
                    root = fresh_root(app)
                    try:
                        (root / rel).unlink()
                        with self.assertRaises(restyle.ConvertError):
                            mod.main(["convert.py", str(root)])
                    finally:
                        shutil.rmtree(root, ignore_errors=True)

    def test_each_missing_folder_stops_the_conversion(self):
        for app in app_names():
            mod = load(app)
            for rel in mod.UPSTREAM_FOLDERS:
                with self.subTest(app=app, rel=rel):
                    root = fresh_root(app)
                    try:
                        shutil.rmtree(root / rel)
                        with self.assertRaises(restyle.ConvertError):
                            mod.main(["convert.py", str(root)])
                    finally:
                        shutil.rmtree(root, ignore_errors=True)

    def test_a_changed_anchor_stops_the_conversion(self):
        for app in app_names():
            with self.subTest(app=app):
                mod = load(app)
                root = fresh_root(app)
                try:
                    rc = root / restyle.LABWC_RC
                    rc.write_text(rc.read_text().replace("<name>Clearlooks</name>", "<name>Other</name>"))
                    with self.assertRaises(restyle.ConvertError) as caught:
                        mod.main(["convert.py", str(root)])
                    self.assertIn(restyle.LABWC_RC, str(caught.exception))
                finally:
                    shutil.rmtree(root, ignore_errors=True)


class GtkSettings(unittest.TestCase):
    def test_an_upstream_settings_file_keeps_its_other_keys(self):
        root = Path(tempfile.mkdtemp(prefix="ahi-gtk-"))
        try:
            path = root / restyle.GTK_SETTINGS
            path.parent.mkdir(parents=True)
            path.write_text("[Settings]\ngtk-theme-name=Yaru\ngtk-cursor-theme-name=Yaru\ngtk-font-name=Ubuntu 11\n")
            restyle.gtk(root)
            lines = path.read_text().splitlines()
            self.assertEqual(lines[0], "[Settings]")
            self.assertIn("gtk-cursor-theme-name=Yaru", lines)
            self.assertIn("gtk-theme-name=ArtisanHub", lines)
            self.assertNotIn("gtk-theme-name=Yaru", lines)
            self.assertNotIn("gtk-font-name=Ubuntu 11", lines)
        finally:
            shutil.rmtree(root)

    def test_no_upstream_settings_file_gets_ours(self):
        root = Path(tempfile.mkdtemp(prefix="ahi-gtk-"))
        try:
            (root / "etc/gtk-3.0").mkdir(parents=True)
            restyle.gtk(root)
            self.assertEqual((root / restyle.GTK_SETTINGS).read_text(),
                             (REPO / "common/files/gtk-settings.ini").read_text())
        finally:
            shutil.rmtree(root)


class StartUpScripts(unittest.TestCase):
    def test_every_script_parses(self):
        for path in sorted((REPO / "common/files/s6").glob("*/run")) + [REPO / "common/files/browser/ahi-open-url"]:
            with self.subTest(script=path.parent.name):
                shell = "bash" if path.read_text().startswith("#!/usr/bin/with-contenv bash") else "sh"
                done = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_s6_folders_are_complete(self):
        s6 = REPO / "common/files/s6"
        for name in restyle.ONESHOTS:
            self.assertEqual((s6 / name / "type").read_text().strip(), "oneshot", name)
            self.assertTrue((s6 / name / "up").is_file(), name)
        for name in restyle.LONGRUNS:
            self.assertEqual((s6 / name / "type").read_text().strip(), "longrun", name)


class OpenerOpensTheWebOnly(unittest.TestCase):
    """ahi-open-url hands http and https addresses to Firefox and refuses anything else."""

    def run_opener(self, url):
        fake = Path(tempfile.mkdtemp(prefix="ahi-opener-"))
        opener = fake / "ahi-open-url"
        body = (REPO / "common/files/browser/ahi-open-url").read_text().replace("/usr/bin/firefox", str(fake / "firefox"))
        opener.write_text(body)
        (fake / "firefox").write_text('#!/bin/sh\necho "$@" > "$(dirname "$0")/opened"\n')
        os.chmod(opener, 0o755)
        os.chmod(fake / "firefox", 0o755)
        done = subprocess.run([str(opener), url], capture_output=True, text=True)
        opened = (fake / "opened").read_text().strip() if (fake / "opened").exists() else None
        shutil.rmtree(fake)
        return done.returncode, opened

    def test_web_addresses_open(self):
        for url in ("https://bambulab.com/en/sign-in?x=1", "http://localhost:41172/callback"):
            self.assertEqual(self.run_opener(url), (0, f"--new-tab {url}"))

    def test_anything_else_is_refused(self):
        for url in ("file:///etc/passwd", "/config", "", "javascript:alert(1)", "-P", "--new-instance"):
            code, opened = self.run_opener(url)
            self.assertNotEqual(code, 0, url)
            self.assertIsNone(opened, url)


class NoProductNamesLeftOver(unittest.TestCase):
    def test_shared_files_name_no_single_app(self):
        """The shared files serve every app: none may still be written for OrcaSlicer alone."""
        for path in sorted((REPO / "common").rglob("*")):
            if path.is_file() and path.suffix not in (".woff2",):
                with self.subTest(path=str(path.relative_to(REPO))):
                    self.assertIsNone(re.search(r"orca", path.read_text(errors="ignore"), re.I))


if __name__ == "__main__":
    unittest.main()
