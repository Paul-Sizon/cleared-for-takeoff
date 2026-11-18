# dependencies: third-party SDK manifests and licenses
**Guidelines:** ITMS-91061 / ITMS-91065 · 5.2.1 · **Rules:** `sdk-manifest`, `unverified`, `gpl`

- Apple keeps a list of commonly used SDKs (Firebase, Alamofire, SDWebImage, Kingfisher, GoogleSignIn, FBSDK, OneSignal, Lottie, RxSwift, many Flutter plugins, hermes…). New and updated apps must include a privacy manifest for each of them, plus a signature for binary SDKs. An old version without one blocks the upload.
- The scanner checks installed sources (`Pods/`, SwiftPM `checkouts/`, Flutter plugin paths from `.flutter-plugins-dependencies`). If they're not installed, it reports `unverified`. Run `pod install` / `flutter pub get`, or scan the `.xcarchive`.
- Pure-Dart / FFI Flutter plugins (`native_build: false`) build no framework and are skipped.

## Fix
- Update the SDK: `pod update <Pod>`, bump the version in `Package.swift` / Xcode packages, or `flutter pub upgrade <plugin>`.
- If the SDK is abandoned, replace it. Adding a manifest to a vendored copy works for source SDKs but not for binary SDKs, which also need a signature.

## GPL
GPL/AGPL terms conflict with App Store distribution terms. Such apps are removed if the copyright holder complains (e.g. the VLC precedent). LGPL is OK if dynamically linked with a relink possibility; that is complex on iOS, so prefer permissive licences.
