"""Entitlements and background modes vs actual code usage."""
from __future__ import annotations

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, WARNING
from . import check, make

F = make("entitlements")

SIWA_CODE = r"ASAuthorizationAppleIDProvider|SignInWithAppleButton|AppleAuthentication|appleAuth\b|SignInWithApple|sign_in_with_apple"
SIWA_DEPS = ("expo-apple-authentication", "@invertase/react-native-apple-authentication", "sign_in_with_apple",
             "react-native-apple-authentication")
PUSH_CODE = r"registerForRemoteNotifications|didRegisterForRemoteNotificationsWithDeviceToken|getDevicePushTokenAsync|getExpoPushTokenAsync|FirebaseMessaging|messaging\(\)\.getToken|FirebaseMessaging\.instance"
PUSH_DEPS = ("expo-notifications", "@react-native-firebase/messaging", "firebase_messaging", "onesignal_flutter",
             "react-native-onesignal", "OneSignalXCFramework", "FirebaseMessaging", "@notifee/react-native")
HEALTH_CODE = r"\bHKHealthStore\b"
HEALTH_DEPS = ("health", "react-native-health", "@kingstinct/react-native-healthkit")

BG_MODES = {
    "audio": (r"AVAudioSession|AVPlayer|AVAudioPlayer|AVAudioEngine|expo-av|expo-audio|just_audio|audioplayers|react-native-track-player|react-native-video",
              ("expo-av", "expo-audio", "just_audio", "audioplayers", "react-native-track-player", "audio_service", "react-native-video"),
              "audible background audio (music, podcasts, navigation prompts)"),
    "location": (r"allowsBackgroundLocationUpdates|startMonitoringSignificantLocationChanges|startTrackingLocationUpdates|startLocationUpdatesAsync|CLBackgroundActivitySession",
                 ("expo-location", "geolocator", "flutter_background_geolocation", "react-native-background-geolocation", "background_location"),
                 "continuous background location the user directly benefits from"),
    "voip": (r"\bPKPushRegistry\b|\bCXProvider\b", ("react-native-callkeep", "react-native-voip-push-notification", "flutter_callkit_incoming"),
             "real VoIP calling via PushKit + CallKit"),
    "bluetooth-central": (r"\bCBCentralManager\b", ("react-native-ble-plx", "flutter_blue_plus", "flutter_reactive_ble", "react-native-ble-manager"),
                          "communicating with BLE accessories in the background"),
    "fetch": (r"BGAppRefreshTask|setMinimumBackgroundFetchInterval|performFetchWithCompletionHandler|BackgroundFetch|registerTaskAsync",
              ("expo-background-fetch", "expo-background-task", "workmanager", "react-native-background-fetch", "background_fetch"),
              "periodic content refresh"),
    "processing": (r"BGProcessingTask", ("expo-background-task", "workmanager"), "deferrable maintenance work"),
    "remote-notification": (PUSH_CODE, PUSH_DEPS, "silent push to refresh content"),
}


def _uses(proj, code_rx, deps, target=None):
    if proj.has_dep(*deps):
        return f"dependency {proj.has_dep(*deps)[0]}"
    hits = proj.grep(code_rx, target=target, limit=1)
    return f"{hits[0].file}:{hits[0].line}" if hits else None


@check("entitlements", "Entitlements & background modes", "Configuration", bundle=True)
def run(proj):
    out = []
    for t in proj.shipping_targets():
        ent = t.entitlements or {}
        loc = t.entitlements_path or t.info_path
        is_app = t.kind == "app"
        if proj.is_bundle:
            # built product: only static consistency
            if ent.get("aps-environment") == "development":
                out.append(F("aps-dev", f"{t.name}: aps-environment=development in built product", BLOCKER, REVIEW_RISK,
                             "2.1", "The signed build carries the development push environment; push will fail in review.",
                             "Archive with a distribution profile (Release); Xcode sets aps-environment=production.",
                             file=loc, target=t.name))
        else:
            # Sign in with Apple
            siwa_used = _uses(proj, SIWA_CODE, SIWA_DEPS) if is_app else None
            has_siwa = "com.apple.developer.applesignin" in ent
            if siwa_used and not has_siwa and not proj.expo_managed:
                out.append(F("siwa-missing", f"{t.name}: Sign in with Apple used without entitlement", BLOCKER, REVIEW_RISK,
                             "2.1 (app completeness)",
                             f"Sign in with Apple is implemented ({siwa_used}) but {loc or 'the target'} lacks "
                             "com.apple.developer.applesignin; the button fails at runtime in review.",
                             "Add the Sign in with Apple capability to the target.", file=loc, target=t.name))
            elif has_siwa and is_app and not siwa_used:
                out.append(F("siwa-unused", f"{t.name}: Sign in with Apple entitlement but no implementation found",
                             INFO, JUDGMENT, "2.5.19 / unused entitlement",
                             "com.apple.developer.applesignin is present but no Sign in with Apple code was found.",
                             "Remove the capability if unused, or verify the implementation lives in a dependency.",
                             file=loc, target=t.name))
            # Push
            push_used = _uses(proj, PUSH_CODE, PUSH_DEPS) if is_app else None
            if push_used and "aps-environment" not in ent and not proj.expo_managed and is_app:
                out.append(F("push-missing", f"{t.name}: push used without aps-environment", WARNING, REVIEW_RISK,
                             "ITMS-90078 / 2.1",
                             f"Push registration found ({push_used}) but no aps-environment entitlement.",
                             "Enable the Push Notifications capability for the app target.",
                             file=loc, target=t.name))
            if ent.get("aps-environment") == "development":
                out.append(F("aps-dev", f"{t.name}: aps-environment=development", INFO, JUDGMENT, "—",
                             "Normal for source: Xcode rewrites it to production when exporting for App Store.",
                             "No action unless you sign manually; verify the archive uses a distribution profile.",
                             file=loc, target=t.name))
            # HealthKit
            hk_used = _uses(proj, HEALTH_CODE, HEALTH_DEPS) if is_app else None
            if hk_used and "com.apple.developer.healthkit" not in ent and not proj.expo_managed:
                out.append(F("healthkit-missing", f"{t.name}: HealthKit used without entitlement", BLOCKER, REVIEW_RISK,
                             "2.1 / 27.x", f"HealthKit usage ({hk_used}) without com.apple.developer.healthkit.",
                             "Add the HealthKit capability.", file=loc, target=t.name))
        # temporary exceptions / risky entitlements
        for k in ent:
            if "temporary-exception" in k:
                out.append(F("temp-exception", f"{t.name}: temporary-exception entitlement {k}", WARNING, REVIEW_RISK,
                             "2.4.5", f"{k} must be justified to App Review.",
                             "Remove it, or explain precisely why it is needed in the review notes.",
                             file=loc, target=t.name))
        # background modes
        modes = t.info.get("UIBackgroundModes") or []
        if isinstance(modes, str):
            modes = modes.split()
        for mode in modes:
            spec = BG_MODES.get(mode)
            if not spec:
                continue
            rx, deps, purpose = spec
            if proj.is_bundle:
                continue
            if not _uses(proj, rx, deps):
                out.append(F("bg-mode-unused", f"{t.name}: UIBackgroundModes '{mode}' without matching code",
                             WARNING, REVIEW_RISK, "2.5.4",
                             f"Info.plist declares background mode '{mode}' but no code using it was found.",
                             f"Remove '{mode}' unless the app does {purpose}; reviewers reject unjustified modes.",
                             file=t.info_path, target=t.name))
            elif mode in ("location", "audio", "voip"):
                out.append(F("bg-mode-justify", f"{t.name}: background mode '{mode}' needs a visible justification",
                             INFO, JUDGMENT, "2.5.4",
                             f"'{mode}' is declared and used. Reviewers check it is only for {purpose}.",
                             "Describe where the reviewer can see it in the review notes.",
                             file=t.info_path, target=t.name))
    return out
