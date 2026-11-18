"""Data sharing: App Tracking Transparency (5.1.2(i)), third-party AI consent (5.1.2(i)),
analytics consent signals (5.1.1)."""
from __future__ import annotations

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, VALIDATOR_BLOCKING, WARNING
from . import check, make

FATT = make("att")
FAI = make("ai-consent")

TRACKING_SDKS = {
    "AppsFlyer": ("react-native-appsflyer", "appsflyer_sdk", "AppsFlyerFramework", "AppsFlyerLib"),
    "Adjust": ("react-native-adjust", "adjust_sdk", "Adjust"),
    "Meta SDK": ("react-native-fbsdk-next", "facebook_app_events", "FBSDKCoreKit", "FacebookCore", "facebook-ios-sdk"),
    "Google Mobile Ads": ("react-native-google-mobile-ads", "google_mobile_ads", "Google-Mobile-Ads-SDK", "GoogleMobileAds",
                          "swift-package-manager-google-mobile-ads"),
    "AppLovin": ("react-native-applovin-max", "applovin_max", "AppLovinSDK"),
    "ironSource / Unity LevelPlay": ("ironsource_mediation", "IronSourceSDK", "unity_levelplay_mediation"),
    "Unity Ads": ("UnityAds", "unity_ads_plugin"),
    "Branch": ("react-native-branch", "flutter_branch_sdk", "Branch", "BranchSDK"),
    "Singular": ("singular-react-native", "singular_flutter_sdk", "Singular-SDK"),
    "Kochava": ("react-native-kochava-tracker", "KochavaNetworking"),
    "TikTok Business SDK": ("TikTokBusinessSDK",),
}
IDFA = r"advertisingIdentifier|ASIdentifierManager|getAdvertisingId|advertising_id"
ATT_REQ = r"requestTrackingAuthorization|requestTrackingPermissionsAsync|requestTrackingAuthorizationAsync|AppTrackingTransparency\.request|TrackingTransparency.*request"
ATT_DEPS = ("expo-tracking-transparency", "react-native-tracking-transparency", "app_tracking_transparency")

AI_ENDPOINTS = (r"api\.openai\.com|generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com|api\.anthropic\.com|"
                r"api\.x\.ai|api\.mistral\.ai|api\.groq\.com|openrouter\.ai|api\.together\.xyz|api\.replicate\.com|"
                r"api\.stability\.ai|api\.elevenlabs\.io|api\.deepgram\.com|api\.assemblyai\.com|api\.perplexity\.ai|"
                r"api\.deepseek\.com|api\.cohere\.(ai|com)|fal\.run|api\.fireworks\.ai|openai\.azure\.com")
AI_CODE = (r"import (OpenAI|GoogleGenerativeAI|FirebaseAI|FirebaseVertexAI|SwiftAnthropic|SwiftOpenAI|AIProxy)\b|"
           r"from ['\"](openai|@anthropic-ai/sdk|@google/generative-ai|@google/genai)['\"]|FirebaseAI\.firebaseAI|getGenerativeModel")
AI_DEPS = ("openai", "@anthropic-ai/sdk", "@google/generative-ai", "@google/genai", "dart_openai", "google_generative_ai",
           "firebase_ai", "firebase_vertexai", "@react-native-firebase/ai", "@react-native-firebase/vertexai", "langchain",
           "ai", "@ai-sdk/openai", "openai-kit", "swiftopenai", "swiftanthropic", "aiproxyswift", "generative-ai-swift",
           "firebase-ios-sdk/FirebaseAI", "groq-sdk", "replicate", "elevenlabs")
AI_CONSENT = (r"(?i)ai[_ ]?consent|hasAccepted(AI|Ai)|aiDataSharing|ai_data_sharing|consentTo(AI|Ai)|thirdParty(AI|Ai)|"
              r"aiDisclosure|ai_disclosure|dataSharingConsent|shareDataWith(OpenAI|Anthropic|Google)")


@check("att", "App Tracking Transparency", "Privacy")
def att(proj):
    out = []
    sdks = [(name, proj.has_dep(*deps)[0]) for name, deps in TRACKING_SDKS.items() if proj.has_dep(*deps)]
    idfa = proj.grep(IDFA, limit=1)
    att_call = proj.has_dep(*ATT_DEPS) or proj.grep(ATT_REQ, limit=1)
    apps = proj.main_targets()
    info = apps[0].info if apps else {}
    has_key = bool(str(info.get("NSUserTrackingUsageDescription", "")).strip())
    if (sdks or idfa) and not att_call:
        ev = ", ".join(f"{n} ({d})" for n, d in sdks) or f"IDFA access `{idfa[0].text[:70]}`"
        out.append(FATT("missing", "Tracking/ads SDK without an ATT prompt", WARNING, REVIEW_RISK, "5.1.2(i)",
                        f"Found {ev} but no ATTrackingManager.requestTrackingAuthorization call.",
                        "If the SDK links user/device data with other companies' data for ads or measurement, request "
                        "ATT before it starts (and configure the SDK to wait). If it is configured for first-party use only, "
                        "say so in App Privacy answers and review notes.",
                        file=idfa[0].file if idfa else None, line=idfa[0].line if idfa else None))
    if att_call and not has_key and not proj.expo_managed:
        out.append(FATT("no-string", "ATT requested without NSUserTrackingUsageDescription", BLOCKER, VALIDATOR_BLOCKING,
                        "5.1.1(ii) / ITMS-90683", "ATT authorization is requested but the purpose string is missing (crash).",
                        "Add NSUserTrackingUsageDescription.", file=apps[0].info_path if apps else None))
    if has_key and not att_call:
        out.append(FATT("string-no-prompt", "NSUserTrackingUsageDescription set but ATT never requested", WARNING,
                        REVIEW_RISK, "2.1 / 5.1.2(i)",
                        "Reviewers look for the ATT prompt when the key exists and reject with 'we couldn't locate the "
                        "App Tracking Transparency request'.",
                        "Either request ATT (after the app is active, not in didFinishLaunching) or remove the key and "
                        "set 'used for tracking' to No in App Privacy.", file=apps[0].info_path if apps else None))
    if att_call:
        early = proj.grep(r"didFinishLaunchingWithOptions|application\(.*didFinishLaunching", limit=0)
        # flag requestTracking inside the same file as didFinishLaunching (common "prompt never shows" bug)
        req_hits = proj.grep(ATT_REQ)
        files = {h.file for h in early}
        bad = [h for h in req_hits if h.file in files]
        if bad:
            out.append(FATT("too-early", "ATT may be requested before the app is active", INFO, JUDGMENT, "2.1",
                            "requestTrackingAuthorization appears in the same file as didFinishLaunching. On iOS 15+ the "
                            "prompt silently fails if requested before the app is active, so the reviewer never sees it.",
                            "Request it from applicationDidBecomeActive / a SwiftUI .task on the first screen.",
                            file=bad[0].file, line=bad[0].line))
    return out


@check("ai-consent", "Third-party AI data sharing consent", "Privacy")
def ai(proj):
    out = []
    ep = proj.grep(AI_ENDPOINTS, limit=1) or proj.grep_config(AI_ENDPOINTS)[:1]
    code = proj.grep(AI_CODE, limit=1)
    dep = proj.has_dep(*[d for d in AI_DEPS if d != "ai"]) or (["ai"] if "ai" in proj.deps["npm"] else [])
    if not (ep or code or dep):
        return out
    ev = (f"endpoint `{ep[0].text[:80]}` ({ep[0].file}:{ep[0].line})" if ep else
          f"`{code[0].text[:80]}` ({code[0].file}:{code[0].line})" if code else f"dependency {dep[0]}")
    loc = (ep or code or [None])[0]
    if proj.grep(AI_CONSENT, limit=1):
        out.append(FAI("verify", "Third-party AI in use; consent gate found, verify it", INFO, JUDGMENT, "5.1.2(i)",
                       f"AI provider usage: {ev}. A consent flag exists.",
                       "Confirm the consent screen names the provider and data sent, runs before the first request, "
                       "can be withdrawn in Settings, and the privacy policy + App Privacy answers name the provider.",
                       file=loc.file if loc else None, line=loc.line if loc else None))
    else:
        out.append(FAI("missing", "Personal data may be sent to a third-party AI without explicit consent", WARNING,
                       REVIEW_RISK, "5.1.2(i)",
                       f"AI provider usage: {ev}. No consent gate was found.",
                       "Before the first AI request, show a screen that names the provider (e.g. OpenAI) and what is sent "
                       "(prompts, photos, voice), with an affirmative Allow action. Store the choice, allow withdrawal, "
                       "and name the provider in the privacy policy. Backend proxies don't exempt you. Also if the AI "
                       "generates content, add 1.2 safeguards (report/filter).",
                       file=loc.file if loc else None, line=loc.line if loc else None))
    return out
