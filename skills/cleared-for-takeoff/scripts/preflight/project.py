"""Project discovery: stack detection, Xcode target enumeration, source indexing, dependencies.

Supports native Xcode projects (Swift/ObjC), React Native (bare + Expo prebuild), Expo managed
(app.json / app.config.*), Flutter (ios/Runner), and built products (.app / .ipa / .xcarchive).
Standard library only.
"""
from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from . import openstep

SKIP_DIRS = {
    "node_modules", "Pods", ".git", "build", "Build", "DerivedData", ".build", ".dart_tool",
    "android", "Carthage", ".symlinks", ".expo", "dist", "vendor", ".next", "web-build",
    "coverage", "fastlane", ".swiftpm", "SourcePackages", "macos", "linux", "windows", "web",
    ".idea", ".vscode", "xcuserdata", ".gradle", "ephemeral", ".fvm",
}
LANG_BY_EXT = {
    ".swift": "swift", ".m": "objc", ".mm": "objc", ".h": "objc", ".c": "objc",
    ".dart": "dart",
    ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".cjs": "js",
}
CONFIG_EXT = {".plist", ".json", ".xcconfig", ".entitlements", ".strings", ".yaml", ".yml", ".env"}
CODE_LANGS = ("swift", "objc", "dart", "js")
MAX_FILE_BYTES = 1_500_000

_TEST_SEG = re.compile(
    r"(^|/)(Tests?|UITests|[A-Za-z0-9_]+Tests|[A-Za-z0-9_]+UITests|__tests__|__mocks__|test|tests|"
    r"integration_test|Preview Content|Previews|Mocks?|Fixtures?|e2e|Example|Examples|Sample|Samples|"
    r"storybook|\.storybook)(/|$)"
)
_TEST_FILE = re.compile(r"(\.test\.|\.spec\.|Tests?\.swift$|Mock[A-Za-z]*\.swift$|_test\.dart$|\.stories\.)")
_JSX_TEXT = re.compile(r">([^<>{}\n]*[A-Za-z][^<>{}\n]*)<")
_STR_LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`([^`\n]*)`')


@dataclass
class Hit:
    file: str
    line: int
    text: str


@dataclass
class SourceFile:
    path: Path
    rel: str
    lang: str
    lines: list
    is_test: bool
    masked: set  # 1-based line numbers inside debug-only code or comments

    def live_lines(self, include_debug: bool = False):
        for i, text in enumerate(self.lines, 1):
            if not include_debug and i in self.masked:
                continue
            yield i, text


@dataclass
class Target:
    name: str
    kind: str                      # app | extension | watch | test | other
    product_type: str = ""
    bundle_id: str = ""
    info: dict = field(default_factory=dict)
    info_path: Optional[str] = None
    entitlements: dict = field(default_factory=dict)
    entitlements_path: Optional[str] = None
    manifests: list = field(default_factory=list)   # list of (label/path, parsed dict or None)
    settings: dict = field(default_factory=dict)
    dirs: list = field(default_factory=list)         # absolute Paths owned by target
    source_rels: set = field(default_factory=set)    # rel paths of code attributed to target
    binary: Optional[Path] = None                    # bundle mode only
    bundle_path: Optional[Path] = None               # bundle mode only
    project_file: Optional[str] = None               # rel path to project.pbxproj
    project_dir: Optional[Path] = None               # dir containing the .xcodeproj

    @property
    def version(self) -> str:
        return str(self.info.get("CFBundleShortVersionString") or self.settings.get("MARKETING_VERSION") or "")

    @property
    def build(self) -> str:
        return str(self.info.get("CFBundleVersion") or self.settings.get("CURRENT_PROJECT_VERSION") or "")

    @property
    def device_family(self) -> set:
        fam = self.settings.get("TARGETED_DEVICE_FAMILY")
        if fam:
            return {x.strip() for x in str(fam).split(",") if x.strip()}
        uidf = self.info.get("UIDeviceFamily")
        if isinstance(uidf, list):
            return {str(x) for x in uidf}
        return {"1"}


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.stacks: set = set()
        self.targets: list = []
        self.files: list = []
        self.config_files: list = []
        self.deps: dict = {"npm": {}, "npm_dev": {}, "pub": {}, "pods": {}, "spm": {}}
        self.flutter_plugins: list = []      # [{name, path}]
        self.expo: Optional[dict] = None     # parsed expo config (app.json) if available
        self.expo_raw: str = ""              # raw app.config.* text if not JSON
        self.expo_managed = False
        self.is_bundle = False
        self.notes: list = []                # discovery notes surfaced in the report
        self._tmp: Optional[str] = None

    # ------------------------------------------------------------------ helpers
    def rel(self, p: Path) -> str:
        try:
            return str(Path(p).resolve().relative_to(self.root))
        except ValueError:
            return str(p)

    def main_targets(self) -> list:
        return [t for t in self.targets if t.kind == "app"]

    def shipping_targets(self) -> list:
        return [t for t in self.targets if t.kind in ("app", "extension", "watch")]

    def code_files(self, langs=CODE_LANGS, include_tests: bool = False, target: Optional[Target] = None):
        for f in self.files:
            if f.lang not in langs:
                continue
            if f.is_test and not include_tests:
                continue
            if target is not None and f.rel not in target.source_rels:
                continue
            yield f

    def grep(self, pattern, langs=CODE_LANGS, include_tests=False, include_debug=False,
             target: Optional[Target] = None, flags=0, limit: int = 0) -> list:
        rx = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
        hits = []
        for f in self.code_files(langs, include_tests, target):
            for i, text in f.live_lines(include_debug):
                if rx.search(text):
                    hits.append(Hit(f.rel, i, text.strip()[:240]))
                    if limit and len(hits) >= limit:
                        return hits
        return hits

    def grep_strings(self, pattern, langs=CODE_LANGS, include_tests=False, flags=0,
                     line_exclude: Optional[re.Pattern] = None) -> list:
        """Match only inside string literals (UI copy, URLs)."""
        rx = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
        hits = []
        for f in self.code_files(langs, include_tests):
            for i, text in f.live_lines():
                if line_exclude and line_exclude.search(text):
                    continue
                lits = [m.group(1) or m.group(2) or m.group(3) or "" for m in _STR_LIT.finditer(text)]
                if f.lang == "js":
                    lits += _JSX_TEXT.findall(text)
                if any(rx.search(lit) for lit in lits):
                    hits.append(Hit(f.rel, i, text.strip()[:240]))
        return hits

    def grep_config(self, pattern, flags=0) -> list:
        rx = re.compile(pattern, flags)
        hits = []
        for p in self.config_files:
            try:
                for i, text in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                    if rx.search(text):
                        hits.append(Hit(self.rel(p), i, text.strip()[:240]))
            except OSError:
                pass
        return hits

    def has_dep(self, *names: str) -> list:
        found = []
        for name in names:
            for eco in ("npm", "pub", "pods", "spm"):
                d = self.deps[eco]
                if name in d or (eco == "pods" and any(k.split("/")[0] == name for k in d)):
                    found.append(name)
                    break
        return found

    def cleanup(self) -> None:
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)


# ====================================================================== loading
def load(path: str) -> Project:
    p = Path(path).expanduser()
    if p.suffix in (".app", ".ipa", ".xcarchive"):
        return _load_bundle(p)
    proj = Project(p)
    _index_files(proj)
    _load_deps(proj)
    _load_expo(proj)
    for pbx in _find_pbxprojs(proj.root):
        try:
            _load_xcodeproj(proj, pbx)
        except Exception as e:  # noqa: BLE001 - report, don't crash the scan
            proj.notes.append(f"Could not parse {proj.rel(pbx)}: {e}")
    if proj.expo is not None and not proj.targets:
        proj.expo_managed = True
        _synth_expo_target(proj)
    _detect_stacks(proj)
    _attribute_sources(proj)
    if not proj.targets:
        proj.notes.append("No Xcode project or Expo config found; target-level checks skipped.")
    return proj


def _index_files(proj: Project) -> None:
    for dirpath, dirnames, filenames in os.walk(proj.root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith((".xcassets", ".xcframework", ".framework", ".bundle"))]
        for fn in filenames:
            path = Path(dirpath) / fn
            ext = path.suffix
            if ext in CONFIG_EXT or fn in ("Podfile", "Podfile.lock", "Package.resolved", "pubspec.yaml", "pubspec.lock") or fn.startswith(".env"):
                if fn not in ("package-lock.json", "yarn.lock") and not fn.endswith(".lock.json"):
                    proj.config_files.append(path)
            lang = LANG_BY_EXT.get(ext)
            if not lang:
                continue
            if fn.endswith((".min.js", ".d.ts", ".g.dart", ".freezed.dart")):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            rel = proj.rel(path)
            lines = text.splitlines()
            is_test = bool(_TEST_SEG.search(rel) or _TEST_FILE.search(fn))
            proj.files.append(SourceFile(path, rel, lang, lines, is_test, _mask(lines, lang)))


_IF_RX = re.compile(r"^\s*#\s*if(def)?\b(.*)$")
_ELSE_RX = re.compile(r"^\s*#\s*(else|elif|elseif)\b")
_ENDIF_RX = re.compile(r"^\s*#\s*endif\b")
_DEBUG_COND = re.compile(r"\b(DEBUG|targetEnvironment\s*\(\s*simulator\s*\)|TESTING|PREVIEW)\b")


def _mask(lines: list, lang: str) -> set:
    """Lines in debug-only conditional compilation blocks and comments."""
    masked = set()
    stack = []  # each entry: [is_debug_cond, negated, in_else]
    in_block_comment = False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        # comments
        if in_block_comment:
            masked.add(i)
            if "*/" in s:
                in_block_comment = False
            continue
        if s.startswith("/*"):
            masked.add(i)
            if "*/" not in s[2:]:
                in_block_comment = True
            continue
        if s.startswith("//") or (s.startswith("*") and lang != "dart") or (s.startswith("#") and lang == "js"):
            masked.add(i)
            continue
        if lang in ("swift", "objc"):
            m = _IF_RX.match(line)
            if m:
                cond = m.group(2)
                stack.append([bool(_DEBUG_COND.search(cond)), "!" in cond, False])
                masked.add(i)
                continue
            if _ELSE_RX.match(line) and stack:
                stack[-1][2] = True
                masked.add(i)
                continue
            if _ENDIF_RX.match(line) and stack:
                stack.pop()
                masked.add(i)
                continue
            for is_dbg, neg, in_else in stack:
                if is_dbg and (neg == in_else):  # `#if DEBUG` body, or `#if !DEBUG` else-branch
                    masked.add(i)
                    break
        elif lang == "js" and "__DEV__" in line:
            masked.add(i)
        elif lang == "dart" and ("kDebugMode" in line or "assert(" in s[:8]):
            masked.add(i)
    return masked


def _find_pbxprojs(root: Path) -> list:
    out = []
    for dirpath, dirnames, _ in os.walk(root):
        rel_depth = len(Path(dirpath).relative_to(root).parts)
        keep = []
        for d in dirnames:
            if d.endswith(".xcodeproj"):
                if d != "Pods.xcodeproj":
                    pbx = Path(dirpath) / d / "project.pbxproj"
                    if pbx.exists():
                        out.append(pbx)
            elif d not in SKIP_DIRS and not d.startswith(".") and rel_depth < 4:
                keep.append(d)
        dirnames[:] = keep
    return out


# ---------------------------------------------------------------- dependencies
def _load_deps(proj: Project) -> None:
    root = proj.root
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            proj.deps["npm"] = {**data.get("dependencies", {}), **data.get("peerDependencies", {})}
            proj.deps["npm_dev"] = data.get("devDependencies", {})
        except (json.JSONDecodeError, OSError):
            proj.notes.append("package.json could not be parsed.")
    # pub: prefer lock (full graph)
    lock = root / "pubspec.lock"
    spec = root / "pubspec.yaml"
    if lock.exists():
        cur = None
        for line in lock.read_text(errors="ignore").splitlines():
            m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
            if m:
                cur = m.group(1)
                proj.deps["pub"][cur] = ""
            m = re.match(r'^    version: "?([^"]+)"?', line)
            if m and cur:
                proj.deps["pub"][cur] = m.group(1)
    elif spec.exists():
        section = None
        for line in spec.read_text(errors="ignore").splitlines():
            if re.match(r"^\S", line):
                section = line.split(":")[0].strip()
                continue
            m = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*)$", line)
            if m and section == "dependencies":
                proj.deps["pub"][m.group(1)] = m.group(2).strip()
    fpd = root / ".flutter-plugins-dependencies"
    if fpd.exists():
        try:
            proj.flutter_plugins = json.loads(fpd.read_text()).get("plugins", {}).get("ios", [])
        except (json.JSONDecodeError, OSError):
            pass
    # CocoaPods
    for podlock in list(root.glob("Podfile.lock")) + list(root.glob("ios/Podfile.lock")) + list(root.glob("*/Podfile.lock")):
        in_pods = False
        for line in podlock.read_text(errors="ignore").splitlines():
            if line.startswith("PODS:"):
                in_pods = True
                continue
            if in_pods and re.match(r"^\S", line):
                break
            m = re.match(r"^  - \"?([^\s\"(]+) \(([^)]+)\)", line)
            if in_pods and m:
                proj.deps["pods"][m.group(1)] = m.group(2)
    # SwiftPM
    for resolved in root.rglob("Package.resolved"):
        if any(s in resolved.parts for s in ("node_modules", "Pods", ".build")):
            continue
        try:
            data = json.loads(resolved.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        pins = data.get("pins") or data.get("object", {}).get("pins", [])
        for pin in pins:
            ident = pin.get("identity") or pin.get("package", "")
            ver = (pin.get("state") or {}).get("version") or ""
            loc = pin.get("location") or pin.get("repositoryURL") or ""
            proj.deps["spm"][ident.lower()] = ver
            if loc:
                proj.deps["spm"][loc.rstrip("/").split("/")[-1].removesuffix(".git").lower()] = ver


def _load_expo(proj: Project) -> None:
    if "expo" not in proj.deps["npm"]:
        return
    app_json = proj.root / "app.json"
    cfg = None
    has_cfg = app_json.exists() or any((proj.root / n).exists() for n in
                                       ("app.config.js", "app.config.ts", "app.config.mjs", "app.config.cjs"))
    if not has_cfg:
        if (proj.root / "expo-module.config.json").exists():
            proj.notes.append("This looks like an Expo module (library), not an app; app-level checks are skipped.")
        return
    if app_json.exists():
        try:
            data = json.loads(app_json.read_text())
            cfg = data.get("expo", data)
        except (json.JSONDecodeError, OSError):
            proj.notes.append("app.json could not be parsed.")
    for name in ("app.config.js", "app.config.ts", "app.config.mjs", "app.config.cjs"):
        p = proj.root / name
        if p.exists():
            proj.expo_raw = p.read_text(errors="ignore")
            proj.notes.append(f"{name} is dynamic; values were read from app.json and by text search only. "
                              "Run `npx expo config --type public --json` to confirm resolved values.")
    proj.expo = cfg or {}


def _synth_expo_target(proj: Project) -> None:
    cfg = proj.expo or {}
    ios = cfg.get("ios", {}) or {}
    info = dict(ios.get("infoPlist", {}) or {})
    if cfg.get("version"):
        info.setdefault("CFBundleShortVersionString", cfg["version"])
    if ios.get("buildNumber"):
        info.setdefault("CFBundleVersion", str(ios["buildNumber"]))
    if cfg.get("name"):
        info.setdefault("CFBundleDisplayName", cfg["name"])
    if (ios.get("config") or {}).get("usesNonExemptEncryption") is not None:
        info.setdefault("ITSAppUsesNonExemptEncryption", ios["config"]["usesNonExemptEncryption"])
    info.setdefault("UILaunchStoryboardName", "SplashScreen")  # expo always generates one
    t = Target(name=cfg.get("name") or "expo-app", kind="app", product_type="expo-managed",
               bundle_id=ios.get("bundleIdentifier", ""), info=info, info_path="app.json",
               entitlements=dict(ios.get("entitlements", {}) or {}),
               entitlements_path="app.json" if ios.get("entitlements") else None)
    if ios.get("usesAppleSignIn"):
        t.entitlements.setdefault("com.apple.developer.applesignin", ["Default"])
    if ios.get("privacyManifests"):
        t.manifests.append(("app.json → expo.ios.privacyManifests", ios["privacyManifests"]))
    t.settings["TARGETED_DEVICE_FAMILY"] = "1,2" if ios.get("supportsTablet") or ios.get("isTabletOnly") else "1"
    t.dirs = [proj.root]
    proj.targets.append(t)


def _detect_stacks(proj: Project) -> None:
    if proj.deps["pub"] or (proj.root / "pubspec.yaml").exists():
        proj.stacks.add("flutter")
    if "react-native" in proj.deps["npm"]:
        proj.stacks.add("react-native")
    if "expo" in proj.deps["npm"]:
        proj.stacks.add("expo")
    if any(f.lang in ("swift", "objc") for f in proj.files) and not proj.stacks:
        proj.stacks.add("native")
    if not proj.stacks and proj.targets:
        proj.stacks.add("native")


# ---------------------------------------------------------------- xcodeproj
_VAR = re.compile(r"\$[({]([A-Za-z0-9_]+)(?::[^)}]*)?[)}]")


def _read_xcconfig(path: Path, seen=None) -> dict:
    seen = seen or set()
    out = {}
    if not path.exists() or path in seen:
        return out
    seen.add(path)
    for line in path.read_text(errors="ignore").splitlines():
        line = line.split("//")[0].strip()
        m = re.match(r'#include\??\s+"([^"]+)"', line)
        if m:
            out.update(_read_xcconfig((path.parent / m.group(1)).resolve(), seen))
            continue
        m = re.match(r"([A-Za-z0-9_]+)(\[[^\]]*\])?\s*=\s*(.*)$", line)
        if m and not m.group(2):
            out[m.group(1)] = m.group(3).strip()
    return out


def _expand(value, env: dict, depth: int = 0):
    if not isinstance(value, str) or depth > 5:
        return value
    def sub(m):
        k = m.group(1)
        v = env.get(k)
        return str(_expand(v, env, depth + 1)) if v is not None else m.group(0)
    if m := re.fullmatch(r"\$[({](\w+):rfc1034identifier[)}]", value):
        return re.sub(r"[^A-Za-z0-9.-]", "-", str(env.get(m.group(1), m.group(0))))
    return _VAR.sub(sub, value)


def _kind(product_type: str) -> str:
    if product_type.endswith(".application") or product_type.endswith(".application.messages"):
        return "app"
    if "watchapp" in product_type or "watchkit" in product_type:
        return "watch"
    if "extension" in product_type:
        return "extension"
    if "test" in product_type:
        return "test"
    return "other"


def _flutter_versions(proj: Project) -> dict:
    spec = proj.root / "pubspec.yaml"
    if not spec.exists():
        return {}
    m = re.search(r"^version:\s*([0-9][^\s+]*)(?:\+(\S+))?", spec.read_text(errors="ignore"), re.M)
    if not m:
        return {}
    return {"FLUTTER_BUILD_NAME": m.group(1), "FLUTTER_BUILD_NUMBER": m.group(2) or "1"}


def _load_xcodeproj(proj: Project, pbx: Path) -> None:
    data = openstep.loads(pbx.read_text(errors="ignore"))
    objs = data["objects"]
    proj_dir = pbx.parent.parent
    root_obj = objs[data["rootObject"]]

    # file-ref path resolution via group tree
    parent = {}
    for oid, o in objs.items():
        for child in o.get("children", []) if isinstance(o, dict) else []:
            parent[child] = oid
    main_group = root_obj.get("mainGroup")
    cache = {}

    def full_path(oid) -> Path:
        if oid in cache:
            return cache[oid]
        o = objs.get(oid, {})
        path = o.get("path", "")
        tree = o.get("sourceTree", "<group>")
        if oid == main_group:
            res = proj_dir / root_obj.get("projectDirPath", "")
        elif tree == "<group>":
            base = full_path(parent[oid]) if oid in parent else proj_dir
            res = base / path if path else base
        elif tree == "SOURCE_ROOT":
            res = proj_dir / path
        elif tree == "<absolute>":
            res = Path(path)
        else:
            res = proj_dir / "__external__" / path
        cache[oid] = res
        return res

    base_env = {"SRCROOT": str(proj_dir), "PROJECT_DIR": str(proj_dir),
                "PROJECT_NAME": pbx.parent.stem, **_flutter_versions(proj)}
    def layered(c: dict) -> dict:
        out = {}
        if c.get("baseConfigurationReference"):
            out.update(_read_xcconfig(full_path(c["baseConfigurationReference"])))
        elif c.get("baseConfigurationReferenceAnchor"):  # Xcode 16 synchronized folders
            anchor = full_path(c["baseConfigurationReferenceAnchor"])
            out.update(_read_xcconfig(anchor / c.get("baseConfigurationReferenceRelativePath", "")))
        out.update(c.get("buildSettings", {}))
        return out

    proj_settings = {}
    pconfigs = [objs[c] for c in objs.get(root_obj.get("buildConfigurationList", ""), {}).get("buildConfigurations", [])]
    pcfg = next((c for c in pconfigs if c.get("name") == "Release"), pconfigs[0] if pconfigs else {})
    proj_settings = layered(pcfg)

    for tid in root_obj.get("targets", []):
        t = objs[tid]
        if t.get("isa") != "PBXNativeTarget":
            continue
        ptype = t.get("productType", "")
        configs = [objs[c] for c in objs.get(t.get("buildConfigurationList", ""), {}).get("buildConfigurations", [])]
        cfg = next((c for c in configs if c.get("name") == "Release"), configs[0] if configs else {})
        settings = {**proj_settings, **layered(cfg)}
        env = {**base_env, **settings, "TARGET_NAME": t.get("name", "")}
        env.setdefault("PRODUCT_NAME", t.get("name", ""))
        for k in list(settings):
            settings[k] = _expand(settings[k], env)
            env[k] = settings[k]

        target = Target(name=t.get("name", "?"), kind=_kind(ptype), product_type=ptype,
                        settings=settings, project_file=proj.rel(pbx), project_dir=proj_dir.resolve())
        target.bundle_id = str(settings.get("PRODUCT_BUNDLE_IDENTIFIER", ""))

        # Info.plist (file + INFOPLIST_KEY_* overrides)
        info = {}
        if settings.get("INFOPLIST_FILE"):
            ip = (proj_dir / settings["INFOPLIST_FILE"]).resolve()
            target.info_path = proj.rel(ip)
            target.dirs.append(ip.parent)
            try:
                info = plistlib.loads(ip.read_bytes())
            except Exception:  # noqa: BLE001
                proj.notes.append(f"{target.name}: Info.plist {target.info_path} missing or unreadable.")
        for k, v in settings.items():
            if k.startswith("INFOPLIST_KEY_"):
                key = k[len("INFOPLIST_KEY_"):]
                if key == "UILaunchScreen_Generation" and str(v).upper() == "YES":
                    info.setdefault("UILaunchScreen", {})
                elif key.startswith("UISupportedInterfaceOrientations"):
                    info.setdefault(key, str(v).split())
                else:
                    info.setdefault(key, v)
        info = {k: _expand(v, env) for k, v in info.items()}
        target.info = info

        # entitlements
        if settings.get("CODE_SIGN_ENTITLEMENTS"):
            ep = (proj_dir / settings["CODE_SIGN_ENTITLEMENTS"]).resolve()
            target.entitlements_path = proj.rel(ep)
            target.dirs.append(ep.parent)
            try:
                target.entitlements = plistlib.loads(ep.read_bytes())
            except Exception:  # noqa: BLE001
                proj.notes.append(f"{target.name}: entitlements {target.entitlements_path} unreadable.")

        # synchronized folders (Xcode 16+) and build-phase file refs
        for gid in t.get("fileSystemSynchronizedGroups", []):
            target.dirs.append(full_path(gid).resolve())
        resource_paths = []
        for ph in t.get("buildPhases", []):
            phase = objs.get(ph, {})
            for bf in phase.get("files", []):
                ref = objs.get(bf, {}).get("fileRef")
                if not ref:
                    continue
                fp = full_path(ref).resolve()
                if phase.get("isa") == "PBXSourcesBuildPhase":
                    target.source_rels.add(proj.rel(fp))
                elif phase.get("isa") == "PBXResourcesBuildPhase":
                    resource_paths.append(fp)
        guess = proj_dir / target.name
        if guess.is_dir():
            target.dirs.append(guess.resolve())
        target.dirs = list(dict.fromkeys(target.dirs))

        # privacy manifests
        found = set()
        for fp in resource_paths:
            if fp.name == "PrivacyInfo.xcprivacy" and fp.exists():
                found.add(fp)
        for d in target.dirs:
            if d == proj_dir.resolve():
                continue
            for mp in d.rglob("PrivacyInfo.xcprivacy"):
                if not any(s in mp.parts for s in ("Pods", "node_modules", ".build")):
                    found.add(mp.resolve())
        for mp in sorted(found):
            try:
                target.manifests.append((proj.rel(mp), plistlib.loads(mp.read_bytes())))
            except Exception:  # noqa: BLE001
                target.manifests.append((proj.rel(mp), None))
        proj.targets.append(target)


def _attribute_sources(proj: Project) -> None:
    """Assign code files to targets: build-phase refs + owned dirs; app targets get the rest."""
    claimed = set()
    for t in proj.targets:
        if t.kind == "app":
            continue
        own_dirs = [d for d in t.dirs if d != t.project_dir and d != proj.root]
        for f in proj.files:
            if any(_under(f.path, d) for d in own_dirs):
                t.source_rels.add(f.rel)
        claimed |= t.source_rels
    for t in proj.targets:
        if t.kind == "app":
            t.source_rels |= {f.rel for f in proj.files if f.rel not in claimed}


def _under(path: Path, d: Path) -> bool:
    try:
        path.resolve().relative_to(d)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- built products
def _load_bundle(p: Path) -> Project:
    proj = Project(p.parent)
    proj.is_bundle = True
    proj.stacks.add("bundle")
    app = None
    if p.suffix == ".ipa":
        tmp = tempfile.mkdtemp(prefix="preflight-ipa-")
        proj._tmp = tmp
        with zipfile.ZipFile(p) as z:
            for member in z.namelist():
                dest = (Path(tmp) / member).resolve()
                if not str(dest).startswith(str(Path(tmp).resolve())):
                    raise ValueError("unsafe path in ipa")
            z.extractall(tmp)
        apps = list((Path(tmp) / "Payload").glob("*.app"))
        app = apps[0] if apps else None
        proj.root = Path(tmp)
    elif p.suffix == ".xcarchive":
        apps = list((p / "Products" / "Applications").glob("*.app"))
        app = apps[0] if apps else None
        proj.root = p
    else:
        app = p
        proj.root = p.parent
    if not app:
        proj.notes.append("No .app found inside the bundle.")
        return proj
    bundles = [(app, "app")]
    for sub in ("PlugIns", "Extensions"):
        bundles += [(x, "extension") for x in (app / sub).glob("*.appex")]
    bundles += [(x, "watch") for x in (app / "Watch").glob("*.app")]
    for bpath, kind in bundles:
        info = {}
        try:
            info = plistlib.loads((bpath / "Info.plist").read_bytes())
        except Exception:  # noqa: BLE001
            proj.notes.append(f"{bpath.name}: Info.plist unreadable")
        t = Target(name=bpath.stem, kind=kind, info=info, bundle_path=bpath,
                   bundle_id=info.get("CFBundleIdentifier", ""), info_path=proj.rel(bpath / "Info.plist"))
        exe = info.get("CFBundleExecutable")
        if exe and (bpath / exe).exists():
            t.binary = bpath / exe
        mp = bpath / "PrivacyInfo.xcprivacy"
        if mp.exists():
            try:
                t.manifests.append((proj.rel(mp), plistlib.loads(mp.read_bytes())))
            except Exception:  # noqa: BLE001
                t.manifests.append((proj.rel(mp), None))
        t.entitlements = _codesign_entitlements(bpath)
        t.entitlements_path = f"codesign:{bpath.name}" if t.entitlements else None
        proj.targets.append(t)
    return proj


def _codesign_entitlements(bpath: Path) -> dict:
    if not shutil.which("codesign"):
        return {}
    try:
        out = subprocess.run(["codesign", "-d", "--entitlements", "-", "--xml", str(bpath)],
                             capture_output=True, timeout=30)
        blob = out.stdout
        start = blob.find(b"<?xml")
        return plistlib.loads(blob[start:]) if start >= 0 else {}
    except Exception:  # noqa: BLE001
        return {}


def binary_contains(t: Target, *needles: bytes) -> list:
    if not t.binary:
        return []
    try:
        data = t.binary.read_bytes()
    except OSError:
        return []
    return [n.decode() for n in needles if n in data]


def iter_literals(text: str) -> Iterable[str]:
    for m in _STR_LIT.finditer(text):
        yield m.group(1) or m.group(2) or m.group(3) or ""
