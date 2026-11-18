"""Third-party SDKs: Apple's 'commonly used SDK' list must ship privacy manifests + signatures
(ITMS-91061 / ITMS-91065); GPL-family licenses are incompatible with App Store terms."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, VALIDATOR_BLOCKING, VALIDATOR_CERTAIN, WARNING
from . import check, make

F = make("dependencies")

# Apple's list of commonly used third-party SDKs (developer.apple.com/support/third-party-SDK-requirements)
LISTED_SDKS = {
    "Abseil", "AFNetworking", "Alamofire", "AppAuth", "BoringSSL", "BoringSSL-GRPC", "Capacitor", "Charts",
    "connectivity_plus", "Cordova", "device_info_plus", "DKImagePickerController", "DKPhotoGallery", "FBAEMKit",
    "FBLPromises", "FBSDKCoreKit", "FBSDKCoreKit_Basics", "FBSDKLoginKit", "FBSDKShareKit", "file_picker",
    "FirebaseABTesting", "FirebaseAuth", "FirebaseCore", "FirebaseCoreDiagnostics", "FirebaseCoreExtension",
    "FirebaseCoreInternal", "FirebaseCrashlytics", "FirebaseDynamicLinks", "FirebaseFirestore", "FirebaseInstallations",
    "FirebaseMessaging", "FirebaseRemoteConfig", "Flutter", "flutter_inappwebview", "flutter_local_notifications",
    "fluttertoast", "FMDB", "geolocator_apple", "GoogleDataTransport", "GoogleSignIn", "GoogleToolboxForMac",
    "GoogleUtilities", "grpcpp", "gRPC-C++", "gRPC-Core", "GTMAppAuth", "GTMSessionFetcher", "hermes", "hermes-engine",
    "image_picker_ios", "IQKeyboardManager", "IQKeyboardManagerSwift", "Kingfisher", "leveldb", "leveldb-library",
    "Lottie", "lottie-ios", "MBProgressHUD", "nanopb", "OneSignal", "OneSignalCore", "OneSignalExtension",
    "OneSignalOutcomes", "OpenSSL", "OpenSSL-Universal", "OrderedSet", "package_info", "package_info_plus",
    "path_provider", "path_provider_ios", "path_provider_foundation", "Promises", "PromisesObjC", "Protobuf",
    "Reachability", "RealmSwift", "Realm", "RxCocoa", "RxRelay", "RxSwift", "SDWebImage", "share_plus",
    "shared_preferences_ios", "shared_preferences_foundation", "SnapKit", "sqflite", "sqflite_darwin", "Starscream",
    "SVProgressHUD", "SwiftyGif", "SwiftyJSON", "Toast", "UnityFramework", "url_launcher", "url_launcher_ios",
    "video_player_avfoundation", "wakelock", "webview_flutter_wkwebview",
}
GPL = re.compile(r"\b(A?GPL|LGPL)(-[23]\.0)?(-only|-or-later)?\b|GNU (Affero )?(Lesser )?General Public License")


def _has_manifest(d: Path) -> bool:
    return d.exists() and any(True for _ in d.rglob("PrivacyInfo.xcprivacy"))


@check("dependencies", "Third-party SDK manifests & licenses", "Dependencies", bundle=True)
def run(proj):
    out = []
    root = proj.root
    if proj.is_bundle:
        for t in proj.shipping_targets():
            if not t.bundle_path:
                continue
            for fw in (t.bundle_path / "Frameworks").glob("*.framework"):
                if fw.stem in LISTED_SDKS and not (fw / "PrivacyInfo.xcprivacy").exists() and not _has_manifest(fw):
                    out.append(F("sdk-manifest", f"{fw.stem}.framework has no privacy manifest", BLOCKER, VALIDATOR_CERTAIN,
                                 "ITMS-91061", f"{fw.stem} is on Apple's commonly-used SDK list and ships without "
                                 "PrivacyInfo.xcprivacy.", f"Update {fw.stem} to a version that includes a privacy manifest.",
                                 target=t.name))
        return out

    unverified = []
    # CocoaPods (native, RN, Flutter)
    for podsdir in [root / "Pods", root / "ios" / "Pods"]:
        if not podsdir.exists():
            continue
        for pod in proj.deps["pods"]:
            base = pod.split("/")[0]
            if base not in LISTED_SDKS:
                continue
            d = podsdir / base
            if d.exists() and not _has_manifest(d):
                out.append(F("sdk-manifest", f"Pod {base} {proj.deps['pods'][pod]} has no privacy manifest", BLOCKER,
                             VALIDATOR_BLOCKING, "ITMS-91061",
                             f"{base} is on Apple's commonly-used SDK list; {proj.rel(d)} contains no PrivacyInfo.xcprivacy.",
                             f"`pod update {base}` to a release that ships a manifest (and signature).",
                             file=proj.rel(d)))
    if proj.deps["pods"] and not any((p).exists() for p in [root / "Pods", root / "ios" / "Pods"]):
        unverified += [p.split("/")[0] for p in proj.deps["pods"] if p.split("/")[0] in LISTED_SDKS]
    # Flutter plugins (paths from .flutter-plugins-dependencies)
    for plugin in proj.flutter_plugins:
        name = plugin.get("name", "")
        path = Path(plugin.get("path", ""))
        cands = [name, f"{name}_ios", f"{name}_foundation", f"{name}_darwin", f"{name}_apple"]
        if not any(c in LISTED_SDKS for c in cands):
            continue
        if plugin.get("native_build") is False or not ((path / "ios").exists() or (path / "darwin").exists()):
            continue  # pure-Dart / FFI plugin: no native framework is built
        if path.exists() and not (_has_manifest(path / "ios") or _has_manifest(path / "darwin")):
            out.append(F("sdk-manifest", f"Flutter plugin {name} has no privacy manifest", BLOCKER, VALIDATOR_BLOCKING,
                         "ITMS-91061", f"{path} has no PrivacyInfo.xcprivacy under ios/ or darwin/.",
                         f"`flutter pub upgrade {name}` to a version with a privacy manifest."))
    if proj.deps["pub"] and not proj.flutter_plugins:
        listed = [p for p in proj.deps["pub"] if p in LISTED_SDKS]
        if listed:
            unverified += listed
    # SwiftPM checkouts
    for checkouts in list(root.glob("**/SourcePackages/checkouts")) + [root / ".build" / "checkouts"]:
        if not checkouts.exists():
            continue
        for d in checkouts.iterdir():
            hit = next((s for s in LISTED_SDKS if s.lower() == d.name.lower() or s.lower() + "-ios" == d.name.lower()), None)
            if hit and not _has_manifest(d):
                out.append(F("sdk-manifest", f"SwiftPM package {d.name} has no privacy manifest", BLOCKER,
                             VALIDATOR_BLOCKING, "ITMS-91061", f"{proj.rel(d)} has no PrivacyInfo.xcprivacy.",
                             f"Update {d.name} in Package.resolved."))
    if unverified:
        out.append(F("unverified", "Could not verify privacy manifests of listed SDKs", INFO, JUDGMENT, "ITMS-91061",
                     f"Dependencies on Apple's list ({', '.join(sorted(set(unverified))[:8])}) are present, but their "
                     "sources aren't installed locally (run `pod install` / `flutter pub get`).",
                     "Re-run after installing dependencies, or scan the built .ipa/.xcarchive."))
    # GPL licenses (node_modules + Pods)
    gpl = []
    for name in list(proj.deps["npm"])[:400]:
        pj = root / "node_modules" / name / "package.json"
        if pj.exists():
            try:
                lic = json.loads(pj.read_text()).get("license", "")
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(lic, str) and GPL.search(lic) and "LGPL" not in lic:
                gpl.append(f"{name} ({lic})")
    for podsdir in [root / "Pods", root / "ios" / "Pods"]:
        for pod in set(p.split("/")[0] for p in proj.deps["pods"]):
            lic = podsdir / pod / "LICENSE"
            if lic.exists():
                head = lic.read_text(errors="ignore")[:800]
                if GPL.search(head) and "Lesser" not in head:
                    gpl.append(f"{pod} (GPL)")
    if gpl:
        out.append(F("gpl", "GPL-licensed dependencies", WARNING, JUDGMENT, "5.2.1",
                     f"{', '.join(gpl[:6])}. GPL terms conflict with App Store distribution terms; such apps get removed "
                     "on complaint.", "Replace with permissively licensed alternatives or obtain a commercial license."))
    return out
