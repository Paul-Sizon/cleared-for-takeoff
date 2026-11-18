"""Permission purpose strings (Info.plist NS*UsageDescription) vs APIs/SDKs actually linked.

Apple's upload validation (ITMS-90683) rejects binaries that reference a protected API without
the matching purpose string; App Review rejects vague strings under 5.1.1(ii).
"""
from __future__ import annotations

import re
from pathlib import Path

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, VALIDATOR_BLOCKING, VALIDATOR_CERTAIN, WARNING
from ..project import binary_contains
from . import check, make

F = make("privacy-strings")

CAM = "NSCameraUsageDescription"
MIC = "NSMicrophoneUsageDescription"
PHOTOS = "NSPhotoLibraryUsageDescription"
PHOTOS_ADD = "NSPhotoLibraryAddUsageDescription"
LOC = "NSLocationWhenInUseUsageDescription"
LOC_ALWAYS = "NSLocationAlwaysAndWhenInUseUsageDescription"
CONTACTS = "NSContactsUsageDescription"
CAL = ("NSCalendarsFullAccessUsageDescription", "NSCalendarsWriteOnlyAccessUsageDescription", "NSCalendarsUsageDescription")
REM = ("NSRemindersFullAccessUsageDescription", "NSRemindersUsageDescription")
HEALTH = "NSHealthShareUsageDescription"
HEALTH_UPD = "NSHealthUpdateUsageDescription"
BT = "NSBluetoothAlwaysUsageDescription"
MOTION = "NSMotionUsageDescription"
SPEECH = "NSSpeechRecognitionUsageDescription"
FACEID = "NSFaceIDUsageDescription"
NFC = "NFCReaderUsageDescription"
ATT = "NSUserTrackingUsageDescription"
MUSIC = "NSAppleMusicUsageDescription"
HOME = "NSHomeKitUsageDescription"
LOCALNET = "NSLocalNetworkUsageDescription"

# (regex over Swift/ObjC, required keys (any-of tuple or single), human label)
NATIVE_APIS = [
    (r"\bAVCaptureDevice\b|\bAVCaptureSession\b|sourceType\s*=\s*\.camera|UIImagePickerControllerSourceTypeCamera|\bDataScannerViewController\b", CAM, "camera capture"),
    (r"\bAVAudioRecorder\b|requestRecordPermission|\bSFSpeechAudioBufferRecognitionRequest\b|\.record\b.*AVAudioSession|setCategory\(\s*\.(playAndRecord|record)", MIC, "microphone recording"),
    (r"\bPHPhotoLibrary\b(?!.*\.shared\(\)\.performChanges)|\bPHAsset\.fetch|\bPHAssetCollection\b|sourceType\s*=\s*\.photoLibrary", PHOTOS, "photo library read"),
    (r"UIImageWriteToSavedPhotosAlbum|PHAssetChangeRequest|PHAssetCreationRequest", (PHOTOS_ADD, PHOTOS), "saving to photo library"),
    (r"\bCLLocationManager\b|\bCLLocationUpdate\b|\bCLMonitor\b", LOC, "location"),
    (r"requestAlwaysAuthorization", LOC_ALWAYS, "always-on location"),
    (r"\bCNContactStore\b|\bCNContactPickerViewController\b(?=.*requestAccess)", CONTACTS, "contacts"),
    (r"\bEKEventStore\b(?!.*\.reminder)|requestFullAccessToEvents|requestWriteOnlyAccessToEvents", CAL, "calendars"),
    (r"requestFullAccessToReminders|requestAccess\(to:\s*\.reminder", REM, "reminders"),
    (r"\bHKHealthStore\b", HEALTH, "HealthKit read"),
    (r"healthStore\.save|HKHealthStore\(\)\.save|\.save\(\s*\[?HK", HEALTH_UPD, "HealthKit write"),
    (r"\bCBCentralManager\b|\bCBPeripheralManager\b", BT, "Bluetooth"),
    (r"\bCMMotionActivityManager\b|\bCMPedometer\b|\bCMAltimeter\b|\bCMFallDetectionManager\b", MOTION, "motion & fitness"),
    (r"\bSFSpeechRecognizer\b", SPEECH, "speech recognition"),
    (r"\bLAContext\b|\.deviceOwnerAuthenticationWithBiometrics", FACEID, "Face ID"),
    (r"\bNFCNDEFReaderSession\b|\bNFCTagReaderSession\b|\bNFCVASReaderSession\b", NFC, "NFC"),
    (r"\bATTrackingManager\b.*requestTrackingAuthorization|requestTrackingAuthorization", ATT, "App Tracking Transparency"),
    (r"\bMPMediaLibrary\b|\bMPMediaQuery\b|\bMusicAuthorization\b", MUSIC, "media library"),
    (r"\bHMHomeManager\b", HOME, "HomeKit"),
    (r"\bNWBrowser\b|\bNetServiceBrowser\b|\bNSNetServiceBrowser\b|\bMCNearbyServiceBrowser\b|\bMCNearbyServiceAdvertiser\b", LOCALNET, "local network"),
]

# npm package -> [(keys, label, expo config-plugin option that sets the text)]
NPM = {
    "expo-camera": [(CAM, "camera", "cameraPermission"), (MIC, "microphone", "microphonePermission")],
    "react-native-vision-camera": [(CAM, "camera", "cameraPermissionText"), (MIC, "microphone", "microphonePermissionText")],
    "expo-image-picker": [(PHOTOS, "photo library", "photosPermission"), (CAM, "camera", "cameraPermission")],
    "react-native-image-picker": [(PHOTOS, "photo library", None), (CAM, "camera", None)],
    "react-native-image-crop-picker": [(PHOTOS, "photo library", None), (CAM, "camera", None)],
    "expo-media-library": [(PHOTOS, "photo library", "photosPermission"), (PHOTOS_ADD, "saving photos", "savePhotosPermission")],
    "@react-native-camera-roll/camera-roll": [(PHOTOS, "photo library", None)],
    "expo-location": [(LOC, "location", "locationWhenInUsePermission")],
    "react-native-geolocation-service": [(LOC, "location", None)],
    "@react-native-community/geolocation": [(LOC, "location", None)],
    "expo-contacts": [(CONTACTS, "contacts", "contactsPermission")],
    "react-native-contacts": [(CONTACTS, "contacts", None)],
    "expo-calendar": [(CAL, "calendars", "calendarPermission")],
    "expo-local-authentication": [(FACEID, "Face ID", "faceIDPermission")],
    "react-native-biometrics": [(FACEID, "Face ID", None)],
    "expo-tracking-transparency": [(ATT, "tracking", "userTrackingPermission")],
    "react-native-tracking-transparency": [(ATT, "tracking", None)],
    "react-native-ble-plx": [(BT, "Bluetooth", "bluetoothAlwaysPermission")],
    "react-native-ble-manager": [(BT, "Bluetooth", None)],
    "@react-native-voice/voice": [(SPEECH, "speech", "speechRecognitionPermission"), (MIC, "microphone", "microphonePermission")],
    "expo-speech-recognition": [(SPEECH, "speech", "speechRecognitionPermission"), (MIC, "microphone", "microphonePermission")],
    "react-native-health": [(HEALTH, "HealthKit", None)],
    "@kingstinct/react-native-healthkit": [(HEALTH, "HealthKit", "NSHealthShareUsageDescription")],
    "react-native-nfc-manager": [(NFC, "NFC", "nfcPermission")],
    "expo-audio": [(MIC, "microphone", "microphonePermission")],
    "react-native-audio-recorder-player": [(MIC, "microphone", None)],
}

PUB = {
    "image_picker": [(PHOTOS, "photo library"), (CAM, "camera"), (MIC, "microphone (video capture)")],
    "camera": [(CAM, "camera"), (MIC, "microphone")],
    "mobile_scanner": [(CAM, "camera")],
    "qr_code_scanner": [(CAM, "camera")],
    "geolocator": [(LOC, "location")],
    "location": [(LOC, "location")],
    "flutter_contacts": [(CONTACTS, "contacts")],
    "contacts_service": [(CONTACTS, "contacts")],
    "device_calendar": [(CAL, "calendars")],
    "record": [(MIC, "microphone")],
    "flutter_sound": [(MIC, "microphone")],
    "speech_to_text": [(SPEECH, "speech"), (MIC, "microphone")],
    "local_auth": [(FACEID, "Face ID")],
    "app_tracking_transparency": [(ATT, "tracking")],
    "flutter_blue_plus": [(BT, "Bluetooth")],
    "flutter_reactive_ble": [(BT, "Bluetooth")],
    "health": [(HEALTH, "HealthKit")],
    "photo_manager": [(PHOTOS, "photo library")],
    "gal": [(PHOTOS_ADD, "saving photos")],
    "image_gallery_saver": [(PHOTOS_ADD, "saving photos")],
    "nfc_manager": [(NFC, "NFC")],
    "pedometer": [(MOTION, "motion")],
}

BINARY_SYMBOLS = {
    CAM: [b"AVCaptureDevice"], MIC: [b"AVAudioRecorder"], PHOTOS: [b"PHPhotoLibrary"],
    LOC: [b"CLLocationManager"], CONTACTS: [b"CNContactStore"], CAL: [b"EKEventStore"],
    HEALTH: [b"HKHealthStore"], BT: [b"CBCentralManager", b"CBPeripheralManager"],
    MOTION: [b"CMMotionActivityManager", b"CMPedometer"], SPEECH: [b"SFSpeechRecognizer"],
    FACEID: [b"LAContext"], NFC: [b"NFCNDEFReaderSession", b"NFCTagReaderSession"],
    ATT: [b"ATTrackingManager"], MUSIC: [b"MPMediaLibrary"], HOME: [b"HMHomeManager"],
}

VAGUE_DEFAULT = re.compile(r"^(Allow|Let) (\$\(PRODUCT_NAME\)|\S+(\s\S+){0,3}) to (access|use) (your|the) [\w ]{1,30}\.?$", re.I)
PLACEHOLDER = re.compile(r"\b(TODO|TBD|lorem|placeholder|fixme|test)\b", re.I)
PURPOSE = re.compile(r"\b(to|so|for|when|while|lets?|helps?|used|enables?|allows? you|in order)\b", re.I)
ACCESS_PHRASE = re.compile(r"\b(access|permission|needs? access|requires? access)\s+to\b", re.I)


def _keys(k):
    return k if isinstance(k, tuple) else (k,)


def _has(info: dict, keys) -> bool:
    return any(str(info.get(k, "")).strip() for k in _keys(keys))


def _keyname(keys) -> str:
    ks = _keys(keys)
    return ks[0] if len(ks) == 1 else " or ".join(ks)


@check("privacy-strings", "Permission purpose strings", "Privacy", bundle=True)
def run(proj):
    out = []
    apps = proj.main_targets()
    if not apps:
        return out
    if proj.is_bundle:
        return _bundle(proj)
    for app in apps:
        info = app.info
        loc = app.info_path
        reported = set()
        # 1) native API usage in code attributed to this target (incl. RN/Flutter native dirs)
        for rx, keys, label in NATIVE_APIS:
            if _has(info, keys) or keys in reported:
                continue
            hits = proj.grep(rx, langs=("swift", "objc"), target=app, limit=1)
            if hits:
                reported.add(keys)
                h = hits[0]
                out.append(F("missing-key", f"Missing {_keyname(keys)} ({label})", BLOCKER, VALIDATOR_BLOCKING,
                             "5.1.1(ii) / ITMS-90683",
                             f"Code uses {label} (`{h.text[:90]}`) but target {app.name} Info.plist has no {_keyname(keys)}.",
                             f"Add {_keyname(keys)} to {loc or 'the target Info.plist'} with a specific, user-facing purpose, e.g. "
                             "\"Used to scan receipts so you can log expenses.\"",
                             file=h.file, line=h.line, target=app.name))
        # 2) SDK-linked APIs (RN / Expo / Flutter plugins)
        for pkg, reqs in NPM.items():
            if pkg not in proj.deps["npm"]:
                continue
            for req in reqs:
                keys, label, plugin_opt = req
                if _has(info, keys) or keys in reported:
                    continue
                reported.add(keys)
                if proj.expo_managed:
                    configured = plugin_opt and plugin_opt in (_raw_expo(proj))
                    if configured:
                        continue
                    out.append(F("expo-default-string", f"{pkg}: {label} purpose string not customised", WARNING, REVIEW_RISK,
                                 "5.1.1(ii)",
                                 f"{pkg} is installed but app.json sets neither ios.infoPlist.{_keyname(keys)} nor the "
                                 f"plugin option `{plugin_opt or _keyname(keys)}`. The config plugin injects a generic default "
                                 "(\"Allow $(PRODUCT_NAME) to access your …\"), which reviewers reject as too vague.",
                                 f"Set a specific purpose in app.json plugins: [[\"{pkg}\", {{\"{plugin_opt or 'permission'}\": "
                                 "\"<what the app does with it and why>\"}]] or ios.infoPlist.",
                                 file="app.json", target=app.name))
                else:
                    out.append(F("missing-key", f"Missing {_keyname(keys)} required by {pkg}", BLOCKER, VALIDATOR_BLOCKING,
                                 "5.1.1(ii) / ITMS-90683",
                                 f"{pkg} links the {label} API but {app.name} Info.plist has no {_keyname(keys)}.",
                                 f"Add {_keyname(keys)} with a specific purpose string to {loc or 'Info.plist'}.",
                                 file=loc, target=app.name))
        for pkg, reqs in PUB.items():
            if pkg not in proj.deps["pub"]:
                continue
            for keys, label in reqs:
                if _has(info, keys) or keys in reported:
                    continue
                reported.add(keys)
                out.append(F("missing-key", f"Missing {_keyname(keys)} required by {pkg}", BLOCKER, VALIDATOR_BLOCKING,
                             "5.1.1(ii) / ITMS-90683",
                             f"Flutter plugin `{pkg}` links the {label} API but {app.name} Info.plist has no {_keyname(keys)}.",
                             f"Add {_keyname(keys)} with a specific purpose string to {loc or 'ios/Runner/Info.plist'}.",
                             file=loc, target=app.name))
        if LOC_ALWAYS in reported or _has(info, LOC_ALWAYS):
            if not _has(info, LOC) and LOC not in reported:
                out.append(F("missing-key", "Always-location requires NSLocationWhenInUseUsageDescription too", BLOCKER,
                             VALIDATOR_BLOCKING, "5.1.1(ii)",
                             f"{LOC_ALWAYS} is declared without {LOC}; iOS requires both for Always authorization.",
                             f"Add {LOC}.", file=loc, target=app.name))
    # 3) string quality across all shipping targets
    for t in proj.shipping_targets():
        out += _quality(t)
    return out


def _raw_expo(proj) -> str:
    import json
    return json.dumps(proj.expo or {}) + proj.expo_raw


def _quality(t) -> list:
    out = []
    for key, val in t.info.items():
        if not (key.endswith("UsageDescription") or key == NFC):
            continue
        text = str(val or "").strip()
        problem = None
        if not text:
            problem = "is empty"
        elif VAGUE_DEFAULT.search(text):
            problem = "is the generic SDK default"
        elif PLACEHOLDER.search(text):
            problem = "contains placeholder wording"
        elif len(text) < 20:
            problem = f"is very short ({len(text)} chars)"
        elif not PURPOSE.search(ACCESS_PHRASE.sub("", text)):
            problem = "states a need for access but not what the app does with it"
        if problem:
            sev = BLOCKER if not text else WARNING
            out.append(F("vague", f"{key} {problem}", sev, REVIEW_RISK if text else VALIDATOR_BLOCKING, "5.1.1(ii)",
                         f"{t.name}: {key} = \"{text[:120]}\"",
                         "Rewrite as a specific purpose tied to a feature, e.g. \"Your location is used to show nearby "
                         "gyms on the map.\" Apple rejects strings like \"This app needs access to your camera.\"",
                         file=t.info_path, target=t.name))
    return out


def _bundle(proj) -> list:
    out = []
    for t in proj.shipping_targets():
        if not t.bundle_path:
            continue
        binaries = [t.binary] if t.binary else []
        for fw in (t.bundle_path / "Frameworks").glob("*.framework"):
            exe = fw / fw.stem
            if exe.exists():
                binaries.append(exe)
        for keys, symbols in BINARY_SYMBOLS.items():
            if _has(t.info, keys):
                continue
            for b in binaries:
                try:
                    data = b.read_bytes()
                except OSError:
                    continue
                hit = next((s for s in symbols if s in data), None)
                if hit:
                    out.append(F("missing-key", f"Missing {_keyname(keys)}", BLOCKER, VALIDATOR_CERTAIN,
                                 "5.1.1(ii) / ITMS-90683",
                                 f"{proj.rel(b)} references {hit.decode()} but {t.name} Info.plist has no {_keyname(keys)}.",
                                 f"Add {_keyname(keys)} with a specific purpose string.", file=t.info_path, target=t.name))
                    break
        out += _quality(t)
    return out
