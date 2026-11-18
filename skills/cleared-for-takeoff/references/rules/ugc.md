# ugc: user-generated content safeguards (1.2)
**Rule:** `safeguards` (judgment-call)

The scanner sees chat or social SDKs, or post/comment/message code, and looks for report, block and terms wording. It's heuristic. Read `app-types/ugc-social-ai.md` for the full list.

## Verify
- Does user content become visible to **other users**? Private notes are not UGC. Shared albums, comments, DMs and AI-generated images shared publicly are.
- Reporting must exist **on the content itself** (⋯ menu → Report). A support email alone is not enough.
- Blocking must hide the blocked user's content immediately.
- Terms acceptance must come before posting, use an unchecked box or explicit button, and include zero-tolerance language.
- Filtering: server-side moderation (OpenAI moderation, AWS Rekognition, Hive, or a keyword list) is acceptable. Describe it in the review notes.

## Fix
Add the report and block actions, the terms gate and the moderation pipeline. Document the 24h response process. Record a short device video of the flows for review.
