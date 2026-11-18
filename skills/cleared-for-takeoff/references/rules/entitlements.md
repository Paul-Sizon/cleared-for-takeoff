# entitlements: capabilities and background modes
**Guidelines:** 2.1 · 2.4.5 · 2.5.4 · ITMS-90078 · **Rules:** `siwa-missing`, `siwa-unused`, `push-missing`, `aps-dev`, `healthkit-missing`, `temp-exception`, `bg-mode-unused`, `bg-mode-justify`

## What Apple enforces
- Features whose entitlement is missing fail at runtime: Sign in with Apple errors, push tokens never arrive, and HealthKit authorization fails. That is a 2.1 rejection.
- **2.5.4:** background modes are only for their intended purpose. Reviewers reject `audio` with no audible playback, `location` for analytics or geofencing that `significantLocationChanges` could handle, and `voip` without CallKit calls.
- Temporary-exception entitlements (mostly macOS) must be justified.

## Verify
- `aps-environment = development` in a source `.entitlements` file is **normal**. Xcode rewrites it to production during App Store export. It only matters in a built product.
- `bg-mode-unused` is a lead, not proof. Check for SDKs that do the work (e.g. a music player SDK for `audio`).
- Expo managed: config plugins add entitlements during prebuild (`expo-notifications` → push, `usesAppleSignIn` → SIWA). The scanner skips these checks for managed Expo.

## Fix
- Xcode → Target → *Signing & Capabilities* → add or remove the capability. Do this for the right target only.
- Background location: make the user benefit visible (navigation, workout tracking), show the blue indicator, and explain it in the review notes. Prefer `CLLocationUpdate.liveUpdates` / `significantLocationChanges`.
- `remote-notification` is only needed for silent push. Don't add it just to show notifications.
