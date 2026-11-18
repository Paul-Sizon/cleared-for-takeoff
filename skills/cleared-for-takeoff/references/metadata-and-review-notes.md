# Metadata and App Review notes

## Getting metadata
1. **asc CLI** (github.com/rudrankriyam/App-Store-Connect-CLI). Install it with `brew install asc`. Authenticate with `asc auth login`, or set `ASC_KEY_ID`, `ASC_ISSUER_ID` and `ASC_PRIVATE_KEY_PATH`. Run `asc auth doctor` to debug.
   ```bash
   asc metadata pull --app "<APP_ID>" --version "<VERSION>" --dir ./.preflight-metadata
   # app-info: ./.preflight-metadata/app-info/*.json   version texts: ./.preflight-metadata/version/<VERSION>/*.json
   ```
   Creative assets (2.3.14) live in the Asset Library. If `asc` doesn't return them, ask the user.
2. **fastlane**: `fastlane/metadata/<locale>/{name,subtitle,description,keywords,promotional_text,release_notes,privacy_url,support_url}.txt` and `fastlane/metadata/review_information/*`.
3. **Ask the user** to paste the fields. Never invent them.

## Field checks
| Field | Rules |
|---|---|
| Name (≤30) | No price words, no keyword stuffing, no Apple trademarks as part of the name, and no competitor or other-platform names (2.3.7, 5.2.5). Must match the app's display name closely. |
| Subtitle (≤30) | Same rules as the name. No "free", "best", "#1". |
| Keywords (≤100 bytes) | No competitor or brand names you don't own, no Apple trademarks, no category names, no "app". No China-restricted AI terms (ChatGPT, Gemini…) in **any** locale if the app ships in China. |
| Description | Every claimed feature exists. IAP and subscriptions are disclosed (2.3.2). No other-platform references (2.3.10). Subscriptions: include the Terms of Use (EULA) link and the Privacy Policy link. |
| Screenshots / previews | Show the app in use. Content matches the build. No "Free" text, even inside captured screens. Device frames for the right device classes. iPhone Duo set required from April 2027. |
| Creative assets (2.3.14) | Related to the app or brand. No pricing or discounts. No unverifiable claims. All-audience appropriate. No misleading references to other apps. |
| What's New | Describes real changes. New features must also appear in the review notes (2.3.1). |
| Age rating | Questionnaire answered honestly: social-media questions (Sept 2026), Shared Location and Dating descriptors (Nov 2026 → Jan 2027), UGC, gambling, medical. Ratings that are too low get the app rejected. |
| Privacy policy URL | Loads, is specific to this app, and names the data collected and who receives it (third-party AI providers by name). |
| Support URL | Loads and has real contact info. |
| App Privacy answers | Match the SDKs found: analytics, crash reporting, ads, AI providers. Mismatches are rejected under 5.1.1/5.1.2. |
| Regulated medical device (Health & Fitness / Medical) | Status declared (Mar 2026 requirement). |

## Review notes template (fill in; keep it under ~1500 chars)

```
WHAT THE APP DOES
<One sentence: who it is for and the core job.>

HOW TO TEST
Demo account: <email> / <password>  (no 2FA; pre-loaded with sample data)
1. <Path to the core feature>
2. <Path to the paid feature / paywall>. Sandbox purchases work. Restore is in Settings → Restore Purchases.
3. <Path to account deletion: Settings → Account → Delete Account>

FEATURES THAT NEED EXPLANATION
- <Background location / audio: why, and where the user sees it>
- <Feature flags: list each gated feature; all are ON for the review account>
- <AI: provider X receives <data>; consent screen appears at <place>>
- <UGC: report via ⋯ menu, block via profile; reports are reviewed within 24h; terms accepted at sign-up>
- <Hardware / location-dependent features: demo mode at <place> or video link>

WHAT'S NEW IN THIS VERSION
- <Every new feature or behaviour change (2.3.1)>

CONTACT
<Name, phone, email reachable during review>
```

## "Metadata Rejected" vs binary rejection
- **Metadata Rejected**: fix it in App Store Connect and reply. No new build is needed.
- **Binary rejected**: needs a new build. Reply in Resolution Center first if you believe the reviewer was mistaken. Include steps and screenshots. Appeals go to the App Review Board.
