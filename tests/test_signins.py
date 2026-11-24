"""Tests for common/files/browser/ahi_signins.py (OPHQ-163): two desktops' Firefox profiles, made here with
Firefox's own cookie table, share their sign-ins through one folder.

    python3 -m unittest tests.test_signins
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ahi_signins", REPO / "common/files/browser/ahi_signins.py")
signins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signins)

# Firefox's moz_cookies, as recent versions make it.
SCHEMA = """CREATE TABLE moz_cookies (id INTEGER PRIMARY KEY, originAttributes TEXT NOT NULL DEFAULT '',
name TEXT, value TEXT, host TEXT, path TEXT, expiry INTEGER, lastAccessed INTEGER, creationTime INTEGER,
isSecure INTEGER, isHttpOnly INTEGER, inBrowserElement INTEGER DEFAULT 0, sameSite INTEGER DEFAULT 0,
schemeMap INTEGER DEFAULT 0, isPartitionedAttributeSet INTEGER DEFAULT 0,
CONSTRAINT moz_uniqueid UNIQUE (name, host, path, originAttributes))"""
LATER = int((time.time() + 86400) * 1000)


def cookie(prof: Path, host: str, name: str, value: str, used: int, expiry: int = LATER) -> None:
    con = sqlite3.connect(prof / "cookies.sqlite")
    con.execute("DELETE FROM moz_cookies WHERE host = ? AND name = ?", (host, name))
    con.execute("INSERT INTO moz_cookies (name, value, host, path, expiry, lastAccessed, creationTime, isSecure, "
                "isHttpOnly) VALUES (?, ?, ?, '/', ?, ?, ?, 1, 1)", (name, value, host, expiry, used, used))
    con.commit()
    con.close()


def cookies(prof: Path) -> dict:
    con = sqlite3.connect(prof / "cookies.sqlite")
    out = {(h, n): v for h, n, v in con.execute("SELECT host, name, value FROM moz_cookies")}
    con.close()
    return out


class Signins(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="ahi-signins-"))
        self.shared = self.dir / "shared"
        self.a, self.b = self.dir / "a", self.dir / "b"
        for p in (self.a, self.b):
            p.mkdir()
            con = sqlite3.connect(p / "cookies.sqlite")
            con.execute(SCHEMA)
            con.close()
        app = self.dir / "firefox"
        app.mkdir()
        (app / "application.ini").write_text("[App]\nName=Firefox\nVersion=140.5.0\n")
        signins.FIREFOX_DIRS = (app,)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_sign_in_in_one_desktop_is_there_in_the_next(self):
        cookie(self.a, ".makerworld.com", "token", "from-a", 100)
        signins.do_export(self.a, self.shared)
        signins.do_import(self.b, self.shared)
        self.assertEqual(cookies(self.b), {(".makerworld.com", "token"): "from-a"})
        self.assertEqual(oct((self.shared / signins.COOKIES_JSON).stat().st_mode & 0o777), "0o600")

    def test_the_most_recently_used_cookie_wins_and_expired_ones_are_dropped(self):
        cookie(self.a, ".bambulab.com", "token", "old", 100)
        cookie(self.a, ".gone.example", "s", "x", 100, expiry=int((time.time() - 60) * 1000))
        signins.do_export(self.a, self.shared)
        cookie(self.b, ".bambulab.com", "token", "new", 200)
        signins.do_export(self.b, self.shared)
        signins.do_import(self.a, self.shared)
        self.assertEqual(cookies(self.a)[(".bambulab.com", "token")], "new")
        shared = json.loads((self.shared / signins.COOKIES_JSON).read_text())
        self.assertEqual([c["host"] for c in shared], [".bambulab.com"])
        # And a desktop's newer cookie is never replaced by an older shared one.
        cookie(self.b, ".bambulab.com", "token", "newest", 300)
        signins.do_import(self.b, self.shared)
        self.assertEqual(cookies(self.b)[(".bambulab.com", "token")], "newest")

    def test_a_new_profile_starts_signed_in_on_the_same_firefox(self):
        cookie(self.a, ".prusa3d.com", "sid", "p", 100)
        signins.do_export(self.a, self.shared)
        fresh = self.dir / "fresh"
        fresh.mkdir()
        signins.do_import(fresh, self.shared)
        self.assertEqual(cookies(fresh), {(".prusa3d.com", "sid"): "p"})
        # Another Firefox version does not take a table it did not make.
        (self.dir / "firefox" / "application.ini").write_text("[App]\nName=Firefox\nVersion=145.0\n")
        other = self.dir / "other"
        other.mkdir()
        signins.do_import(other, self.shared)
        self.assertFalse((other / "cookies.sqlite").exists())

    def test_saved_passwords_are_shared_through_one_key(self):
        (self.a / signins.KEY).write_bytes(b"key-of-a")
        (self.a / signins.LOGINS).write_text(json.dumps({"nextId": 2, "logins": [
            {"guid": "{1}", "hostname": "https://bambulab.com", "timePasswordChanged": 10}]}))
        signins.do_export(self.a, self.shared)
        self.assertEqual((self.shared / signins.KEY).read_bytes(), b"key-of-a")
        signins.do_import(self.b, self.shared)
        self.assertEqual((self.b / signins.KEY).read_bytes(), b"key-of-a")
        self.assertEqual([x["guid"] for x in json.loads((self.b / signins.LOGINS).read_text())["logins"]], ["{1}"])
        # A desktop with passwords under a key of its own keeps them and its key; nothing is mixed.
        c = self.dir / "c"
        c.mkdir()
        (c / signins.KEY).write_bytes(b"key-of-c")
        (c / signins.LOGINS).write_text(json.dumps({"logins": [{"guid": "{9}", "timePasswordChanged": 1}]}))
        signins.do_import(c, self.shared)
        signins.do_export(c, self.shared)
        self.assertEqual((c / signins.KEY).read_bytes(), b"key-of-c")
        shared = json.loads((self.shared / signins.LOGINS).read_text())
        self.assertEqual([x["guid"] for x in shared["logins"]], ["{1}"])

    def test_the_profile_is_firefoxs_default_or_one_of_its_own(self):
        home = self.dir / "home"
        signins.MOZILLA = home / ".mozilla" / "firefox"
        signins.OWN_PROFILE = signins.MOZILLA / "ahi.default"
        self.assertEqual(signins.profile(), signins.OWN_PROFILE)
        mine = signins.MOZILLA / "x1.default-release"
        mine.mkdir(parents=True)
        (signins.MOZILLA / "profiles.ini").write_text(
            "[Install4F96D1932A9F858E]\nDefault=x1.default-release\n\n"
            "[Profile0]\nName=default-release\nIsRelative=1\nPath=x1.default-release\n")
        self.assertEqual(signins.profile(), mine)


if __name__ == "__main__":
    unittest.main()
