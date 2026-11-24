#!/usr/bin/env python3
"""xTool Studio's first-run questions, asked by the desktop because xTool's own windows for them open blank under
Wine (their pages load a script Wine's Chromium cannot run in a sandboxed window).

    xtool_consent.py <wine app data folder>

xTool Studio asks, once, before its main window: the person's country or region; that they agree to xTool's
Terms of Use, Safety Terms and Privacy Policy; and whether they join xTool's improvement plan. This asks the same
questions, in the same order, showing xTool's own text from the xTool Studio just installed (its app.asar), and
writes the answers to xTool Studio's own settings file under the same names its windows use. Nothing is ever
answered for the person: a question not answered, or terms not agreed to, writes nothing and xTool Studio does not
start. The keys and the policy's version come from the installed app too, so a new xTool version that changes
them asks again, as xTool would.

Exit 0: xTool Studio may start. Exit 1: it may not (the person declined or closed a question).
"""

from __future__ import annotations

import html
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

USER = "abc"
APP_DIR = Path("drive_c/users") / USER / "AppData/Local/Programs/xTool Studio"
CONFIG = Path("drive_c/users") / USER / "AppData/Roaming/xTool Studio/config.json"
TITLE = "xTool Studio"
# xTool's own recommended countries, first in its list; the rest follow alphabetically.
FIRST = ("US", "CN", "DE", "FR", "GB", "ES", "CA", "AU", "JP", "TH")


class Asar:
    """Reads files from an Electron app.asar (the archive format is public: a JSON index, then the files)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        with path.open("rb") as f:
            head = f.read(16)
            header_size = struct.unpack("<I", head[4:8])[0]
            json_size = struct.unpack("<I", head[12:16])[0]
            self.index = json.loads(f.read(json_size))
        self.base = 8 + header_size

    def _entry(self, rel: str) -> dict:
        node = self.index
        for part in rel.split("/"):
            node = node["files"][part]
        return node

    def read(self, rel: str) -> str:
        entry = self._entry(rel)
        with self.path.open("rb") as f:
            f.seek(self.base + int(entry["offset"]))
            return f.read(entry["size"]).decode("utf-8")

    def names(self, rel: str) -> list[str]:
        return sorted(self._entry(rel)["files"])


def text_of(page: str) -> str:
    """A document page's words, as plain paragraphs (the page's own line breaks are only its source's wrapping)."""
    page = re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", page)
    page = re.sub(r"(?i)<li[^>]*>", "\x00- ", page)
    page = re.sub(r"(?i)<br\s*/?>|</?(p|div|h[1-6]|ul|ol|li|tr|table|section)\b[^>]*>", "\x00", page)
    page = html.unescape(re.sub(r"<[^>]+>", "", page))
    blocks = (re.sub(r"\s+", " ", block).strip() for block in page.split("\x00"))
    return "\n\n".join(block for block in blocks if block)


def find(pattern: str, source: str, what: str) -> re.Match:
    match = re.search(pattern, source)
    if not match:
        raise LookupError(what)
    return match


def facts(app: Asar) -> dict:
    """What this xTool Studio version's first run records, read from its own code."""
    build = ".vite/build"
    code = {name: app.read(f"{build}/{name}") for name in app.names(build) if name.endswith(".js")}
    utils = next(src for src in code.values() if "privacyPolicyAccepted:`privacyPolicyAccepted`" in src)
    keys = find(
        r"us:\{privacyPolicyAccepted:`(\w+)`,privacyPolicyVersion:`(\w+)`,version:(\w+)\},"
        r"cn:\{privacyPolicyAccepted:`(\w+)`,privacyPolicyVersion:`(\w+)`,version:(\w+)\}",
        utils,
        "the privacy policy's keys",
    )
    version = {
        area: find(rf"\b{re.escape(var)}=`([0-9.]+)`", utils, f"the {area} privacy policy version").group(1)
        for area, var in (("us", keys.group(3)), ("cn", keys.group(6)))
    }
    regions = next(src for src in code.values() if "function $T(e){return QT[e]||`us`}" in src)
    area_of = dict(
        re.findall(r"(\w+):`(us|cn)`", find(r"var QT=\{([^}]*)\}", regions, "the country areas").group(1))
    )
    countries = json.loads(
        re.sub(
            r"(\{|,)(code|name):",
            r'\1"\2":',
            find(r"en:(\[\{code:`[A-Z]{2}`,name:`[^`]*`\}(?:,\{code:`[A-Z]{2}`,name:`[^`]*`\})*\])", regions,
                 "the country list").group(1).replace("`", '"'),
        )
    )
    # The country window records the country and its area under these names (its code, and the onboarding's).
    for key in ("COUNTRY_KEY", "STUDIO_AREA"):
        find(rf"`{key}`", utils, "the country keys")
    find(r"F\.set\(\w+,n\),F\.set\(\w+,r\)", regions, "the country keys")
    plan = app.read(".vite/renderer/shell/improvement-plan.html")
    en = find(r"(?s)en: \{(.*?)\n\s*\},", plan, "the improvement plan's words").group(1)
    words = {k: v.replace("\\'", "'") for k, v in re.findall(r"(\w+):\s*'((?:[^'\\]|\\.)*)'", en)}
    return {
        "app_version": json.loads(app.read("package.json"))["version"],
        "accepted": {"us": keys.group(1), "cn": keys.group(4)},
        "version_key": {"us": keys.group(2), "cn": keys.group(5)},
        "version": version,
        "area_of": area_of,
        "countries": countries,
        "plan": words,
    }


def zenity(*args: str, stdin: str | None = None) -> tuple[int, str]:
    done = subprocess.run(
        ["zenity", f"--title={TITLE}", *args], input=stdin, capture_output=True, text=True, check=False
    )
    return done.returncode, done.stdout.strip()


def ask_country(f: dict) -> str | None:
    by_code = {c["code"]: c["name"] for c in f["countries"]}
    order = [c for c in FIRST if c in by_code] + sorted(
        (c for c in by_code if c not in FIRST), key=lambda c: by_code[c]
    )
    rows = [x for code in order for x in (by_code[code], code)]
    code, picked = zenity(
        "--list", "--width=460", "--height=560", "--text=Where are you? xTool Studio asks this once, to set "
        "which xTool services, terms and privacy policy apply to you.", "--column=Country or region",
        "--column=Code", "--hide-column=2", "--print-column=2", *rows,
    )
    return picked.split("|")[0] if code == 0 and picked else None


def ask_terms(app: Asar, area: str) -> bool:
    if area == "cn":
        base, docs = ".vite/renderer/shell/privacy/cn", app.names(".vite/renderer/shell/privacy/cn")
    else:
        base, docs = ".vite/renderer/shell/privacy/us", ("service-terms", "safety-terms", "privacy-policy",
                                                         "eu-uk-notice")
    parts = []
    for doc in docs:
        lang = "en.html" if "en.html" in app.names(f"{base}/{doc}") else app.names(f"{base}/{doc}")[0]
        parts.append(text_of(app.read(f"{base}/{doc}/{lang}")))
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(("\n\n" + "=" * 60 + "\n\n").join(parts))
    try:
        code, _ = zenity(
            "--text-info", f"--filename={tmp.name}", "--width=760", "--height=640",
            "--checkbox=I have read and agree to xTool's Terms of Use, Safety Terms and Privacy Policy",
        )
    finally:
        os.unlink(tmp.name)
    return code == 0


def ask_plan(f: dict) -> str | None:
    w = f["plan"]
    text = "\n\n".join(
        html.escape(s)
        for s in (
            w.get("inviteBody", "Join xTool's improvement plan?"),
            f"{w.get('tierSuper', 'Join')}: {w.get('tierSuperDesc', '')}",
            f"{w.get('tierClose', 'Not participating')}: {w.get('tierCloseTip', '')}",
        )
    )
    code, picked = zenity(
        "--list", "--radiolist", "--width=560", "--height=420", f"--text={text}", "--column=",
        "--column=Choice", "--column=Tier", "--hide-column=3", "--print-column=3",
        "TRUE", w.get("tierClose", "Not participating"), "close",
        "FALSE", w.get("tierSuper", "Join"), "super",
    )
    return picked if code == 0 and picked in ("super", "close") else None


def main(argv: list[str]) -> int:
    prefix = Path(argv[1]) / "prefix"
    config_path = prefix / CONFIG
    try:
        app = Asar(prefix / APP_DIR / "resources/app.asar")
        f = facts(app)
    except (OSError, LookupError, ValueError, KeyError, StopIteration) as exc:
        zenity("--error", "--width=460", f"--text=This version of xTool Studio asks its first-run questions in a way "
               f"this desktop does not know yet ({html.escape(str(exc) or type(exc).__name__)}), so it cannot "
               "start here. Ask your hub's owner to update the desktop app.")
        return 1
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}

    country = config.get("COUNTRY_KEY")
    area = config.get("STUDIO_AREA") or (f["area_of"].get(country, "us") if country else None)
    need_country = not country and not config.get("STUDIO_AREA")
    plan = config.get("improvementPlan") if isinstance(config.get("improvementPlan"), dict) else {}
    answers: dict = {}

    if need_country:
        country = ask_country(f)
        if not country:
            return 1
        area = f["area_of"].get(country, "us")
        answers["COUNTRY_KEY"], answers["STUDIO_AREA"] = country, area
    area = area if area in ("us", "cn") else "us"
    agreed = config.get(f["accepted"][area]) is True and config.get(f["version_key"][area]) == f["version"][area]
    if not agreed:
        if not ask_terms(app, area):
            zenity("--info", "--width=420", "--text=xTool Studio only starts once you agree to xTool's terms. "
                   "Open it again from the desktop's menu (right-click the desktop) when you are ready.")
            return 1
        answers[f["accepted"][area]] = True
        answers[f["version_key"][area]] = f["version"][area]
    # As xTool's own check: asked while a prompt is pending, or until the person has joined, for each new version
    # when they have not.
    joined = plan.get("tier") == "super"
    if plan.get("pendingPrompt") or (not joined and plan.get("promptedVersion") != f["app_version"]):
        tier = ask_plan(f)
        if not tier:
            return 1
        answers["improvementPlan"] = {
            **plan,
            "tier": tier,
            "decidedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "promptedVersion": f["app_version"],
            "pendingPrompt": False,
        }

    if answers:
        config.update(answers)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = config_path.with_suffix(".json.ahi")
        tmp.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(config_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
