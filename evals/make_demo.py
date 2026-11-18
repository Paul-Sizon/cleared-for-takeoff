#!/usr/bin/env python3
"""Builds the README demo: scan a fixture, enrich it the way the skill does (drop a false positive,
add reviewer-judgment findings, summary, review notes), render HTML, and screenshot it.

    python3 evals/make_demo.py            # writes assets/demo-report.html (+ PNGs if a Chromium browser exists)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "cleared-for-takeoff" / "scripts"))
sys.path.insert(0, str(REPO / "evals" / "fixtures"))

import build_fixtures  # noqa: E402
from preflight import html as html_report  # noqa: E402
from preflight.cli import _recount, run, to_json  # noqa: E402

BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser",
]


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="preflight-demo-"))
    build_fixtures.build(tmp)
    proj, findings, sup, ran, errors = run(str(tmp / "swift-broken"))
    data = to_json(proj, findings, sup, ran, errors)
    text = json.dumps(data).replace("BrokenWidget", "ReceiptWidget").replace("Broken", "ReceiptPal") \
        .replace("com.example.broken", "com.acme.receiptpal").replace("com.other.widget", "com.acme.widget") \
        .replace("iPhone Cleaner", "iPhone Receipt Scanner").replace(str(tmp / "swift-broken"), "~/code/ReceiptPal")
    data = json.loads(text)
    data["app_name"] = "ReceiptPal"
    data["generated"] = "2026-11-18"
    # the skill verifies leads: drop INFO noise for the demo, add reviewer findings
    data["findings"] = [f for f in data["findings"] if f["rule"] not in ("entitlements/aps-dev",)]
    data["findings"] += [
        {"check": "semantic", "rule": "semantic/2.3.1-accuracy", "area": "Reviewer judgment", "severity": "WARNING",
         "confidence": "judgment-call", "guideline": "2.3.1",
         "title": "Description promises bank sync that this build doesn't have",
         "evidence": "App Store description: \"Sync receipts with your bank automatically\". No bank or Plaid integration found in code.",
         "fix": "Remove the claim from the description, or ship the feature in this build and describe it in the review notes.",
         "file": "fastlane/metadata/en-US/description.txt", "line": 3},
        {"check": "semantic", "rule": "semantic/2.1-demo-account", "area": "Reviewer judgment", "severity": "BLOCKER",
         "confidence": "review-risk", "guideline": "2.1",
         "title": "Login wall with no demo account in review notes",
         "evidence": "Every screen after onboarding requires sign-in; App Review Information has no demo credentials.",
         "fix": "Add a demo account (no 2FA) with sample receipts to App Store Connect → App Review Information."},
    ]
    data["summary_text"] = ("ReceiptPal scans paper receipts, uses accounts and a monthly subscription, and sends receipt "
                            "text to OpenAI for categorisation. Highest risk: upload will fail (widget privacy manifest, "
                            "icon alpha, version string), followed by privacy (camera string, AI consent) and the missing "
                            "demo account.")
    data["review_notes"] = ("WHAT THE APP DOES\nScan paper receipts and track expenses.\n\nHOW TO TEST\n"
                            "Demo account: review@receiptpal.app / ••••••••  (no 2FA, 20 sample receipts)\n"
                            "1. Tap + → Scan to capture a receipt (camera).\n"
                            "2. Settings → ReceiptPal Pro shows the subscription; Restore Purchases is below it.\n"
                            "3. Settings → Account → Delete Account.\n\nAI\nReceipt text is sent to OpenAI after the "
                            "consent screen shown on first scan.")
    data["external_checklist"] = ["Archive with the Release configuration on the current SDK",
                                  "Test the full flow on an iPad and on an IPv6-only (NAT64) network",
                                  "Attach the Pro subscription to this version in App Store Connect",
                                  "Answer the new age-rating questions (Shared Location, social media)"]
    data["verification_note"] = ("Guidelines checked against developer.apple.com on 2026-11-18; Apple news scanned through "
                                 "2026-11-17. Scanner: 30 leads, 1 dropped after reading code.")
    _recount(data)
    out = REPO / "assets" / "demo-report.html"
    out.parent.mkdir(exist_ok=True)
    html_report.write(data, str(out))
    print("wrote", out)
    browser = next((b for b in BROWSERS if Path(b).exists() or shutil.which(b)), None)
    if not browser:
        print("no Chromium-based browser found; skipping screenshots")
        return
    for theme in ("light", "dark"):
        png = REPO / "assets" / f"report-{theme}.png"
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,1800",
                        "--force-device-scale-factor=2", f"--screenshot={png}", f"{out.as_uri()}?theme={theme}"],
                       check=True, capture_output=True)
        print("wrote", png)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
