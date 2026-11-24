#!/usr/bin/env python3
"""OpenPrintHQ: one set of web sign-ins for every desktop's Firefox (OPHQ-163).

    ahi_signins.py profile                    the Firefox profile this desktop uses (made when there is none)
    ahi_signins.py import <profile> <shared>  the shared sign-ins into the profile, before Firefox starts
    ahi_signins.py export <profile> <shared>  the profile's sign-ins into the shared folder

The installer mounts one folder of sign-ins in every desktop (one per person, with a desktop each): <shared>,
/ahi-browser. Firefox cannot open one profile from two places at once, so each desktop keeps its own profile and
this merges what makes a person signed in:

- Cookies, one by one (by site, name, path and container), the most recently used kept. Expired ones are dropped.
- Saved passwords (logins.json), one by one (by their id), the most recently changed kept, should a desktop's
  Firefox save any: the desktops' policies turn the password manager off (policies.json), so today there are
  none. Firefox encrypts them with the profile's key (key4.db), so every desktop's Firefox uses the shared
  folder's key: a profile with no passwords of its own takes it; one with its own key keeps it and its own.

Nothing else of the profile is shared (history, open tabs, settings). The shared folder is written under a lock
and each file replaced whole, so two desktops writing at once do not mix their writes.
"""

from __future__ import annotations

import configparser
import fcntl
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/config"))
MOZILLA = HOME / ".mozilla" / "firefox"
OWN_PROFILE = MOZILLA / "ahi.default"
COOKIES_JSON = "cookies.json"
# An empty cookie table from a desktop's Firefox, and that Firefox's version: a new profile on the same version
# starts from it, so the sign-ins are there at its very first start.
TEMPLATE = "cookies-empty.sqlite"
TEMPLATE_VERSION = "cookies-empty.version"
FIREFOX_DIRS = (Path("/usr/lib/firefox"), Path("/usr/lib/firefox-esr"))
KEY = "key4.db"
LOGINS = "logins.json"
# A cookie's identity in Firefox's own table.
COOKIE_KEY = ("host", "name", "path", "originAttributes")


def profile() -> Path:
    """The default profile Firefox already has here, or this desktop's own one (made empty)."""
    ini = MOZILLA / "profiles.ini"
    if ini.is_file():
        cfg = configparser.RawConfigParser()
        cfg.read(ini, encoding="utf-8")
        chosen = [s for s in cfg.sections() if s.startswith("Install") and cfg.has_option(s, "Default")]
        paths = [cfg.get(s, "Default") for s in chosen]
        paths += [cfg.get(s, "Path") for s in cfg.sections()
                  if s.startswith("Profile") and cfg.get(s, "Default", fallback="0") == "1"]
        for rel in paths:
            for sec in cfg.sections():
                if cfg.get(sec, "Path", fallback=None) == rel:
                    p = MOZILLA / rel if cfg.get(sec, "IsRelative", fallback="1") == "1" else Path(rel)
                    if p.is_dir():
                        return p
            p = MOZILLA / rel
            if p.is_dir():
                return p
    OWN_PROFILE.mkdir(parents=True, exist_ok=True)
    return OWN_PROFILE


@contextmanager
def locked(shared: Path):
    shared.mkdir(parents=True, exist_ok=True)
    with open(shared / ".lock", "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def write_whole(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def expired(cookie: dict, now: float) -> bool:
    exp = cookie.get("expiry") or 0
    # Firefox keeps the expiry in seconds, and in milliseconds since version 133.
    exp = exp / 1000 if exp > 10**11 else exp
    return bool(exp) and exp < now


def used(cookie: dict) -> int:
    return int(cookie.get("lastAccessed") or 0)


def firefox_version() -> str:
    for d in FIREFOX_DIRS:
        ini = d / "application.ini"
        if ini.is_file():
            cfg = configparser.RawConfigParser()
            cfg.read(ini, encoding="utf-8")
            return cfg.get("App", "Version", fallback="")
    return ""


def key_of(cookie: dict) -> tuple:
    return tuple(cookie.get(k) for k in COOKIE_KEY)


# Cookies


def read_cookies(prof: Path) -> list[dict]:
    db = prof / "cookies.sqlite"
    if not db.is_file():
        return []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute("SELECT * FROM moz_cookies")]
        con.close()
    except sqlite3.Error:
        return []
    for r in rows:
        r.pop("id", None)
    return rows


def merge(a: list[dict], b: list[dict]) -> list[dict]:
    now = time.time()
    out: dict[tuple, dict] = {}
    for c in [*a, *b]:
        if expired(c, now):
            continue
        k = key_of(c)
        if k not in out or used(c) >= used(out[k]):
            out[k] = c
    return list(out.values())


def write_cookies(prof: Path, cookies: list[dict]) -> int:
    """The cookies into the profile's own table (Firefox not running), each kept when the profile's is newer."""
    db = prof / "cookies.sqlite"
    if not db.is_file():
        return 0
    con = sqlite3.connect(db, timeout=10)
    cols = [r[1] for r in con.execute("PRAGMA table_info(moz_cookies)") if r[1] != "id"]
    have = {}
    for row in con.execute(f"SELECT {', '.join(COOKIE_KEY)}, lastAccessed FROM moz_cookies"):
        have[tuple(row[:4])] = row[4] or 0
    done = 0
    for c in cookies:
        k = key_of(c)
        if k in have and have[k] >= used(c):
            continue
        row = {n: c[n] for n in cols if n in c}
        if not all(n in row for n in COOKIE_KEY):
            continue
        con.execute(f"DELETE FROM moz_cookies WHERE {' AND '.join(f'{n} = ?' for n in COOKIE_KEY)}", k)
        con.execute(f"INSERT INTO moz_cookies ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                    list(row.values()))
        done += 1
    con.commit()
    con.close()
    return done


# Saved passwords


def read_logins(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def merge_logins(a: dict, b: dict) -> dict:
    by_id: dict[str, dict] = {}
    for login in [*(a.get("logins") or []), *(b.get("logins") or [])]:
        k = login.get("guid") or f"{login.get('hostname')}|{login.get('encryptedUsername')}"
        mine = by_id.get(k)
        changed = int(login.get("timePasswordChanged") or 0)
        if mine is None or changed >= int(mine.get("timePasswordChanged") or 0):
            by_id[k] = login
    out = {**b, **a}
    out["logins"] = list(by_id.values())
    out["nextId"] = len(out["logins"]) + 1
    return out


def same_key(prof: Path, shared: Path) -> bool:
    a, b = prof / KEY, shared / KEY
    return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()


# The two directions


def do_import(prof: Path, shared: Path) -> None:
    with locked(shared):
        cookies = json.loads((shared / COOKIES_JSON).read_text()) if (shared / COOKIES_JSON).is_file() else []
        db = prof / "cookies.sqlite"
        template = shared / TEMPLATE
        if not db.is_file() and template.is_file():
            # A profile Firefox has not opened yet: from the empty table of the same Firefox version, if any.
            seen = (shared / TEMPLATE_VERSION).read_text().strip() if (shared / TEMPLATE_VERSION).is_file() else ""
            if seen and seen == firefox_version():
                shutil.copyfile(template, db)
        n = write_cookies(prof, merge([], cookies))
        mine = read_logins(prof / LOGINS)
        if (shared / KEY).is_file() and not (mine.get("logins")) and not same_key(prof, shared):
            # No passwords of its own: this profile takes the shared key, so it can read the shared passwords.
            shutil.copy2(shared / KEY, prof / KEY)
        if same_key(prof, shared) and (shared / LOGINS).is_file():
            merged = merge_logins(read_logins(shared / LOGINS), mine)
            write_whole(prof / LOGINS, json.dumps(merged).encode())
    print(f"ahi-signins: {n} sign-in cookies taken in")


def do_export(prof: Path, shared: Path) -> None:
    with locked(shared):
        old = json.loads((shared / COOKIES_JSON).read_text()) if (shared / COOKIES_JSON).is_file() else []
        cookies = merge(old, read_cookies(prof))
        write_whole(shared / COOKIES_JSON, json.dumps(cookies).encode())
        os.chmod(shared / COOKIES_JSON, 0o600)
        version = firefox_version()
        if (prof / "cookies.sqlite").is_file() and version:
            seen = (shared / TEMPLATE_VERSION).read_text().strip() if (shared / TEMPLATE_VERSION).is_file() else ""
            if seen != version:
                fd, tmp = tempfile.mkstemp(dir=shared, prefix=".template.")
                os.close(fd)
                os.unlink(tmp)
                con = sqlite3.connect(f"file:{prof / 'cookies.sqlite'}?mode=ro", uri=True, timeout=5)
                con.execute("VACUUM INTO ?", (tmp,))
                con.close()
                empty = sqlite3.connect(tmp)
                empty.execute("DELETE FROM moz_cookies")
                empty.commit()
                empty.execute("VACUUM")
                empty.close()
                os.replace(tmp, shared / TEMPLATE)
                write_whole(shared / TEMPLATE_VERSION, version.encode())
        mine = read_logins(prof / LOGINS)
        if mine.get("logins") and (prof / KEY).is_file():
            if not (shared / KEY).is_file():
                # The first desktop with passwords gives everyone its key.
                write_whole(shared / KEY, (prof / KEY).read_bytes())
                os.chmod(shared / KEY, 0o600)
            if same_key(prof, shared):
                merged = merge_logins(mine, read_logins(shared / LOGINS))
                write_whole(shared / LOGINS, json.dumps(merged).encode())
                os.chmod(shared / LOGINS, 0o600)


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "profile":
        print(profile())
        return 0
    if len(argv) == 4 and argv[1] in ("import", "export"):
        prof, shared = Path(argv[2]), Path(argv[3])
        try:
            (do_import if argv[1] == "import" else do_export)(prof, shared)
        except (OSError, sqlite3.Error, ValueError) as exc:
            print(f"ahi-signins: {argv[1]} skipped: {exc}", file=sys.stderr)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
