"""Build/config checks: ATS & networking, export compliance, icons & launch screen & iPad,
version numbers, bundle ids, archive configuration."""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, VALIDATOR_BLOCKING, VALIDATOR_CERTAIN, WARNING
from . import check, make

FATS = make("networking")
FEXP = make("export-compliance")
FAS = make("assets")
FB = make("build-config")

IPV4 = re.compile(r"(?:https?://|wss?://|^)((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?::\d+|/|$)")
IPV4_OK = ("127.0.0.1", "0.0.0.0", "255.255.255.255", "10.0.2.2", "1.1.1.1", "8.8.8.8")
HTTP_URL = re.compile(r"^http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|10\.0\.2\.2|www\.w3\.org|schemas\.|ns\.adobe|purl\.org|www\.apple\.com/DTDs|xml\.org)")


def _conf(proj):
    return VALIDATOR_CERTAIN if proj.is_bundle else VALIDATOR_BLOCKING


@check("networking", "ATS & IPv6 networking", "Configuration", bundle=True)
def networking(proj):
    out = []
    for t in proj.shipping_targets():
        ats = t.info.get("NSAppTransportSecurity") or {}
        if isinstance(ats, dict) and ats.get("NSAllowsArbitraryLoads") in (True, "YES", "true", 1):
            out.append(FATS("ats-disabled", f"{t.name}: NSAllowsArbitraryLoads = true", WARNING, REVIEW_RISK, "2.5 / ATS",
                            "App Transport Security is disabled globally; App Review asks for justification.",
                            "Remove it and add narrow NSExceptionDomains only for hosts you don't control that lack TLS. "
                            "Use NSAllowsArbitraryLoadsInWebContent for in-app browsers.",
                            file=t.info_path, target=t.name))
    if proj.is_bundle:
        return out
    hits = proj.grep_strings(IPV4)
    hits = [h for h in hits if not any(ok in h.text for ok in IPV4_OK)]
    for h in hits[:3]:
        out.append(FATS("ipv4-literal", "Hardcoded IPv4 address", WARNING, REVIEW_RISK, "2.5.5",
                        f"`{h.text[:100]}`. App Review runs on an IPv6-only (NAT64) network, where IPv4 literals fail.",
                        "Use a hostname (DNS gives NAT64 a chance to synthesize an address) and URLSession/Network.framework.",
                        file=h.file, line=h.line))
    http = proj.grep_strings(HTTP_URL)
    ats_on = all(not (t.info.get("NSAppTransportSecurity") or {}).get("NSAllowsArbitraryLoads") for t in proj.main_targets()
                 if isinstance(t.info.get("NSAppTransportSecurity") or {}, dict))
    if http and ats_on:
        h = http[0]
        out.append(FATS("cleartext-http", f"{len(http)} cleartext http:// URL(s) in code", WARNING, REVIEW_RISK, "2.1",
                        f"e.g. `{h.text[:100]}`. ATS blocks these at runtime, so the feature breaks during review.",
                        "Switch to https:// or add a scoped ATS exception.", file=h.file, line=h.line))
    return out


@check("export-compliance", "Export compliance declaration", "Configuration", bundle=True)
def export(proj):
    out = []
    for t in proj.main_targets():
        if "ITSAppUsesNonExemptEncryption" not in t.info:
            out.append(FEXP("missing", "ITSAppUsesNonExemptEncryption not set", INFO, JUDGMENT, "Export compliance",
                            "Without it, App Store Connect blocks each build in 'Missing Compliance' until you answer manually.",
                            "If you only use HTTPS/Apple crypto, set ITSAppUsesNonExemptEncryption = NO"
                            + (" (Expo: ios.config.usesNonExemptEncryption = false)." if proj.expo_managed else "."),
                            file=t.info_path, target=t.name))
    return out


# ---------------------------------------------------------------- assets
def _png_info(path: Path):
    try:
        with open(path, "rb") as fh:
            head = fh.read(33)
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h, depth, ctype = struct.unpack(">IIBB", head[16:26])
    return w, h, ctype in (4, 6)


@check("assets", "App icon, launch screen, iPad support", "UI & assets", bundle=True)
def assets(proj):
    out = []
    conf = _conf(proj)
    for t in proj.main_targets():
        info = t.info
        # launch screen
        if not (info.get("UILaunchStoryboardName") or "UILaunchScreen" in info or info.get("UILaunchImages")):
            out.append(FAS("no-launch-screen", f"{t.name}: no launch screen", BLOCKER, conf, "ITMS-90475 / 4.0",
                           "Info.plist has neither UILaunchStoryboardName nor UILaunchScreen.",
                           "Add a LaunchScreen storyboard or the UILaunchScreen dictionary (Xcode: 'Launch Screen' in target Info).",
                           file=t.info_path, target=t.name))
        # iPad
        fam = t.device_family
        if "2" in fam and not info.get("UIRequiresFullScreen"):
            ipad = info.get("UISupportedInterfaceOrientations~ipad") or info.get("UISupportedInterfaceOrientations") or []
            if isinstance(ipad, str):
                ipad = ipad.split()
            if ipad and len(set(ipad)) < 4:
                out.append(FAS("ipad-orientations", f"{t.name}: iPad multitasking needs all 4 orientations", BLOCKER, conf,
                               "ITMS-90474",
                               f"iPad is supported but only {len(set(ipad))} orientation(s) are declared and UIRequiresFullScreen is not set.",
                               "Support all four iPad orientations, or set UIRequiresFullScreen = YES.",
                               file=t.info_path, target=t.name))
        if "2" in fam:
            out.append(FAS("ipad-review", f"{t.name}: universal app, so App Review tests it on iPad", INFO, JUDGMENT, "2.4.1",
                           "Reviewers commonly test on a current iPad; layout bugs there are rejected under 2.1/4.0.",
                           "Run the full flow on an iPad simulator, including split view.", target=t.name))
        if proj.is_bundle:
            continue
        # icon
        out += _icon(proj, t)
    return out


def _icon(proj, t) -> list:
    out = []
    conf = _conf(proj)
    if proj.expo_managed:
        cfg = proj.expo or {}
        icon = (cfg.get("ios") or {}).get("icon") or cfg.get("icon")
        if not icon:
            return [FAS("no-icon", "No app icon configured", BLOCKER, conf, "ITMS-90022 / 2.3", "app.json has no icon.",
                        "Set expo.icon to a 1024×1024 opaque PNG.", file="app.json")]
        if isinstance(icon, str):
            p = (proj.root / icon)
            inf = _png_info(p)
            if inf:
                w, h, alpha = inf
                if (w, h) != (1024, 1024):
                    out.append(FAS("icon-size", f"App icon is {w}×{h}", BLOCKER, conf, "ITMS-90022",
                                   f"{icon} must be 1024×1024.", "Export a 1024×1024 PNG.", file=icon))
                if alpha:
                    out.append(FAS("icon-alpha", "App icon PNG has an alpha channel", WARNING, REVIEW_RISK, "ITMS-90717",
                                   f"{icon} has an alpha channel. Expo flattens it at build time, but transparent areas render black.",
                                   "Export without transparency.", file=icon))
        return out
    sets = [p for p in proj.root.rglob("*.appiconset") if not any(s in p.parts for s in ("Pods", "node_modules", "build", ".build"))]
    tdirs = [d for d in t.dirs if d != t.project_dir]
    mine = [s for s in sets if any(str(s).startswith(str(d)) for d in tdirs)] or sets
    if not mine:
        return [FAS("no-icon", f"{t.name}: no AppIcon asset found", BLOCKER, conf, "ITMS-90022 / ITMS-90713",
                    "No *.appiconset found.", "Add an AppIcon set with a 1024×1024 opaque PNG.", target=t.name)]
    for s in mine:
        try:
            contents = json.loads((s / "Contents.json").read_text())
        except (OSError, json.JSONDecodeError):
            continue
        marketing = [im for im in contents.get("images", [])
                     if im.get("size") in ("1024x1024",) and im.get("idiom") in ("ios-marketing", "universal")]
        if not marketing:
            continue
        files = [im.get("filename") for im in marketing]
        if not any(files):
            out.append(FAS("icon-missing-1024", f"{s.name}: 1024×1024 icon slot is empty", BLOCKER, conf, "ITMS-90713",
                           f"{proj.rel(s)}/Contents.json declares the 1024pt icon but no file is assigned.",
                           "Drop a 1024×1024 PNG into the App Store slot.", file=proj.rel(s / "Contents.json"), target=t.name))
            continue
        for fn in filter(None, files):
            inf = _png_info(s / fn)
            if inf and inf[2]:
                out.append(FAS("icon-alpha", f"{fn}: App Store icon has an alpha channel", BLOCKER, conf, "ITMS-90717",
                               f"{proj.rel(s / fn)} is PNG with alpha; upload is rejected for the marketing icon.",
                               "Re-export without alpha (Preview → Export → uncheck Alpha, or `sips -s format jpeg` then back to png).",
                               file=proj.rel(s / fn), target=t.name))
            if inf and (inf[0], inf[1]) != (1024, 1024):
                out.append(FAS("icon-size", f"{fn}: marketing icon is {inf[0]}×{inf[1]}", BLOCKER, conf, "ITMS-90022",
                               "The App Store icon must be 1024×1024.", "Export at 1024×1024.",
                               file=proj.rel(s / fn), target=t.name))
    return out


# ---------------------------------------------------------------- versions / ids
VERSION_RX = re.compile(r"^\d+(\.\d+){0,2}$")
BUILD_RX = re.compile(r"^\d+(\.\d+){0,2}$")
TRADEMARK = re.compile(r"(?i)\b(apple|iphone|ipad|ios|macos|facetime|imessage|siri|airpods|app store|testflight|watchos|visionos)\b")


@check("build-config", "Versions, bundle IDs, archive config", "Configuration", bundle=True)
def build_config(proj):
    out = []
    conf = _conf(proj)
    apps = proj.main_targets()
    for t in proj.shipping_targets():
        v, b = t.version, t.build
        if v and "$(" not in v and not VERSION_RX.match(v):
            out.append(FB("bad-version", f"{t.name}: CFBundleShortVersionString '{v}' is invalid", BLOCKER, conf, "ITMS-90060",
                          "Must be up to three period-separated integers (e.g. 1.2.0). No 'beta' or suffixes.",
                          "Use a numeric version; put pre-release info in the build number or TestFlight notes.",
                          file=t.info_path, target=t.name))
        if b and "$(" not in b and not BUILD_RX.match(b):
            out.append(FB("bad-build", f"{t.name}: CFBundleVersion '{b}' is invalid", BLOCKER, conf, "ITMS-90058",
                          "Build number must be period-separated integers.", "Use e.g. 42 or 1.2.0.42.",
                          file=t.info_path, target=t.name))
        if t.kind != "app" and apps:
            parent = apps[0]
            if parent.version and v and v != parent.version and "$(" not in v + parent.version:
                out.append(FB("ext-version-mismatch", f"{t.name}: version {v} ≠ app {parent.version}", WARNING, conf, "ITMS-90473",
                              "Extension CFBundleShortVersionString must match the containing app.",
                              "Set MARKETING_VERSION identically for all targets.", file=t.info_path, target=t.name))
            if parent.bundle_id and t.bundle_id and "$(" not in t.bundle_id and not t.bundle_id.startswith(parent.bundle_id + "."):
                out.append(FB("ext-bundle-id", f"{t.name}: bundle ID not prefixed by the app's", BLOCKER, conf, "ITMS-90355",
                              f"{t.bundle_id} must start with {parent.bundle_id}.",
                              f"Rename to {parent.bundle_id}.<extension>.", target=t.name, file=t.project_file))
    for t in apps:
        name = str(t.info.get("CFBundleDisplayName") or t.info.get("CFBundleName") or "")
        if "$(" in name:
            name = t.settings.get("PRODUCT_NAME", "")
        if name and TRADEMARK.search(name):
            out.append(FB("trademark-name", f"App name '{name}' uses an Apple trademark", WARNING, REVIEW_RISK, "5.2.5",
                          "Names like 'iPhone Cleaner' or 'Siri Tools' are rejected; Apple marks may only be used descriptively "
                          "('for iPhone') in the description, not in the name.", "Rename the app.", target=t.name,
                          file=t.info_path))
        if t.bundle_id and re.search(r"(?i)\b(com\.apple)\b", t.bundle_id):
            out.append(FB("trademark-bundle", "Bundle ID uses com.apple", BLOCKER, REVIEW_RISK, "5.2.5",
                          t.bundle_id, "Use your own reverse-DNS domain.", target=t.name))
        if v := t.version:
            if VERSION_RX.match(v) and v.startswith("0."):
                out.append(FB("zero-version", f"{t.name}: version {v} starts with 0.", INFO, JUDGMENT, "2.2",
                              "Allowed, but 2.2 rejects demos/betas/trials, so a 0.x version invites the reviewer to "
                              "treat it as a beta.", "Consider 1.0.0 for the first public release.", target=t.name))
    if not proj.is_bundle:
        out += _schemes(proj)
    return out


def _schemes(proj) -> list:
    out = []
    for scheme in proj.root.rglob("*.xcscheme"):
        if any(s in scheme.parts for s in ("Pods", "node_modules", ".build", "xcuserdata")):
            continue
        try:
            text = scheme.read_text(errors="ignore")
        except OSError:
            continue
        m = re.search(r"<ArchiveAction[^>]*buildConfiguration\s*=\s*\"([^\"]+)\"", text)
        if m and m.group(1) not in ("Release",) and "Release" not in m.group(1):
            out.append(FB("archive-config", f"Scheme {scheme.stem} archives with '{m.group(1)}'", WARNING, REVIEW_RISK, "2.1",
                          "Archiving a non-Release configuration ships debug code paths/settings to review.",
                          "Edit Scheme → Archive → Build Configuration = Release.", file=proj.rel(scheme)))
    return out
