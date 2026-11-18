"""Scanner tests against generated fixture projects. Run: python3 -m unittest discover tests"""
from __future__ import annotations

import io
import json
import plistlib
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "cleared-for-takeoff" / "scripts"))
sys.path.insert(0, str(REPO / "evals" / "fixtures"))

import build_fixtures  # noqa: E402
from preflight.cli import main, run  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="preflight-tests-"))
build_fixtures.build(TMP)


def rules(name: str) -> dict:
    _, findings, _, _, errors = run(str(TMP / name))
    assert not errors, errors
    out = {}
    for f in findings:
        out.setdefault(f.rule, []).append(f)
    return out


class SwiftBroken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = rules("swift-broken")

    def test_expected_rules(self):
        expected = {
            "privacy-strings/missing-key", "privacy-strings/vague", "privacy-manifest/missing",
            "assets/icon-alpha", "assets/no-launch-screen", "assets/ipad-orientations",
            "build-config/bad-version", "build-config/ext-bundle-id", "build-config/trademark-name",
            "code/uiwebview", "code/custom-review-prompt", "secrets/stripe-secret",
            "login-services/no-equivalent", "account-deletion/missing", "payments/no-restore",
            "payments/sub-disclosure", "payments/hardcoded-price", "networking/ats-disabled",
            "networking/ipv4-literal", "content/placeholder", "content/other-platform",
            "hidden-features/review-detection", "ai-consent/missing", "entitlements/bg-mode-unused",
        }
        self.assertTrue(expected <= set(self.r), expected - set(self.r))

    def test_extension_manifest_is_blocker(self):
        widget = [f for f in self.r["privacy-manifest/missing"] if f.target == "BrokenWidget"]
        self.assertEqual(widget[0].severity, "BLOCKER")
        self.assertIn("UserDefaults", widget[0].evidence)

    def test_camera_key_cites_line(self):
        f = self.r["privacy-strings/missing-key"][0]
        self.assertEqual((f.file, f.line), ("Broken/CameraView.swift", 6))

    def test_debug_only_code_ignored(self):
        self.assertFalse(any("Debug.swift" in (f.file or "") for fs in self.r.values() for f in fs))

    def test_location_key_present_not_missing(self):
        self.assertFalse(any("NSLocationWhenInUse" in f.title for f in self.r["privacy-strings/missing-key"]))


class SwiftClean(unittest.TestCase):
    def test_no_findings(self):
        r = rules("swift-clean")
        self.assertEqual(r, {}, {k: [f.evidence for f in v] for k, v in r.items()})


class ExpoBroken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = rules("expo-broken")

    def test_expected_rules(self):
        expected = {"privacy-strings/expo-default-string", "privacy-manifest/expo-missing", "assets/icon-size",
                    "att/missing", "code/eval", "code/ota", "payments/no-restore", "account-deletion/missing",
                    "login-services/no-equivalent", "content/placeholder", "payments/hardcoded-price"}
        self.assertTrue(expected <= set(self.r), expected - set(self.r))

    def test_platform_check_not_flagged(self):
        self.assertNotIn("content/other-platform", self.r)


class FlutterBroken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = rules("flutter-broken")

    def test_plugin_keys(self):
        titles = " ".join(f.title for f in self.r["privacy-strings/missing-key"])
        self.assertIn("NSCameraUsageDescription", titles)
        self.assertNotIn("NSPhotoLibraryUsageDescription", titles)  # present, though vague

    def test_vague_default(self):
        self.assertIn("privacy-strings/vague", self.r)

    def test_version_from_pubspec(self):
        proj, *_ = run(str(TMP / "flutter-broken"))
        self.assertEqual(proj.targets[0].version, "2.0.0")

    def test_other(self):
        for rid in ("ai-consent/missing", "login-services/no-equivalent", "networking/ipv4-literal", "content/other-platform"):
            self.assertIn(rid, self.r)


class Suppression(unittest.TestCase):
    def test_preflightignore(self):
        d = TMP / "swift-broken-ignored"
        shutil.copytree(TMP / "swift-broken", d)
        (d / ".preflightignore").write_text("secrets\ncontent/other-platform Broken/*\n")
        r = rules("swift-broken-ignored")
        self.assertNotIn("secrets/stripe-secret", r)
        self.assertNotIn("content/other-platform", r)
        self.assertIn("code/uiwebview", r)

    def test_inline(self):
        d = TMP / "swift-broken-inline"
        shutil.copytree(TMP / "swift-broken", d)
        p = d / "Broken/CameraView.swift"
        p.write_text(p.read_text().replace("let web = UIWebView()", "let web = UIWebView() // preflight:ignore code/uiwebview"))
        self.assertNotIn("code/uiwebview", rules("swift-broken-inline"))


class Bundle(unittest.TestCase):
    def test_app_bundle(self):
        app = TMP / "Built.app"
        app.mkdir(exist_ok=True)
        (app / "Built").write_bytes(b"\xcf\xfa\xed\xfe....AVCaptureDevice....NSUserDefaults....UIWebView")
        (app / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleExecutable": "Built", "CFBundleIdentifier": "com.example.built",
            "CFBundleShortVersionString": "1.0", "CFBundleVersion": "1", "UILaunchStoryboardName": "Launch"}))
        _, findings, _, _, errors = run(str(app))
        self.assertFalse(errors, errors)
        by = {f.rule: f for f in findings}
        self.assertEqual(by["privacy-strings/missing-key"].confidence, "validator-certain")
        self.assertEqual(by["privacy-manifest/missing"].severity, "BLOCKER")
        self.assertIn("code/uiwebview", by)


class Cli(unittest.TestCase):
    def _run(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, buf.getvalue()

    def test_ci_exit_codes(self):
        self.assertEqual(self._run(str(TMP / "swift-broken"), "--ci", "--json")[0], 1)
        self.assertEqual(self._run(str(TMP / "swift-clean"), "--ci", "--json")[0], 0)

    def test_json_shape(self):
        _, out = self._run(str(TMP / "swift-clean"), "--json")
        data = json.loads(out)
        self.assertEqual(data["verdict"], "READY")
        self.assertEqual({t["name"] for t in data["targets"]}, {"Clean", "CleanWidget"})

    def test_only(self):
        _, out = self._run(str(TMP / "swift-broken"), "--json", "--only", "secrets")
        self.assertEqual({f["check"] for f in json.loads(out)["findings"]}, {"secrets"})


class Html(unittest.TestCase):
    def test_html_and_from_json(self):
        out = TMP / "r.html"
        jpath = TMP / "r.json"
        buf = io.StringIO()
        with redirect_stdout(buf):
            main([str(TMP / "swift-broken"), "--json", "--html", str(out)])
        page = out.read_text()
        self.assertIn("NOT READY", page)
        self.assertIn("BrokenWidget", page)
        self.assertNotIn("<script src", page)  # self-contained
        data = json.loads(buf.getvalue())
        data["findings"] = [f for f in data["findings"] if f["severity"] != "BLOCKER"]
        data["findings"].append({"check": "semantic", "severity": "WARNING", "title": "Thin <wrapper>",
                                 "guideline": "4.2", "evidence": "`WKWebView` only", "fix": "Add native value"})
        data["review_notes"] = "Demo account: x"
        jpath.write_text(json.dumps(data))
        with redirect_stdout(io.StringIO()):
            main(["--from-json", str(jpath), "--html", str(out)])
        page = out.read_text()
        self.assertIn("LIKELY READY", page)
        self.assertIn("Thin &lt;wrapper&gt;", page)   # escaped
        self.assertIn("<code>WKWebView</code>", page)
        self.assertIn("Draft App Review notes", page)


if __name__ == "__main__":
    unittest.main()
