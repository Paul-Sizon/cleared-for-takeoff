#!/usr/bin/env python3
"""Generates the fixture projects used by tests/ and evals/. Run from repo root:
    python3 evals/fixtures/build_fixtures.py
Fixtures are committed; re-run only when changing them."""
from __future__ import annotations

import json
import plistlib
import shutil
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).parent


def png(path: Path, size=1024, alpha=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    ctype, bpp = (6, 4) if alpha else (2, 3)
    raw = b"".join(b"\x00" + b"\x20\x80\xc0\xff"[:bpp] * size for _ in range(size))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, ctype, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    path.write_bytes(data)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"))


def plist(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(data))


def appicon(dir_: Path, alpha: bool):
    s = dir_ / "Assets.xcassets" / "AppIcon.appiconset"
    png(s / "icon-1024.png", alpha=alpha)
    write(s / "Contents.json", json.dumps({"images": [{"filename": "icon-1024.png", "idiom": "universal",
                                                         "platform": "ios", "size": "1024x1024"}],
                                            "info": {"author": "xcode", "version": 1}}, indent=2))


def pbxproj(path: Path, name: str, targets: list):
    """targets: [{name, type, infoplist, entitlements, bundle, version, build, family, dir}]"""
    objs, tids = [], []
    n = 0
    def oid():
        nonlocal n
        n += 1
        return f"A{n:023d}"
    main_group, proj_id, plist_id = oid(), oid(), oid()
    group_children = []
    for t in targets:
        tid, cl, rel = oid(), oid(), oid()
        g = oid()
        group_children.append(g)
        objs.append(f'{g} = {{isa = PBXFileSystemSynchronizedRootGroup; path = {t["dir"]}; sourceTree = "<group>"; }};')
        bs = {
            "INFOPLIST_FILE": t["infoplist"], "PRODUCT_BUNDLE_IDENTIFIER": t["bundle"],
            "MARKETING_VERSION": t.get("version", "1.0"), "CURRENT_PROJECT_VERSION": t.get("build", "1"),
            "TARGETED_DEVICE_FAMILY": t.get("family", "1"), "PRODUCT_NAME": "$(TARGET_NAME)",
        }
        if t.get("entitlements"):
            bs["CODE_SIGN_ENTITLEMENTS"] = t["entitlements"]
        body = " ".join(f'{k} = "{v}";' for k, v in bs.items())
        objs.append(f'{rel} = {{isa = XCBuildConfiguration; buildSettings = {{ {body} }}; name = Release; }};')
        objs.append(f'{cl} = {{isa = XCConfigurationList; buildConfigurations = ( {rel}, ); }};')
        objs.append(f'{tid} = {{isa = PBXNativeTarget; buildConfigurationList = {cl}; buildPhases = ( ); '
                    f'fileSystemSynchronizedGroups = ( {g}, ); name = {t["name"]}; productType = "{t["type"]}"; }};')
        tids.append(tid)
    pcl, prel = oid(), oid()
    objs.append(f'{prel} = {{isa = XCBuildConfiguration; buildSettings = {{ IPHONEOS_DEPLOYMENT_TARGET = 17.0; }}; name = Release; }};')
    objs.append(f'{pcl} = {{isa = XCConfigurationList; buildConfigurations = ( {prel}, ); }};')
    objs.append(f'{main_group} = {{isa = PBXGroup; children = ( {", ".join(group_children)}, ); sourceTree = "<group>"; }};')
    objs.append(f'{proj_id} = {{isa = PBXProject; buildConfigurationList = {pcl}; mainGroup = {main_group}; '
                f'projectDirPath = ""; targets = ( {", ".join(tids)}, ); }};')
    text = ("// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tobjectVersion = 77;\n\tobjects = {\n\t\t"
            + "\n\t\t".join(objs) + f"\n\t}};\n\trootObject = {proj_id} /* Project object */;\n}}\n")
    write(path, text)


GOOD_MANIFEST = {
    "NSPrivacyTracking": False, "NSPrivacyTrackingDomains": [], "NSPrivacyCollectedDataTypes": [],
    "NSPrivacyAccessedAPITypes": [{"NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults",
                                   "NSPrivacyAccessedAPITypeReasons": ["CA92.1"]}],
}


def swift_broken(root: Path):
    pbxproj(root / "Broken.xcodeproj" / "project.pbxproj", "Broken", [
        dict(name="Broken", type="com.apple.product-type.application", infoplist="Broken/Info.plist",
             entitlements="Broken/Broken.entitlements", bundle="com.example.broken", version="1.0 beta",
             family="1,2", dir="Broken"),
        dict(name="BrokenWidget", type="com.apple.product-type.app-extension", infoplist="BrokenWidget/Info.plist",
             bundle="com.other.widget", version="1.1", dir="BrokenWidget"),
    ])
    plist(root / "Broken/Info.plist", {
        "CFBundleDisplayName": "iPhone Cleaner",
        "CFBundleShortVersionString": "$(MARKETING_VERSION)", "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
        "NSLocationWhenInUseUsageDescription": "This app needs your location.",
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
        "UISupportedInterfaceOrientations~ipad": ["UIInterfaceOrientationPortrait", "UIInterfaceOrientationPortraitUpsideDown"],
        "UIBackgroundModes": ["audio", "location"],
    })
    plist(root / "Broken/Broken.entitlements", {"aps-environment": "development"})
    plist(root / "BrokenWidget/Info.plist", {"CFBundleShortVersionString": "$(MARKETING_VERSION)",
                                             "NSExtension": {"NSExtensionPointIdentifier": "com.apple.widgetkit-extension"}})
    appicon(root / "Broken", alpha=True)
    write(root / "Broken/CameraView.swift", """
import AVFoundation
import UIKit
import CoreLocation

final class CameraController {
    let session = AVCaptureSession()
    let location = CLLocationManager()
    func start() { AVCaptureDevice.requestAccess(for: .video) { _ in } }
}

final class LegacyWeb: UIView {
    let web = UIWebView()
}
""")
    write(root / "Broken/Auth.swift", """
import GoogleSignIn
import FirebaseAuth

struct AuthService {
    func google() { GIDSignIn.sharedInstance.signIn(withPresenting: UIViewController()) { _, _ in } }
    func signUp(email: String, pw: String) { Auth.auth().createUser(withEmail: email, password: pw) }
}
""")
    fake_key = "sk_" + "live_" + "51HxQ" + "abcdefghijklmnopqrstuvwxyz0123"  # split so secret scanners ignore this file
    write(root / "Broken/Store.swift", """
import StoreKit

final class Store {
    let stripeKey = "FAKE_KEY"
    let api = "http://192.168.1.10:8080/api"
    func load() { let r = SKProductsRequest(productIdentifiers: ["pro.monthly"]); r.start() }
    var label: String { "Pro subscription monthly: $9.99 / month" }
    var isReviewMode = false
}
""".replace("FAKE_KEY", fake_key))
    write(root / "Broken/Content.swift", """
import SwiftUI

struct HomeView: View {
    var body: some View {
        VStack {
            Text("Coming soon")
            Text("Also available on Android and Google Play")
            Button("Rate us 5 stars!") {}
        }
    }
}
""")
    write(root / "Broken/AI.swift", """
import Foundation

struct Assistant {
    let url = URL(string: "https://api.openai.com/v1/chat/completions")!
}
""")
    write(root / "BrokenWidget/Widget.swift", """
import WidgetKit
struct Provider {
    func read() -> Int { UserDefaults(suiteName: "group.x")?.integer(forKey: "n") ?? 0 }
}
""")
    write(root / "Broken/Debug.swift", """
#if DEBUG
let debugWeb = UIWebView()   // must NOT be reported (debug only)
#endif
""")


def swift_clean(root: Path):
    pbxproj(root / "Clean.xcodeproj" / "project.pbxproj", "Clean", [
        dict(name="Clean", type="com.apple.product-type.application", infoplist="Clean/Info.plist",
             entitlements="Clean/Clean.entitlements", bundle="com.example.clean", version="1.2.0", build="12",
             family="1", dir="Clean"),
        dict(name="CleanWidget", type="com.apple.product-type.app-extension", infoplist="CleanWidget/Info.plist",
             bundle="com.example.clean.widget", version="1.2.0", build="12", dir="CleanWidget"),
    ])
    plist(root / "Clean/Info.plist", {
        "CFBundleDisplayName": "Receipt Keeper",
        "CFBundleShortVersionString": "$(MARKETING_VERSION)", "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
        "NSCameraUsageDescription": "The camera is used to scan paper receipts so you can store them as expenses.",
        "ITSAppUsesNonExemptEncryption": False,
        "UILaunchScreen": {},
    })
    plist(root / "Clean/Clean.entitlements", {"com.apple.developer.applesignin": ["Default"]})
    plist(root / "Clean/PrivacyInfo.xcprivacy", GOOD_MANIFEST)
    plist(root / "CleanWidget/Info.plist", {"CFBundleShortVersionString": "$(MARKETING_VERSION)",
                                            "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)"})
    plist(root / "CleanWidget/PrivacyInfo.xcprivacy", GOOD_MANIFEST)
    appicon(root / "Clean", alpha=False)
    write(root / "Clean/Scanner.swift", """
import AVFoundation
import AuthenticationServices

final class Scanner {
    let session = AVCaptureSession()
    func settings() { UserDefaults.standard.set(true, forKey: "onboarded") }
    func signIn() { _ = ASAuthorizationAppleIDProvider().createRequest() }
}
""")
    write(root / "CleanWidget/Widget.swift", """
import WidgetKit
struct Provider { func read() -> Int { UserDefaults(suiteName: "group.x")?.integer(forKey: "n") ?? 0 } }
""")


def expo_broken(root: Path):
    write(root / "package.json", json.dumps({
        "name": "expo-broken", "dependencies": {
            "expo": "~53.0.0", "react-native": "0.79.0", "expo-camera": "~16.0.0", "expo-location": "~18.0.0",
            "react-native-google-mobile-ads": "^15.0.0", "react-native-purchases": "^8.0.0", "expo-updates": "~0.28.0",
            "@react-native-google-signin/google-signin": "^13.0.0"}}, indent=2))
    write(root / "app.json", json.dumps({"expo": {
        "name": "Snap Deals", "version": "1.0.0", "icon": "./assets/icon.png",
        "ios": {"bundleIdentifier": "com.example.snapdeals", "supportsTablet": True, "buildNumber": "3"},
        "plugins": ["expo-camera", "expo-location"]}}, indent=2))
    png(root / "assets/icon.png", size=512, alpha=True)
    write(root / "App.tsx", """
import { Text, Button, Platform } from 'react-native';
import Purchases from 'react-native-purchases';

export default function App() {
  const isAndroid = Platform.OS === 'android';
  const run = (code: string) => eval(code);
  Purchases.configure({ apiKey: 'appl_public' });
  return (<>
    <Text>Lorem ipsum dolor sit amet</Text>
    <Button title="Rate us 5 stars" onPress={() => {}} />
    <Text>Unlock Pro for $4.99/month subscription</Text>
  </>);
}
""")
    write(root / "src/signup.ts", """
export async function signUp(email: string, pw: string) {
  return fetch('https://api.example.com/v1/auth/register', { method: 'POST', body: JSON.stringify({ email, pw }) });
}
""")


def flutter_broken(root: Path):
    write(root / "pubspec.yaml", """
name: flutter_broken
version: 2.0.0+7
dependencies:
  flutter:
    sdk: flutter
  image_picker: ^1.1.0
  google_sign_in: ^6.2.0
  google_generative_ai: ^0.4.0
""")
    pbxproj(root / "ios/Runner.xcodeproj/project.pbxproj", "Runner", [
        dict(name="Runner", type="com.apple.product-type.application", infoplist="Runner/Info.plist",
             bundle="com.example.flutterbroken", version="$(FLUTTER_BUILD_NAME)", build="$(FLUTTER_BUILD_NUMBER)",
             family="1", dir="Runner"),
    ])
    plist(root / "ios/Runner/Info.plist", {
        "CFBundleShortVersionString": "$(FLUTTER_BUILD_NAME)", "CFBundleVersion": "$(FLUTTER_BUILD_NUMBER)",
        "UILaunchStoryboardName": "LaunchScreen",
        "NSPhotoLibraryUsageDescription": "Allow $(PRODUCT_NAME) to access your photos",
    })
    appicon(root / "ios/Runner", alpha=False)
    write(root / "ios/Runner/AppDelegate.swift", """
import Flutter
import UIKit
@main @objc class AppDelegate: FlutterAppDelegate {}
""")
    write(root / "lib/main.dart", """
import 'package:flutter/material.dart';
import 'package:google_generative_ai/google_generative_ai.dart';

void main() => runApp(const MaterialApp(home: Text('Download our app on Google Play too')));

final model = GenerativeModel(model: 'gemini-2.0-flash', apiKey: const String.fromEnvironment('KEY'));
final server = 'http://10.1.2.3/api';
""")


def build(dest: Path = HERE) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    for name, fn in FIXTURES:
        d = dest / name
        shutil.rmtree(d, ignore_errors=True)
        fn(d)
    return dest


FIXTURES = [("swift-broken", swift_broken), ("swift-clean", swift_clean),
            ("expo-broken", expo_broken), ("flutter-broken", flutter_broken)]


def main():
    import sys
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
    build(dest)
    print("fixtures built in", dest)


def _unused():
    for name, fn in [("swift-broken", swift_broken), ("swift-clean", swift_clean),
                     ("expo-broken", expo_broken), ("flutter-broken", flutter_broken)]:
        d = HERE / name
        shutil.rmtree(d, ignore_errors=True)
        fn(d)
        print("built", d)


if __name__ == "__main__":
    main()
