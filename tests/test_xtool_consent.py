"""Tests for apps/xtoolstudio's first-run questions (root/usr/local/lib/ahi/xtool_consent.py), on a small app.asar
made here in the shape of xTool Studio's (the repository holds none of xTool's files) and a stand-in zenity that
answers as told and records what it was asked.

    python3 -m unittest tests.test_xtool_consent
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "apps/xtoolstudio/root/usr/local/lib/ahi/xtool_consent.py"
spec = importlib.util.spec_from_file_location("xtool_consent", SCRIPT)
consent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consent)

UTILS = (
    "function Mi(e){let t={us:{privacyPolicyAccepted:`privacyPolicyAccepted`,privacyPolicyVersion:"
    "`privacyPolicyVersion`,version:he},cn:{privacyPolicyAccepted:`privacyPolicyAcceptedCN`,privacyPolicyVersion:"
    "`privacyPolicyVersionCN`,version:ge}};return t[e]||t.us}var pe=`STUDIO_AREA`,me=`COUNTRY_KEY`,he=`1.0.2`,"
    "ge=`1.0.1`;"
)
REGIONS = (
    "var XT={en:[{code:`AF`,name:`Afghanistan`},{code:`US`,name:`United States`},{code:`CN`,name:`China`}],"
    "de:[{code:`US`,name:`Vereinigte Staaten`}]};var QT={CN:`cn`,US:`us`};function $T(e){return QT[e]||`us`}"
    "let r=$T(n);F.set(qe,n),F.set(nt,r),await F.save(!0)"
)
PLAN = """<script>const words = {
        en: {
          inviteBody: 'Join xTool\\'s plan?',
          tierSuper: 'Super Co-creator',
          tierSuperDesc: 'Share data.',
          tierClose: 'Not participating',
          tierCloseTip: 'Safety data still collected.',
        },
        de: { tierClose: 'Nein' },
      }</script>"""
FILES = {
    "package.json": json.dumps({"version": "1.11.9"}),
    ".vite/build/utils-A.js": UTILS,
    ".vite/build/app-B.js": REGIONS,
    ".vite/renderer/shell/improvement-plan.html": PLAN,
    **{
        f".vite/renderer/shell/privacy/us/{doc}/en.html": f"<html><head><style>x</style></head><body><p>{doc} "
        "text</p><p>Second <b>para</b>graph</p></body></html>"
        for doc in ("service-terms", "safety-terms", "privacy-policy", "eu-uk-notice")
    },
    ".vite/renderer/shell/privacy/cn/privacy-policy/zh.html": "<p>cn</p>",
}

ZENITY = """#!/usr/bin/env bash
printf '%s\\036' "$*" >> "$ZENITY_LOG"
case "$*" in
  *--radiolist*) [ -n "$ANSWER_PLAN" ] && echo "$ANSWER_PLAN"; exit ${ANSWER_PLAN_EXIT:-0} ;;
  *--list*) [ -n "$ANSWER_COUNTRY" ] && echo "$ANSWER_COUNTRY"; exit ${ANSWER_COUNTRY_EXIT:-0} ;;
  *--text-info*) exit ${ANSWER_TERMS_EXIT:-0} ;;
  *) exit 0 ;;
esac
"""


def make_asar(path: Path, files: dict[str, str]) -> None:
    index: dict = {"files": {}}
    data = b""
    for rel, text in files.items():
        node = index
        *dirs, name = rel.split("/")
        for d in dirs:
            node = node["files"].setdefault(d, {"files": {}})
        body = text.encode()
        node["files"][name] = {"size": len(body), "offset": str(len(data))}
        data += body
    head = json.dumps(index).encode()
    padded = head + b"\0" * (-len(head) % 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        struct.pack("<IIII", 4, len(padded) + 8, len(padded) + 4, len(head)) + padded + data
    )


class Consent(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="ahi-xtool-"))
        prefix = self.dir / "data/prefix"
        make_asar(prefix / consent.APP_DIR / "resources/app.asar", FILES)
        self.config = prefix / consent.CONFIG
        bin_dir = self.dir / "bin"
        bin_dir.mkdir()
        (bin_dir / "zenity").write_text(ZENITY)
        (bin_dir / "zenity").chmod(0o755)
        self.log = self.dir / "zenity.log"
        self.env = dict(os.environ)
        os.environ.update(
            PATH=f"{bin_dir}:{os.environ['PATH']}", ZENITY_LOG=str(self.log), ANSWER_COUNTRY="US",
            ANSWER_PLAN="close",
        )
        for k in ("ANSWER_COUNTRY_EXIT", "ANSWER_TERMS_EXIT", "ANSWER_PLAN_EXIT"):
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.env)
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_it(self) -> int:
        return consent.main(["xtool_consent.py", str(self.dir / "data")])

    def asked(self) -> list[str]:
        return [c for c in self.log.read_text().split("\x1e") if c] if self.log.exists() else []

    def test_reads_what_this_version_records(self):
        f = consent.facts(consent.Asar(self.dir / "data/prefix" / consent.APP_DIR / "resources/app.asar"))
        self.assertEqual(f["version"], {"us": "1.0.2", "cn": "1.0.1"})
        self.assertEqual(f["accepted"], {"us": "privacyPolicyAccepted", "cn": "privacyPolicyAcceptedCN"})
        self.assertEqual(f["area_of"], {"CN": "cn", "US": "us"})
        self.assertEqual([c["code"] for c in f["countries"]], ["AF", "US", "CN"])
        self.assertEqual(f["plan"]["inviteBody"], "Join xTool's plan?")
        self.assertEqual(f["app_version"], "1.11.9")

    def test_the_persons_answers_are_written_as_xtools_own_windows_write_them(self):
        self.assertEqual(self.run_it(), 0)
        config = json.loads(self.config.read_text())
        self.assertEqual(config["COUNTRY_KEY"], "US")
        self.assertEqual(config["STUDIO_AREA"], "us")
        self.assertIs(config["privacyPolicyAccepted"], True)
        self.assertEqual(config["privacyPolicyVersion"], "1.0.2")
        plan = config["improvementPlan"]
        self.assertEqual((plan["tier"], plan["promptedVersion"], plan["pendingPrompt"]), ("close", "1.11.9", False))
        asked = self.asked()
        self.assertEqual(len(asked), 3)
        self.assertIn("United States US", asked[0])
        self.assertTrue(asked[0].index("United States") < asked[0].index("Afghanistan"))  # xTool's first
        self.assertIn("--checkbox=I have read and agree", asked[1])
        # Asked once: the next start goes straight to xTool Studio.
        self.log.unlink()
        self.assertEqual(self.run_it(), 0)
        self.assertEqual(self.asked(), [])

    def test_the_terms_shown_are_xtools_own_text(self):
        shown = []
        real = consent.zenity

        def spy(*args, stdin=None):
            for a in args:
                if a.startswith("--filename="):
                    shown.append(Path(a.split("=", 1)[1]).read_text())
            return real(*args, stdin=stdin)

        consent.zenity = spy
        try:
            self.run_it()
        finally:
            consent.zenity = real
        text = shown[0]
        for doc in ("service-terms", "safety-terms", "privacy-policy", "eu-uk-notice"):
            self.assertIn(f"{doc} text\n\nSecond paragraph", text)
        self.assertNotIn("<", text)

    def test_declining_or_closing_writes_nothing_and_does_not_start(self):
        for key, value in (("ANSWER_COUNTRY_EXIT", "1"), ("ANSWER_TERMS_EXIT", "1"), ("ANSWER_PLAN_EXIT", "1")):
            with self.subTest(declined=key):
                os.environ[key] = value
                if key == "ANSWER_COUNTRY_EXIT":
                    os.environ["ANSWER_COUNTRY"] = ""
                self.assertEqual(self.run_it(), 1)
                self.assertFalse(self.config.exists())
                os.environ.pop(key)
                os.environ["ANSWER_COUNTRY"] = "US"

    def test_a_new_policy_version_asks_again_and_keeps_other_settings(self):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps({
            "COUNTRY_KEY": "US", "STUDIO_AREA": "us", "privacyPolicyAccepted": True,
            "privacyPolicyVersion": "1.0.1", "improvementPlan": {"tier": "super"}, "deviceId": "abc",
        }))
        self.assertEqual(self.run_it(), 0)
        asked = self.asked()
        self.assertEqual(len(asked), 1)  # the terms alone: the country is set and the plan joined
        self.assertIn("--text-info", asked[0])
        config = json.loads(self.config.read_text())
        self.assertEqual((config["privacyPolicyVersion"], config["deviceId"]), ("1.0.2", "abc"))
        self.assertEqual(config["improvementPlan"], {"tier": "super"})

    def test_china_mainland_uses_xtools_cn_keys(self):
        os.environ["ANSWER_COUNTRY"] = "CN"
        self.assertEqual(self.run_it(), 0)
        config = json.loads(self.config.read_text())
        self.assertEqual((config["STUDIO_AREA"], config["privacyPolicyVersionCN"]), ("cn", "1.0.1"))
        self.assertIs(config["privacyPolicyAcceptedCN"], True)
        self.assertNotIn("privacyPolicyAccepted", config)

    def test_a_version_it_cannot_read_does_not_start(self):
        make_asar(self.dir / "data/prefix" / consent.APP_DIR / "resources/app.asar", {"package.json": "{}"})
        self.assertEqual(self.run_it(), 1)
        self.assertIn("--error", self.asked()[0])
        self.assertFalse(self.config.exists())


if __name__ == "__main__":
    unittest.main()
