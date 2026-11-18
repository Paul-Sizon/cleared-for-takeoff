# assets: icon, launch screen, iPad
**Rules:** `no-icon`, `icon-missing-1024`, `icon-alpha`, `icon-size`, `no-launch-screen`, `ipad-orientations`, `ipad-review`

- **Icon:** the App Store (marketing) icon is 1024×1024 PNG with **no alpha** (ITMS-90717). Xcode 15+ single-size icons are fine. iOS 26 Icon Composer (`.icon`) files are fine too, but check that the asset is part of the target.
  - Remove alpha: `sips -s format jpeg icon.png --out /tmp/i.jpg && sips -s format png /tmp/i.jpg --out icon.png`, or Preview → Export → untick Alpha.
  - Expo: `expo.icon` is a 1024×1024 PNG. Expo flattens it, but transparent areas render black.
- **Launch screen:** `UILaunchStoryboardName` or a `UILaunchScreen` dictionary is required. Without it the app is letterboxed, or the upload is rejected.
- **iPad multitasking (ITMS-90474):** if iPad is supported and `UIRequiresFullScreen` is not YES, all 4 iPad orientations are required.
- **iPad review:** universal apps are tested on iPad (current review devices include a recent iPad Air). An iPhone-only app also runs on iPad in compatibility mode, so check that it doesn't crash there. Rejections cite 2.1 / 4.0 with iPad screenshots.
- **Flutter:** the default Info.plist declares iPad support. Remove `UISupportedInterfaceOrientations~ipad` and set `TARGETED_DEVICE_FAMILY = 1` if you don't want iPad.
