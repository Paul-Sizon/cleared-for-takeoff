# Semantic review: what a scanner can't decide

Read the code, the copy and the metadata. Label findings `judgment-call` unless the guideline is unambiguous. For each area: ask the question, look in the listed places, flag when the condition holds.

## 2.1 App completeness: the #1 rejection cluster
- **Can a reviewer reach every feature?** If there's a login wall, a demo account must be in the review notes, with no 2FA to a phone you control, no expiring invite codes, and no geo-locks. Hardware-dependent features need a demo mode or a video.
- **Empty states.** A fresh install with no data must still show a working app. Watch for an empty feed, a "No items" dead end, or a backend that is seeded only for you.
- **Server dependence.** Features that need a backend: is it production-ready, IPv6-reachable, and serving the reviewed region?
- **Placeholder content, "coming soon" badges, disabled buttons.** Hide unfinished features. Don't ship them greyed out.
- **Crash-prone patterns.** Force unwraps on network data, `fatalError` in reachable paths, Dart `!` on API JSON, RN unhandled promise rejections in startup code.

## 2.3 Metadata accuracy
- Does every feature claimed in the description or screenshots exist in this build?
- Screenshots must show the app in use, not just splash or marketing art. Since 2.3.14 (Oct 2026), creative assets (product page header, search-result assets) must relate to the app or brand, carry no pricing or discounts, make no unverifiable claims ("#1", "best"), and be appropriate for all audiences.
- No price words ("Free", "Sale") in the name, subtitle, keywords, screenshots or previews. That includes text visible inside captured screens (2.3.7).
- No other platform names (Android, Google Play) and no competitor names in keywords (2.3.7, 2.3.10).
- The name is 30 characters or fewer and contains no keyword stuffing or Apple trademarks used as part of the name (5.2.5). "for iPhone" belongs in the description only.
- The age rating matches the content. Check against the Nov 2026 descriptors (Shared Location, Dating), the social-media questions, and gambling, medical and UGC.

## 2.5.19 Hidden, dormant or undocumented features
- Look for any code path that shows different features by date, region, IP, sandbox receipt, TestFlight, a reviewer account, or a remote flag.
- Remote **data** changes (copy, layout order, prices shown) for code that is in the binary are generally fine. A **feature** that only exists after a server switch is not. Note that this distinction is an inference from Apple's announcement, so label it.
- Obfuscated entry points (hidden gestures, secret codes) unlocking functionality count as violations.
- Every flag-gated feature should be listed in the review notes.

## 4.2 Minimum functionality / 4.3 Spam
- **Web wrapper test:** is the app mostly a `WKWebView` / `react-native-webview` / `webview_flutter` of a website? What native value is added: offline use, push, device features, native navigation? Thin wrappers get rejected under 4.2.
- **Saturated categories** that Apple calls out (4.3): flashlights, fart/sound boards, wallpapers, simple timers, fortune telling, dating clones, drinking games, horoscopes. State plainly what differentiates this app. If the honest answer is "little", say so.
- Multiple near-identical apps from the same developer, or template/white-label clones, fall under 4.3(a).
- A single-feature app ("just a list") with no persistence or utility is a 4.2 risk.

## 5.1.1 Permissions and data
- **Request timing:** ask for a permission in context, when the feature is used. A wall of permission prompts at launch is a common rejection.
- **Pre-permission screens** may have one neutral button ("Continue" / "Next") that leads to the system prompt. No "Allow" / "Enable" wording, and no Cancel or Close that skips the system prompt (5.1.1(iv)).
- **Forced permissions:** the app must stay usable if the user denies a non-essential permission.
- **Data minimisation:** don't require personal data (phone, birthday, gender) that the feature doesn't need. Don't force account creation for features that work without one (5.1.1(v)).
- **Privacy policy:** linked in App Store Connect **and** reachable in the app. It must name what is collected and who receives it.

## 5.1.2(i) Third-party AI
- Does user content (prompts, chat, photos, voice, documents, health data) reach an external model provider, directly or through your backend?
- If it does: before the first request, show a consent screen that names the provider and the data types and has an affirmative action. Make consent withdrawable. Name the provider in the privacy policy and in the App Privacy "Data Shared" answers.
- On-device models (Apple Foundation Models, Core ML) and your own self-hosted models are not third-party. 5.1.1 consent still applies.

## 1.2 UGC (social, chat, comments, AI content creation)
- Filtering of objectionable material, report with a timely response (act within 24h), block abusive users, published contact info, and an unchecked terms agreement (EULA with zero tolerance) shown before posting.
- AI generators: prevent nonconsensual intimate imagery (Oct 2026), and filter prompts and outputs.
- Random or anonymous chat is high risk (Feb 2026 clarification).
- Reviewers may ask for a device screen recording of terms acceptance, reporting and blocking. Suggest preparing one.

## 3.1 Business model
- What is sold? Digital content, features or subscriptions need IAP (3.1.1), unless an exception applies: reader apps 3.1.3(a), multiplatform 3.1.3(b), person-to-person services 3.1.3(d), physical goods 3.1.3(e), or storefront terms (US link-outs, EU, Brazil, Korea).
- Subscription screens must show the price per period prominently, plus the trial terms and auto-renewal. Free trials must say what is charged afterwards (3.1.2).
- Unlocking features through rewards for actions such as reviews, ratings, social shares or watching ads to unlock core features is a common 3.1 / 5.6 trap.
- Apps that are only a paywall on first launch, with no visible value, are a 2.1/3.1.2 judgment risk. Make sure there is a dismiss path where appropriate.

## 4.8 Login
- Check which login methods exist. If any third-party or social login sets up the primary account, there must be an equivalent privacy-focused option (Sign in with Apple is the simplest).
- Exempt: apps that use only your own accounts, education/enterprise apps, government ID, and clients of a specific third-party service.

## Accessibility and quality (not a rejection by itself, but reviewers notice)
- Dynamic Type clipping, missing labels on icon-only buttons, hardcoded colours that break in Dark Mode, and broken iPad layouts.
