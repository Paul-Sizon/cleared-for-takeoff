# hidden-features: 2.5.19
**Rules:** `review-detection` (BLOCKER), `env-detection`, `remote-flags`

Live text: *"Don't include any hidden, dormant, or undocumented features in your app; your app's functionality should be clear to end users and App Review. Attempting to hide undocumented features in your app binary, such as through code obfuscation or other methods, is grounds for removal of your app from the App Store and termination of your developer account."*

## Verify
- `review-detection`: any logic that identifies reviewers (by account, region such as Cupertino, IP ranges, sandbox receipts, device model or date) and changes features is the most serious finding this skill can report. Confirm it before reporting. `isReviewMode` might be your own "review screen" feature. If confirmed, the risk is **account termination**, not just a rejection.
- `env-detection`: using the sandbox or TestFlight environment for receipt validation, analytics or a debug banner is fine. Using it to hide payments, content or features is not.
- `remote-flags`: list the flags and their defaults. Every feature a flag can enable must be in this binary, reachable by the reviewer, and described in the review notes. Server-driven **data** (copy, prices, ordering) is generally fine. A server-only **feature switch** for unreviewed functionality is not. That distinction is an inference from Apple's text; label it so.

## Fix
- Remove reviewer detection.
- Turn flag-gated features ON for the review account, or describe how to enable them.
- Describe every feature in the review notes ("What's new" plus "Features behind flags").
