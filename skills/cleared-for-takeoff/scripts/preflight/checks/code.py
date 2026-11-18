"""Code-level checks: deprecated/private APIs, dynamic code, secrets, placeholder & platform copy,
review prompts, hidden features (2.5.19), UGC safeguards (1.2)."""
from __future__ import annotations

import re

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, VALIDATOR_BLOCKING, VALIDATOR_CERTAIN, WARNING
from . import check, make

FC = make("code")
FS = make("secrets")
FT = make("content")
FH = make("hidden-features")
FU = make("ugc")


@check("code", "Deprecated/private APIs & dynamic code", "Code", bundle=True)
def code(proj):
    out = []
    if proj.is_bundle:
        for t in proj.shipping_targets():
            bins = [t.binary] if t.binary else []
            if t.bundle_path:
                bins += [fw / fw.stem for fw in (t.bundle_path / "Frameworks").glob("*.framework") if (fw / fw.stem).exists()]
            for b in bins:
                try:
                    if b"UIWebView" in b.read_bytes():
                        out.append(FC("uiwebview", f"UIWebView referenced in {b.name}", BLOCKER, VALIDATOR_CERTAIN,
                                      "ITMS-90809", f"{proj.rel(b)} contains UIWebView symbols.",
                                      "Update the framework / replace with WKWebView.", target=t.name))
                except OSError:
                    pass
        return out
    rules = [
        ("uiwebview", r"\bUIWebView\b", ("swift", "objc"), BLOCKER, VALIDATOR_BLOCKING, "ITMS-90809",
         "UIWebView is rejected at upload.", "Replace with WKWebView."),
        ("private-api", r"NSSelectorFromString\(\s*@?\"_|valueForKey(Path)?:?\s*\(?@?\"_[a-z]|value\(forKey:\s*\"_|"
         r"\bLSApplicationWorkspace\b|\bUIGetScreenImage\b|\b_UIBackdropView\b|\bUIStatusBarManager\b.*_|setValue\(.*forKey:\s*\"_",
         ("swift", "objc"), BLOCKER, REVIEW_RISK, "2.5.1",
         "Private API / private ivar access. Apple's static analyzer flags these.",
         "Use only public APIs. If this is your own selector named with a leading underscore, rename it."),
        ("dlopen", r"\bdlopen\s*\(|\bdlsym\s*\(|NSClassFromString\(\s*\"_", ("swift", "objc"), WARNING, REVIEW_RISK, "2.5.2",
         "Runtime symbol loading can be read as downloading/executing code or calling private API.",
         "Remove unless strictly necessary; explain in review notes."),
        ("eval", r"(?<![\w.])eval\s*\(|new Function\s*\(", ("js",), WARNING, JUDGMENT, "2.5.2",
         "eval / new Function. Executing downloaded code that changes features violates 2.5.2.",
         "Fine for bundled code; never evaluate remote code that adds or changes features."),
        ("js-eval-native", r"evaluateScript\(|evaluateJavaScript\(", ("swift", "objc"), INFO, JUDGMENT, "2.5.2",
         "JavaScriptCore/WebView script execution.", "Make sure the scripts are bundled or don't change app functionality."),
        ("deprecated", r"\bUIAlertView\b|\bUIActionSheet\b|\bALAssetsLibrary\b|\bABAddressBook|\bUILocalNotification\b|"
         r"\bAddressBookUI\b|\bMPMoviePlayerController\b|\bGLKView\b|\bEAGLContext\b", ("swift", "objc"), INFO, JUDGMENT, "2.5.1",
         "Deprecated framework usage.", "Migrate to the modern replacement (UIAlertController, Photos, Contacts, …)."),
        ("exit", r"(?<![\w.])exit\s*\(\s*0?\s*\)|\babort\s*\(\s*\)|SystemNavigator\.pop|BackHandler\.exitApp|\bexit\(0\)",
         ("swift", "objc", "dart", "js"), WARNING, REVIEW_RISK, "2.1 / HIG",
         "Programmatically quitting the app looks like a crash to reviewers.", "Never quit; show a screen explaining the state instead."),
    ]
    for rid, rx, langs, sev, conf, gl, why, fix in rules:
        hits = proj.grep(rx, langs=langs)
        if not hits:
            continue
        h = hits[0]
        more = f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""
        out.append(FC(rid, why.split(".")[0], sev, conf, gl, f"`{h.text[:100]}`{more}. {why}", fix, file=h.file, line=h.line))
    # OTA updates
    ota = proj.has_dep("expo-updates", "react-native-code-push", "@revopush/react-native-code-push", "shorebird_code_push",
                       "hot-updater", "@hot-updater/react-native")
    if ota:
        out.append(FC("ota", f"Over-the-air updates ({ota[0]})", INFO, JUDGMENT, "2.5.2 / 3.3.1(b) DPLA",
                      "OTA JS/Dart updates are allowed for bug fixes and small changes.",
                      "Do not ship new features or change the app's primary purpose via OTA; that requires review. "
                      "Make sure the reviewed binary contains every feature you will turn on.", ))
    # custom review prompts (5.6.1)
    rate = proj.grep_strings(r"(?i)\brate (us|this app|our app)\b|leave (us )?a review|enjoying .{1,30}\?|5[- ]stars?")
    sys_api = proj.grep(r"requestReview|SKStoreReviewController|StoreReview\.requestReview|InAppReview|in_app_review|"
                        r"react-native-rate|action=write-review", limit=1) or proj.has_dep("expo-store-review", "in_app_review",
                                                                                           "react-native-in-app-review")
    if rate and not sys_api:
        h = rate[0]
        out.append(FC("custom-review-prompt", "Custom rating prompt", WARNING, REVIEW_RISK, "5.6.1",
                      f"`{h.text[:100]}`. Custom review prompts are not allowed.",
                      "Use SKStoreReviewController / requestReview (expo-store-review, in_app_review). Linking to "
                      "the App Store write-review page from a user-initiated button is fine.", file=h.file, line=h.line))
    elif rate:
        h = rate[0]
        out.append(FC("review-gating", "Rating copy alongside the system prompt", INFO, JUDGMENT, "5.6.1",
                      f"`{h.text[:100]}`. Pre-prompts that filter happy users toward the review sheet ('Enjoying the "
                      "app?') are considered review manipulation.", "Call requestReview directly at a natural moment.",
                      file=h.file, line=h.line))
    return out


# ---------------------------------------------------------------- secrets
SECRET_PATTERNS = [
    ("stripe-secret", r"\b(sk|rk)_live_[0-9A-Za-z]{16,}"),
    ("aws-key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("private-key", r"-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----"),
    ("openai-key", r"\bsk-(proj-|svcacct-)?[A-Za-z0-9_\-]{32,}"),
    ("anthropic-key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    ("github-token", r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
    ("slack-token", r"\bxox[baprs]-[0-9A-Za-z\-]{10,}"),
    ("google-service-account", r"\"type\"\s*:\s*\"service_account\""),
    ("supabase-service-role", r"service_role"),
    ("twilio-secret", r"\bSK[0-9a-fA-F]{32}\b"),
]


@check("secrets", "Hardcoded secrets", "Security")
def secrets(proj):
    out = []
    seen = set()
    for rid, rx in SECRET_PATTERNS:
        hits = proj.grep(rx, include_debug=True) + [h for h in proj.grep_config(rx)
                                                    if not h.file.endswith(("package-lock.json", "Package.resolved"))]
        for h in hits[:2]:
            if (h.file, h.line) in seen:
                continue
            seen.add((h.file, h.line))
            if rid == "supabase-service-role" and not re.search(r"ey[A-Za-z0-9_-]{20,}", h.text):
                continue
            out.append(FS(rid, f"Possible secret: {rid}", WARNING, REVIEW_RISK, "1.6 / 2.5",
                          f"`{_redact(h.text)}`. Anything in the bundle can be extracted from the IPA.",
                          "Move the secret server-side and rotate it now. (Client keys designed to ship, such as "
                          "Firebase/Google Maps 'AIza…', RevenueCat public, Stripe pk_, and Supabase anon keys, are fine.)",
                          file=h.file, line=h.line))
    return out


def _redact(text: str) -> str:
    return re.sub(r"([A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]{8,}", r"\1…", text)[:120]


# ---------------------------------------------------------------- content
PLATFORM_EXCLUDE = re.compile(r"Platform\.(OS|select|isAndroid|isIOS)|defaultTargetPlatform|TargetPlatform\.|"
                              r"Platform\.android|\bandroid\s*:|ios\s*:|\.android\b|useAndroid|isAndroid|androidPackage|"
                              r"com\.android|android\.permission|ANDROID_|packageName")


@check("content", "Placeholder, beta, and other-platform copy", "UI & assets")
def content(proj):
    out = []
    rules = [
        ("placeholder", r"(?i)lorem ipsum|\bplaceholder text\b|coming soon|under construction|\bTODO\b|\bFIXME\b|"
         r"\btest@test\.|\bsample text\b|\bdummy (text|data)\b|\bnot implemented\b",
         WARNING, REVIEW_RISK, "2.1 / 2.3.3",
         "Placeholder or unfinished content in user-facing strings.", "Ship complete content; hide unfinished features entirely."),
        ("other-platform", r"(?i)\bandroid\b|google play|play store|\bwindows phone\b",
         WARNING, REVIEW_RISK, "2.3.10",
         "References to other mobile platforms in the iOS app.", "Remove mentions of Android/Google Play from iOS UI copy."),
        ("beta-copy", r"(?i)\bbeta\b|\btest (build|version)\b|\bdemo version\b|\btrial version\b|\bpreview build\b",
         INFO, JUDGMENT, "2.2",
         "Beta/demo wording in UI strings. Betas belong on TestFlight.", "Remove 'beta' labels from the App Store build."),
    ]
    for rid, rx, sev, conf, gl, why, fix in rules:
        hits = proj.grep_strings(rx, line_exclude=PLATFORM_EXCLUDE if rid == "other-platform" else None)
        # ignore literals that are clearly identifiers/keys (no spaces) for prose rules
        hits = [h for h in hits if rid != "other-platform" or re.search(r"[\"'`][^\"'`]*\s[^\"'`]*(android|play)", h.text, re.I)]
        if not hits:
            continue
        h = hits[0]
        more = f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""
        out.append(FT(rid, why.split(".")[0], sev, conf, gl, f"`{h.text[:100]}`{more}. {why}", fix, file=h.file, line=h.line))
    return out


# ---------------------------------------------------------------- hidden features
@check("hidden-features", "Hidden or dormant features (2.5.19)", "Compliance")
def hidden(proj):
    out = []
    strong = proj.grep(r"(?i)\b(is_?)?(app_?|apple_?)?(review(er)?_?mode|in_?review|apple_?review(er)?|is_?reviewer|"
                       r"hide_?for_?review|reviewer_?(account|device|build))\b")
    if strong:
        h = strong[0]
        out.append(FH("review-detection", "Code appears to detect App Review", BLOCKER, JUDGMENT, "2.5.19 / 2.3.1",
                      f"`{h.text[:100]}`. Changing behaviour for reviewers is bait-and-switch and can terminate the "
                      "developer account.", "Remove reviewer detection; every feature must be visible to the reviewer.",
                      file=h.file, line=h.line))
    env = proj.grep(r"sandboxReceipt|appStoreReceiptURL|AppTransaction.*environment|\.environment\s*==\s*\.(sandbox|xcode)|"
                    r"isTestFlight|is_testflight|isTestflight|Environment\.sandbox")
    if env:
        h = env[0]
        out.append(FH("env-detection", "Sandbox/TestFlight environment detection", INFO, JUDGMENT, "2.5.19",
                      f"`{h.text[:100]}`. Fine for receipt validation and analytics routing.",
                      "Make sure it never hides or unlocks user-facing features.", file=h.file, line=h.line))
    flags = proj.has_dep("firebase_remote_config", "@react-native-firebase/remote-config", "FirebaseRemoteConfig",
                         "launchdarkly_flutter_client_sdk", "@launchdarkly/react-native-client-sdk", "LaunchDarkly",
                         "statsig", "statsig-react-native", "@statsig/react-native-bindings", "configcat-client",
                         "growthbook", "@growthbook/growthbook-react", "posthog-react-native", "posthog_flutter", "posthog-ios",
                         "flagsmith", "unleash_proxy_client_flutter", "@unleash/proxy-client-react", "optimizely")
    if not flags:
        rc = proj.grep(r"RemoteConfig\.remoteConfig\(\)|featureFlag|FeatureFlag|isFeatureEnabled|feature_flag", limit=1)
        flags = [f"`{rc[0].text[:60]}`"] if rc else []
    if flags:
        out.append(FH("remote-flags", f"Remote feature flags ({flags[0]})", INFO, JUDGMENT, "2.5.19",
                      "Flags are allowed, but every feature they can turn on must be in the reviewed build, reachable "
                      "by the reviewer, and described in the review notes.",
                      "List flag-gated features in App Review notes and make sure they are ON (or toggleable) for review."))
    return out


# ---------------------------------------------------------------- UGC
UGC_SIGNALS = (r"\b(createPost|submitPost|uploadPost|postComment|addComment|sendMessage|createComment|publishPost|"
               r"ChatViewController|ChatScreen|ChatView|CommentsView|CommentsScreen|FeedView|FeedScreen|"
               r"CommunityView|ForumView)\b|collection\([\"'](posts|comments|messages|chats)[\"']\)|"
               r"\.from\([\"'](posts|comments|messages)[\"']\)")
UGC_DEPS = ("stream_chat_flutter", "stream-chat-react-native", "stream-chat-expo", "StreamChat", "StreamChatSwiftUI",
            "sendbird_chat_sdk", "@sendbird/chat", "SendbirdChatSDK", "react-native-gifted-chat", "flutter_chat_ui",
            "TwilioConversationsClient", "@twilio/conversations", "cometchat", "@cometchat/chat-sdk-react-native")
REPORT = r"(?i)report[_ ]?(content|post|user|abuse|comment|message)|reportUser|reportPost|flag[_ ]?(content|post)|\breport\b.*(button|action|menu)"
BLOCK = r"(?i)block[_ ]?user|blockUser|blockedUsers|blocked_users|\bmute[_ ]?user"
EULA = r"(?i)zero[- ]tolerance|community guidelines|\bEULA\b|terms of (use|service)|acceptTerms|agreedToTerms|accepted_terms"


@check("ugc", "User-generated content safeguards (1.2)", "Safety")
def ugc(proj):
    out = []
    dep = proj.has_dep(*UGC_DEPS)
    sig = proj.grep(UGC_SIGNALS, limit=1)
    if not (dep or sig):
        return out
    ev = f"dependency {dep[0]}" if dep else f"`{sig[0].text[:80]}`"
    missing = []
    if not (proj.grep(REPORT, limit=1) or proj.grep_strings(r"(?i)\breport\b")):
        missing.append("report/flag content")
    if not (proj.grep(BLOCK, limit=1) or proj.grep_strings(r"(?i)\bblock\b")):
        missing.append("block abusive users")
    if not (proj.grep(EULA, limit=1) or proj.grep_strings(EULA)):
        missing.append("terms acceptance (zero tolerance for objectionable content)")
    if missing:
        out.append(FU("safeguards", "User-generated content without required safeguards", WARNING, JUDGMENT, "1.2",
                      f"UGC / chat detected ({ev}); could not find: {', '.join(missing)}.",
                      "Apps with UGC (including random/anonymous chat and AI-generated content) need: filtering of "
                      "objectionable material, a way to report content with a timely response (24h), the ability to "
                      "block users, published contact info, and an unchecked terms agreement before posting.",
                      file=sig[0].file if sig else None, line=sig[0].line if sig else None))
    return out
