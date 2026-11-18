"""Privacy manifest (PrivacyInfo.xcprivacy) per target + required-reason API declarations.

Upload validation (ITMS-91053) rejects any bundle - including each app extension - that uses a
required-reason API without declaring it in its own privacy manifest.
"""
from __future__ import annotations

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, VALIDATOR_BLOCKING, VALIDATOR_CERTAIN, WARNING
from . import check, make

F = make("privacy-manifest")

RR_APIS = {
    "NSPrivacyAccessedAPICategoryUserDefaults": (
        r"\bUserDefaults\b|\bNSUserDefaults\b|@AppStorage\b",
        b"NSUserDefaults", "CA92.1 (app-only data)"),
    "NSPrivacyAccessedAPICategoryFileTimestamp": (
        r"\.creationDate\b|\.modificationDate\b|contentModificationDateKey|creationDateKey|NSFileCreationDate|"
        r"NSFileModificationDate|\bgetattrlist\b|\bfstat\(|\blstat\(|\bstat\(",
        b"NSFileModificationDate", "C617.1 (files inside app container)"),
    "NSPrivacyAccessedAPICategorySystemBootTime": (
        r"systemUptime\b|mach_absolute_time|\bkern\.boottime|clock_gettime\(\s*CLOCK_MONOTONIC",
        b"systemUptime", "35F9.1 (measure elapsed time)"),
    "NSPrivacyAccessedAPICategoryDiskSpace": (
        r"volumeAvailableCapacity|NSFileSystemFreeSize|NSFileSystemSize|\bstatfs\(|\bstatvfs\(|systemFreeSize",
        b"NSFileSystemFreeSize", "E174.1 (check space before writing)"),
    "NSPrivacyAccessedAPICategoryActiveKeyboards": (
        r"activeInputModes", b"activeInputModes", "54BD.1 (custom keyboard)"),
}


def _declared(manifest: dict) -> dict:
    out = {}
    for entry in manifest.get("NSPrivacyAccessedAPITypes", []) or []:
        if isinstance(entry, dict):
            out[entry.get("NSPrivacyAccessedAPIType", "")] = entry.get("NSPrivacyAccessedAPITypeReasons", []) or []
    return out


@check("privacy-manifest", "Privacy manifest per target", "Privacy", bundle=True)
def run(proj):
    out = []
    certain = proj.is_bundle
    conf = VALIDATOR_CERTAIN if certain else VALIDATOR_BLOCKING
    for t in proj.shipping_targets():
        # which RR categories does this target use?
        used = {}
        for cat, (rx, sym, _) in RR_APIS.items():
            if certain:
                if t.binary and sym in t.binary.read_bytes():
                    used[cat] = f"binary symbol {sym.decode()}"
            else:
                hits = proj.grep(rx, langs=("swift", "objc"), target=t, limit=1)
                if hits:
                    used[cat] = f"{hits[0].file}:{hits[0].line}"
        if "react-native" in proj.stacks and t.kind == "app" and not certain:
            # React Native core pods ship without manifests; the app manifest must declare their usage
            for cat in ("NSPrivacyAccessedAPICategoryUserDefaults", "NSPrivacyAccessedAPICategoryFileTimestamp",
                        "NSPrivacyAccessedAPICategorySystemBootTime"):
                used.setdefault(cat, "React Native core (template manifest declares this)")

        if not t.manifests:
            if proj.expo_managed:
                out.append(F("expo-missing", "No privacyManifests in Expo config", WARNING, REVIEW_RISK, "ITMS-91053",
                             "app.json has no expo.ios.privacyManifests. Expo modules ship their own manifests, but "
                             "your app-level required-reason API use (e.g. AsyncStorage → UserDefaults) must be declared.",
                             "Add expo.ios.privacyManifests.NSPrivacyAccessedAPITypes (UserDefaults CA92.1 etc.), "
                             "run `npx expo prebuild`, and verify ios/<App>/PrivacyInfo.xcprivacy.",
                             file="app.json", target=t.name))
                continue
            if used or t.kind == "app":
                sev = BLOCKER if used else WARNING
                ev = "; ".join(f"{k.replace('NSPrivacyAccessedAPICategory', '')} ({v})" for k, v in used.items())
                out.append(F("missing", f"{t.name}: no PrivacyInfo.xcprivacy", sev, conf if used else REVIEW_RISK,
                             "ITMS-91053 / 5.1.1",
                             (f"Target {t.name} ({t.kind}) uses required-reason APIs: {ev}." if used else
                              f"App target {t.name} has no privacy manifest.") +
                             (" Each extension needs its OWN manifest; the app's does not cover it." if t.kind != "app" else ""),
                             f"Add PrivacyInfo.xcprivacy to target {t.name} (File > New > App Privacy) and declare "
                             "each NSPrivacyAccessedAPIType with an approved reason code.",
                             file=t.info_path, target=t.name))
            continue

        merged = {}
        tracking = False
        domains = []
        for label, data in t.manifests:
            if data is None:
                out.append(F("invalid", f"{t.name}: unreadable privacy manifest", BLOCKER, conf, "ITMS-91053",
                             f"{label} is not a valid property list.", "Fix the XML/plist syntax.",
                             file=label, target=t.name))
                continue
            merged.update(_declared(data))
            tracking = tracking or bool(data.get("NSPrivacyTracking"))
            domains += data.get("NSPrivacyTrackingDomains", []) or []
        label = t.manifests[0][0]
        for cat, where in used.items():
            reasons = merged.get(cat)
            if reasons is None:
                hint = RR_APIS[cat][2]
                out.append(F("undeclared-api", f"{t.name}: {cat.replace('NSPrivacyAccessedAPICategory', '')} not declared",
                             BLOCKER, conf, "ITMS-91053",
                             f"Used at {where}, but {label} has no {cat} entry.",
                             f"Add {cat} to NSPrivacyAccessedAPITypes with a reason, typically {hint}.",
                             file=label, target=t.name))
            elif not reasons:
                out.append(F("empty-reasons", f"{t.name}: {cat} has no reason codes", BLOCKER, conf, "ITMS-91053",
                             f"{label} declares {cat} with an empty NSPrivacyAccessedAPITypeReasons.",
                             "Add at least one approved reason code.", file=label, target=t.name))
        if tracking and not domains:
            out.append(F("tracking-domains", f"{t.name}: NSPrivacyTracking=true but no tracking domains", WARNING,
                         REVIEW_RISK, "5.1.2",
                         f"{label} sets NSPrivacyTracking but lists no NSPrivacyTrackingDomains.",
                         "List the domains that receive tracking data (they are blocked until ATT is granted).",
                         file=label, target=t.name))
    return out
