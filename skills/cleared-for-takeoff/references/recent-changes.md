# Recent changes covered (verified against developer.apple.com/news on 2026-11-18)

Look for anything **newer than the top entry** during the live check (SKILL Step 4).

| Date | Change | What to check |
|---|---|---|
| 2026-11-17 | Tax/price updates (Dec 3 2026 equalisation; California sales tax 2027) | Hardcoded prices go stale. Use StoreKit `displayPrice`. |
| 2026-11-16 → 2027-01-12 | **New age-rating content descriptors**: *Shared Location* and *Dating and Relationships*. Required for new submissions from Nov 16 2026, and for all apps by Jan 12 2027. Dating apps get a minimum 18+. Brazil uses A16/A18. | Apps that share location with other users, or dating apps, must answer these. Ask the user to confirm the age-rating questionnaire. |
| 2026-10-29 | Taiwan storefront commission 26% | — |
| **2026-10-16** | **Guidelines revision**: 1.2 (AI content creation apps count as UGC; safeguards against nonconsensual intimate imagery, including AI-generated), **2.3.14** (creative assets: product page header + search results), **2.5.19** (hidden/dormant/undocumented features; account termination), 3.1.1(a) purchase links revised, Section 5 (alternative distribution enforcement) | AI generators need 1.2 safeguards. Creative assets: no pricing or unverifiable claims, must be all-audience. Feature flags must be documented. |
| 2026-10-05 | **iPhone Duo screenshots** required for submissions from **April 2027** | Plan for the screenshot set. Note it in the report if the release is near April 2027. |
| 2026-09-16 | Subscriptions for iOS 27: Bundles & Suites, multiseat on by default. StoreKit 2 recommended. | Original StoreKit (`SKPaymentQueue`) is an INFO-level migration note. |
| 2026-09-16 | **EU alternative ATT prompt** from iOS 27.2. Only the alternative prompt is shown in DE, FR, IT, PL, RO. | ATT copy and flow may differ in the EU. Make sure tracking SDKs wait for the result. |
| 2026-09-09 | **SDK minimum: iOS 27 SDK** for uploads from **April 2027**. Social-media age-rating questions required. | Note Xcode version requirements for spring 2027 releases. |
| 2026-08-24 | Sign in with Apple relay domain `private.icloud.com` (alongside `privaterelay.appleid.com`) | Backend email-domain allowlists. |
| 2026-08-18 | EU: one set of terms from Oct 1 2026. 5% Core Technology Commission. Alternative payments. | EU-specific link-outs or payments are allowed under these terms. Don't flag them blindly. |
| 2026-08-12 | Korea: GRAC rating override. Two descriptors move to 12+. | — |
| 2026-07-09 | Age-rating questionnaire adds social-media questions (required from Sept 2026). Feeds the *Time Allowances* "Social Media" category. | Apps with a social feed must answer them. |
| 2026-06-18 | Brazil: alternative marketplaces and out-of-app payments (iOS 26.5+) | Brazil link-outs are allowed under Attachment 12. |
| 2026-06-03 | Texas SB 2420 age assurance for new accounts (from Jun 4 2026). Declared Age Range API. | Apps with age-restricted content may need Declared Age Range. |
| 2026-05-21 | Australia: 15+ → 16+. Vietnam regional ratings. | — |
| 2026-05-08 | Brazil gambling apps need an SPA betting license. Gambling sets Brazil A18. | Gambling apps: licence per storefront. |
| 2026-03-26 | **Regulated medical device declaration** for Health & Fitness / Medical apps in the EEA, UK and US (existing apps by early 2027) | Health apps must declare their medical-device status in App Store Connect. |
| 2026-03-12 | China storefront commission 25% | — |
| 2026-02-24 | Age assurance (Brazil, Australia, Singapore, Utah, Louisiana). Declared Age Range API updates. | — |
| **2026-02-06** | **Guidelines**: apps with random or anonymous chat fall under 1.2. Live text says apps used *primarily* for random/anonymous chat "do not belong on the App Store". | Anonymous chat is a high-risk category. |
| 2026-02-03 | **SDK minimum: iOS 26 SDK** for uploads since **Apr 28 2026** | An older Xcode fails at upload. |

## Long-standing upload gates (ITMS codes)

| Code | Meaning |
|---|---|
| ITMS-90683 | Missing purpose string for an API referenced in the binary |
| ITMS-91053 | Missing API declaration (required-reason API not in the privacy manifest), checked per bundle |
| ITMS-91061 | Commonly-used third-party SDK without a privacy manifest |
| ITMS-91065 | Missing signature for a commonly-used SDK binary |
| ITMS-90809 | UIWebView reference |
| ITMS-90474 / 90475 | iPad multitasking orientations / launch storyboard |
| ITMS-90717 | App Store icon has an alpha channel |
| ITMS-90022 / 90713 | Missing or incorrect icon |
| ITMS-90060 / 90058 | Invalid version or build number |
| ITMS-90355 | Extension bundle ID not prefixed by the app's |
| ITMS-90473 | Extension version mismatch (warning) |
| ITMS-90078 | Missing push entitlement (warning email) |
