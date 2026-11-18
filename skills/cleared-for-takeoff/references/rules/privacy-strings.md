# privacy-strings: permission purpose strings
**Guidelines:** 5.1.1(ii) · ITMS-90683 (upload) · **Rules:** `missing-key`, `vague`, `expo-default-string`

## What Apple enforces
- **Upload:** if the binary (your code, *or any linked SDK*) references a protected API, the matching `NS…UsageDescription` must exist, even if the code path is never reached. A missing key makes the app crash the moment the permission is requested.
- **Review:** the string must say *what the app does with the data and why*. Rejected: "This app needs camera access", "Allow MyApp to access your photos", empty strings, or text in the wrong language.

## Verify a finding
- `missing-key` from Swift/ObjC: open the line. Usage in a test target or under `#if DEBUG` is not shipped. Usage in a linked framework still counts.
- `missing-key` from an RN/Flutter package: the plugin's native code links the API whether or not you call it. **Keep it as a finding.** Exception: `permission_handler` (Flutter) uses compile-time macros and only links what you enable in the Podfile.
- `vague`: judge the string. "Your location is used to show gyms near you" passes.

## Fix by stack
- **Swift (Xcode 14+ generated Info.plist):** Target → Info → add the key, or add `INFOPLIST_KEY_NSCameraUsageDescription` to the build settings.
- **Expo:** set it in the plugin config, which wins over the defaults:
  ```json
  "plugins": [["expo-camera", {"cameraPermission": "Used to scan receipts so you can track expenses.", "microphonePermission": false}]]
  ```
  Or use `ios.infoPlist.NSCameraUsageDescription`. Passing `false` for an unneeded permission removes it.
- **Bare RN:** `ios/<App>/Info.plist`.
- **Flutter:** `ios/Runner/Info.plist`. For `image_picker`, also add `NSMicrophoneUsageDescription` (video capture) and `NSCameraUsageDescription`.
- **Localisation:** translate the strings in `InfoPlist.strings` / `InfoPlist.xcstrings` for each supported language.

## Example rejection
> Guideline 5.1.1(ii) - Legal - Privacy - Data Collection and Storage. The app's purpose string does not sufficiently explain the use of protected resources… update the location purpose string to explain how the app will use the requested information, and provide an example.
