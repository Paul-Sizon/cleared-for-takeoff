# privacy-manifest: PrivacyInfo.xcprivacy per bundle
**Guidelines:** ITMS-91053 · 5.1.1 · 5.1.2 · **Rules:** `missing`, `undeclared-api`, `empty-reasons`, `invalid`, `tracking-domains`, `expo-missing`

## What Apple enforces
Each **bundle** (app, and *each* extension or watch app) that calls a required-reason API must declare that API in its own `PrivacyInfo.xcprivacy`, with an approved reason. Otherwise the upload is rejected with ITMS-91053 *Missing API declaration*. The app's manifest does **not** cover its extensions.

| Category | Typical APIs | Common reasons |
|---|---|---|
| UserDefaults | `UserDefaults`, `@AppStorage` | `CA92.1` app-only, `1C8F.1` App Group, `C56D.1` third-party SDK wrapper |
| FileTimestamp | `.creationDate`, `.modificationDate`, `stat()` | `C617.1` files in container, `DDA9.1` shown to user, `3B52.1` user-granted files |
| SystemBootTime | `systemUptime`, `mach_absolute_time` | `35F9.1` elapsed time |
| DiskSpace | `volumeAvailableCapacity…`, `statfs` | `E174.1` check before writing, `85F4.1` shown to user |
| ActiveKeyboards | `activeInputModes` | `54BD.1` custom keyboard, `3EC4.1` |

## Verify
- An extension sharing an App Group through `UserDefaults(suiteName:)` needs `1C8F.1` (or `CA92.1`) **in the extension's manifest**. This is the classic widget blocker.
- No manifest on an app that doesn't use these APIs is a WARNING, not a BLOCKER. You still need one for Data Collected declarations if SDKs collect data.
- RN: the RN template's manifest declares UserDefaults, FileTimestamp and SystemBootTime for the RN core. Keep them.
- Flutter: the Flutter engine ships its own manifest. Plugins are checked under `dependencies`.

## Fix
- **Xcode:** File → New → File → *App Privacy* → tick the target membership (one file per target).
- **Expo (SDK 50+):** `expo.ios.privacyManifests` in app.json:
  ```json
  "privacyManifests": {"NSPrivacyAccessedAPITypes": [
    {"NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults", "NSPrivacyAccessedAPITypeReasons": ["CA92.1"]}]}
  ```
  Expo merges these with module manifests during prebuild. Verify the result in `ios/<App>/PrivacyInfo.xcprivacy`.
- Also fill in `NSPrivacyCollectedDataTypes`, and `NSPrivacyTracking` + `NSPrivacyTrackingDomains` if you track.
- Verify against a real archive: `python3 scripts/preflight.py path/to/App.xcarchive`. Xcode → Archive → *Generate Privacy Report* shows the merged view.
