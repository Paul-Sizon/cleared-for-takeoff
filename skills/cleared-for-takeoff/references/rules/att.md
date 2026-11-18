# att: App Tracking Transparency
**Guidelines:** 5.1.2(i) · 2.1 · **Rules:** `missing`, `no-string`, `string-no-prompt`, `too-early`

## What counts as tracking
Linking user or device data from your app with other companies' data for targeted ads or ad measurement, or sharing it with data brokers. The IDFA requires ATT. First-party analytics alone (no IDFA, no cross-company linking) does **not**.

## Verify
- `missing`: read the SDK's init. AdMob with non-personalised ads only, or AppsFlyer/Adjust configured without IDFA collection, may not need ATT. Then the App Privacy answers must say "not used for tracking". Most ad SDKs in default config **do** need it.
- `string-no-prompt`: reviewers search for the prompt when the key exists. A common rejection is "We're unable to locate the App Tracking Transparency request". Either show it (on a fresh install, reachable without login) or remove the key.
- `too-early`: on iOS 15+, `requestTrackingAuthorization` called before the app is `.active` returns `.notDetermined` silently. Call it after the first screen appears.
- EU (iOS 27.2+): an alternative ATT prompt is available. In DE, FR, IT, PL and RO only the alternative prompt is shown. Test there if you target the EU.

## Fix
- **Swift:** `ATTrackingManager.requestTrackingAuthorization { … }` from `.task` / `applicationDidBecomeActive`, then start the SDK.
- **Expo:** `expo-tracking-transparency` with the plugin `userTrackingPermission` text, then `requestTrackingPermissionsAsync()`.
- **Flutter:** `app_tracking_transparency` → `AppTrackingTransparency.requestTrackingAuthorization()` after the first frame.
- Gate SDK init (or set the SDK's wait-for-ATT option, e.g. AppsFlyer `waitForATTUserAuthorization`).
- Don't incentivise or pre-pressure the prompt ("Allow to keep the app free!" screens that block the app are rejected).
