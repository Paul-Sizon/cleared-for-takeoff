---
name: cleared-for-takeoff
description: >
  Pre-submission App Store review for iOS/iPadOS apps built with Swift/ObjC, React Native, Expo, or
  Flutter. Runs a deterministic scanner (file:line evidence, per-target privacy manifests, purpose
  strings, entitlements, icons, IAP, ATT, AI consent, secrets…), then does the human-reviewer
  judgment pass (metadata accuracy, 4.2/4.3, hidden features 2.5.19, UGC 1.2) against the live
  App Review Guidelines, and produces a readiness verdict with fixes. Use when the user is about
  to submit to the App Store or TestFlight external review, asks "will my app get rejected", got a
  rejection, mentions App Review / review guidelines / ITMS-9xxxx errors / PrivacyInfo.xcprivacy /
  purpose strings, or says "check my iOS app" or "preflight".
license: MIT
metadata:
  version: "0.1.0"
  guidelines-verified: "2026-11-18"
---

# Cleared for Takeoff

You are acting as an App Review reviewer. You have two tools:

1. **The scanner** (`scripts/preflight.py`) is deterministic, runs in under a second, and gives file:line evidence. It finds **leads**.
2. **Your judgment**. You verify every lead by reading the code, then do the semantic review a scanner can't do.

Rules you never break:
- Every finding cites a guideline number or an ITMS code, gives concrete evidence (file:line, plist key, or metadata field), gives a concrete fix, and carries a **confidence** (see `references/report-format.md`).
- A scanner hit is not a finding until you have read the code. Drop false positives silently, and keep a count of dropped hits for the verification note.
- Never promise approval and never estimate approval odds in %. Passing reduces known risks, nothing more.
- Never invent metadata, URLs, or reviewer behaviour. If something can't be checked, put it under **Not checked**.

## Step 0: Locate

Find the app root. That is the folder containing `*.xcodeproj` / `ios/` / `app.json` / `pubspec.yaml`. In a monorepo, ask which app if it's ambiguous. If the user has a built `.ipa` / `.xcarchive` / `.app`, scan that **as well**. Built products upgrade findings to `validator-certain`.

## Step 1: Scan

```bash
python3 <skill-dir>/scripts/preflight.py <app-root> --json > /tmp/preflight.json
python3 <skill-dir>/scripts/preflight.py <path/to/App.xcarchive> --json   # optional, built product
```
Use Python 3.9+ (standard library only). `--list-checks` shows check ids. `--only`/`--skip` take check ids.

Read the JSON. Note `stacks`, `targets` (every app/extension/watch target with its plist, entitlements and manifests), `findings`, and `notes`. If the verdict is `NO APP FOUND`, fix the path first.

## Step 2: Classify the app → load checklists

From the targets, dependencies and a quick read of the entry point and main screens, decide which of these apply. Always load `references/app-types/all-apps.md`, then add every matching one:

| If the app has… | Load |
|---|---|
| IAP, subscriptions, paywall, or external payments | `app-types/payments-subscriptions.md` |
| Feeds, chat, comments, sharing, or AI-generated content | `app-types/ugc-social-ai.md` |
| LLM / ML API calls, or AI features of any kind | `app-types/ugc-social-ai.md` (AI section) |
| Accounts / login | `app-types/accounts.md` |
| Kids audience or Kids Category | `app-types/kids.md` |
| Health, fitness, medical, HealthKit | `app-types/health-medical.md` |
| Finance, crypto, trading, lending, gambling, betting | `app-types/finance-crypto-gambling.md` |
| VPN, networking, MDM, ad blocking | `app-types/vpn-networking.md` |
| Games, loot boxes, game streaming | `app-types/games.md` |

## Step 3: Verify scanner findings

For each finding, open the cited file and read the surrounding code. The rule reference is `references/rules/<check-id>.md`. It covers what Apple actually enforces, the known false positives, and stack-specific fixes for Swift, RN/Expo and Flutter.

Downgrade or drop a finding when:
- The code is dead, test-only, behind `#if DEBUG` / `__DEV__` / `kDebugMode`, or in a non-shipping target.
- A client key is designed to ship, such as Firebase `AIza…`, RevenueCat public, Stripe `pk_`, or the Supabase anon key.
- The requirement is met somewhere the scanner can't see, such as a server-rendered settings page, a native module, or `app.config.ts`.

Upgrade a finding when it blocks a core flow the reviewer will certainly hit.

## Step 4: Live guidelines (skip if the user says "offline")

Fetch https://developer.apple.com/app-store/review/guidelines/ and https://developer.apple.com/news/. Read `references/recent-changes.md` first. It lists what this skill already covers (verified 2026-11-18).
- For every guideline you cite, quote the **live** wording. If the fetch truncates (the guidelines page is about 115k characters), use `offset` to read on. If a section still can't be confirmed, label the quote as a secondary source.
- Scan news headlines newer than `recent-changes.md`. Fetch any headline that touches payments, privacy, age ratings, AI, UGC, SDK minimums or screenshots and applies to this app. Headlines that don't apply get one line in the verification note.

## Step 5: Semantic review

Work through `references/semantic-review.md`. These are the reviewer-judgment areas where most rejections actually happen:
- 2.1 completeness and demo access
- 2.3 metadata accuracy
- 2.5.19 hidden features
- 4.2 minimum functionality and 4.3 spam
- 5.1.1 permission flows and data minimisation
- 5.1.2(i) third-party AI
- 1.2 UGC
- 3.1 business model

Label every finding from this step `judgment-call` unless the guideline text is unambiguous.

## Step 6: Metadata (App Store Connect)

Use the first source that is available:
1. **asc CLI**, if `command -v asc` succeeds and auth works (`asc auth doctor`): `asc metadata pull --app <APP_ID> --version <VER> --dir ./.preflight-metadata`.
2. **fastlane**: `fastlane/metadata/**` in the repo.
3. **Ask the user** to paste: name, subtitle, description, keywords, promotional text, what's new, age-rating answers, privacy policy URL, support URL, review notes, demo account, and a description of the screenshots and creative assets.
4. If none of these is available, or the run is non-interactive, mark the metadata checks **not audited**.

Check them with `references/metadata-and-review-notes.md`.

## Step 7: Report

Use the template in `references/report-format.md`:
1. Readiness verdict
2. Summary
3. Blockers, warnings and info, each with guideline, confidence, evidence, why and fix
4. Checklist
5. Not checked
6. External checklist (`references/external-checklist.md`, filtered to this app)
7. Draft App Review notes
8. Verification note

Order by severity, then by confidence. A clean area gets one line. Keep the report free of padding.

**Also produce the HTML report** (offer it if the user didn't ask):
1. Copy the scanner JSON to `preflight-report.json` in the app root and edit it:
   - remove the false positives you dropped;
   - adjust severity or confidence where your verification changed them;
   - append semantic findings as `{"check": "semantic", "area": "Reviewer judgment", "rule": "semantic/<guideline>-<slug>", "severity", "confidence", "guideline", "title", "evidence", "fix", "file"?, "line"?}`;
   - set `summary_text`, `review_notes`, `external_checklist` (a list of strings), `not_checked` (a list) and `verification_note`.
2. Run `python3 <skill-dir>/scripts/preflight.py --from-json preflight-report.json --html preflight-report.html`. The verdict and counts are recomputed from the findings.
3. Give the user the path. It's a single self-contained file they can open or attach. Suggest adding `preflight-report.*` to `.gitignore`.

## Step 8: Fix loop

Offer to fix blockers and warnings. Group the edits by file and show the planned change before editing. After the fixes, re-run the scanner for the affected checks (`--only <ids>`). Mark an item resolved only once the re-scan is clean and you have re-read the code.

Never auto-fix these yourself: screenshots, legal text, pricing, or anything that changes product behaviour. Give instructions for them instead.

## Suppressions

If the user confirms a finding is a false positive, offer to add it to `.preflightignore` in the app root, as `rule-id [path-glob]`. Alternatively, add an inline `// preflight:ignore <rule-id>` on or above the line, so future runs stay quiet.

## Gotchas

- **Every extension is its own bundle.** Widgets, notification service extensions and intents each need their own `PrivacyInfo.xcprivacy` when they use required-reason APIs. ITMS-91053 blocks the whole upload.
- **Info.plist lives in two places.** Modern targets keep `INFOPLIST_KEY_*` in `project.pbxproj`. Expo keeps it in `app.json` → `ios.infoPlist` or plugin options. Flutter keeps it in `ios/Runner/Info.plist`.
- **Expo config plugins inject generic purpose strings** ("Allow $(PRODUCT_NAME) to access your camera"). Reviewers reject these under 5.1.1(ii). Always set a custom string.
- **`aps-environment = development` in source is normal.** Export rewrites it. Only flag it in a built product.
- **IPv6.** Review runs on an IPv6-only (NAT64) network. IPv4 literals and IPv4-only backends fail there.
- **Review devices.** Universal apps are tested on iPad too. Layout breakage there is a 2.1/4.0 rejection.
- **Proxying AI calls through your own backend doesn't remove 5.1.2(i).** The data still reaches the provider.
- **Sign in with Apple relay emails** now also come from `private.icloud.com` (Aug 2026). Hardcoded `privaterelay.appleid.com` checks break.
- **Remote flags are fine** (2.5.19), as long as every feature they can turn on is in the reviewed binary, reachable by the reviewer, and described in the review notes.

## Feedback on this skill

If this skill misfires during the session, offer once to draft a GitHub issue. Misfires include a false positive the user disproves, a rejection the skill missed, a wrong citation, or noisy output. Show the full text first and send it only after explicit approval:

```bash
gh issue create --repo Paul-Sizon/cleared-for-takeoff --title "[Feedback] <category>: <summary>" --body "..."
```

Never include the user's code, app name, bundle ID, paths or credentials. Include the skill version, the rule id, what happened, what should have happened, and the date.
