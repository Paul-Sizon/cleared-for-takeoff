# Report format

## Severity: what happens if this ships as-is

| Severity | Meaning |
|---|---|
| **BLOCKER** | Upload validation rejects the build, or App Review rejects it with high likelihood. |
| **WARNING** | Commonly rejected, or likely to cause a resubmission. Fix before submitting. |
| **INFO** | Best practice, or something to verify by hand. Not a rejection on its own. |

## Confidence: how sure we are

Use exactly these levels:

- **validator-certain**: Apple's automated upload/App Store Connect validation blocks this deterministically, **and** the evidence comes from a built product (`.app` / `.ipa` / `.xcarchive`). A source-only scan never reaches this level.
- **review-risk (validator-blocking if shipped as-is; needs build verification)**: the same mechanical gate, but the evidence is source or config. Conditional compilation, excluded files, or build-time plugins could change the outcome. The scanner reports this as `validator-blocking`.
- **review-risk**: a pattern human reviewers reject often, backed by guideline text and evidence in the code.
- **judgment-call**: a semantic assessment where a reasonable reviewer could go either way. Examples: differentiation (4.3), metadata accuracy, copy quality, whether data is "personal".

## Verdict

| Verdict | When |
|---|---|
| **NOT READY** | 1 or more blockers remain after verification |
| **LIKELY READY** | 0 blockers, 1 or more warnings |
| **READY TO SUBMIT** | 0 blockers, 0 warnings after semantic review. Still state "not a guarantee". |

## Priority when time is short

The ranking below is an editorial heuristic. Apple publishes only section-level counts (Transparency Report 2025: about 23% of 9.1M submissions were rejected; Performance §2 had the most rejections, then Legal §5, Design §4, Business §3, Safety §1). Never cite per-guideline percentages. Every listicle that claims them is unsourced.

1. **2.1 completeness**: crashes, broken flows, placeholder content, missing demo account.
2. **Privacy (5.1.1 / 5.1.2)**: purpose strings, privacy manifests, account deletion, ATT, AI sharing.
3. **2.3 metadata**: screenshots, description vs reality, pricing words, age rating.
4. **4.2 / 4.3**: thin apps, web wrappers, template clones.
5. **3.1 payments**: IAP for digital goods, restore, subscription disclosure.
6. **4.8 login**, **1.2 UGC**, **2.5.x software requirements**.

## Template

```markdown
# Cleared for Takeoff: <App name> <version> (<stacks>)

**Readiness: NOT READY**. 2 blockers must be fixed before submission.
_Not a guarantee of approval. Covers what code, config and provided metadata can show._

## Summary
<2–3 sentences: what the app is, its classification (accounts, IAP, UGC, AI…), and the overall risk.>
Top issues: 1) … 2) … 3) …

## Blockers
### [B1] Widget extension has no privacy manifest
- **Guideline:** ITMS-91053 (upload validation)
- **Confidence:** review-risk (validator-blocking if shipped as-is; needs build verification)
- **Evidence:** `StatsWidget/Provider.swift:14` reads `UserDefaults(suiteName:)`; target StatsWidget has no PrivacyInfo.xcprivacy
- **Why:** each bundle must declare its own required-reason API use; the upload is rejected.
- **Fix:** add PrivacyInfo.xcprivacy to the StatsWidget target with NSPrivacyAccessedAPICategoryUserDefaults → CA92.1 (or 1C8F.1 for App Group).

## Warnings
…same shape…

## Info
- one line each

## Checklist
✓ Purpose strings · ✗ Privacy manifests (1) · ✓ Entitlements · … (one line per area; clean areas = ✓)

## Not checked
Runtime crashes, broken links, live server content, IAP sandbox behaviour, push delivery, OAuth flows,
anything behind remote config, screenshots (unless described), App Privacy answers in App Store Connect.

## Before you press Submit
<filtered items from external-checklist.md>

## Draft App Review notes
<from metadata-and-review-notes.md template, filled with what you learned>

## Verification note
Guidelines checked against the live page on <date>; sections not confirmed: <…>. Apple news scanned
through <date>; relevant: <…>. Scanner: <n> findings, <k> dropped as false positives after reading code.
```
