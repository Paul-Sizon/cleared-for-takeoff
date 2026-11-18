# build-config: versions, IDs, names, archive
**Rules:** `bad-version`, `bad-build`, `ext-version-mismatch`, `ext-bundle-id`, `trademark-name`, `trademark-bundle`, `zero-version`, `archive-config`

- `CFBundleShortVersionString`: one to three period-separated integers. No `-beta` or `rc1` (ITMS-90060). It must be higher than the last released version.
- `CFBundleVersion`: integers, unique per version. Flutter takes it from `pubspec.yaml` `version: x.y.z+BUILD`. Expo uses `ios.buildNumber` (or EAS `autoIncrement`).
- Extensions: the bundle ID must start with the app's ID plus `.` (ITMS-90355), and the version must match the app (ITMS-90473).
- **5.2.5:** Apple trademarks (iPhone, iPad, iOS, Siri, FaceTime, App Store…) can't be part of the app name or icon. "for iPhone" is allowed in the description only.
- **Archive scheme:** Edit Scheme → Archive → *Release*. Debug archives ship debug menus and endpoints, and run slower.
- A `0.x` version is legal, but combined with "beta" copy it reads as a demo (2.2).
