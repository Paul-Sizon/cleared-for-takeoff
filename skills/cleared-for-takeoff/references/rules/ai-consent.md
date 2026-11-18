# ai-consent: personal data to third-party AI (5.1.2(i))
**Rules:** `missing`, `verify`

Live text: *"You must clearly disclose where personal data will be shared with third parties, including with third-party AI, and obtain explicit permission before doing so."*

## Scope
| Setup | Third-party AI? |
|---|---|
| App calls OpenAI, Gemini, Anthropic, ElevenLabs, Deepgram… directly | Yes |
| App → your backend → AI provider | **Yes** (a proxy doesn't change the recipient) |
| Firebase AI Logic / Vertex AI | Yes |
| Apple Foundation Models / Core ML on device | No |
| Your own self-hosted model | Not third-party (5.1.1 still applies) |

"Personal data" includes prompts and chat text, voice recordings, photos, documents, health data, and anything identifying.

## Verify
- Find where the first AI request can happen on a fresh install. Is a consent screen guaranteed before it?
- A consent screen that is skippable, pre-checked, or hidden in the ToS fails.
- Also check: the hardcoded provider API key in the client (`secrets`) is a security issue and allows key abuse.

## Fix
1. Show a consent sheet before the first request: *"To transcribe your workouts, <App> sends your voice recordings to **OpenAI**. OpenAI processes them under its privacy policy. [Allow] [Not now]"*.
2. Persist the choice. Check it before every call. If consent is declined, the feature is off and the rest of the app still works.
3. Add a Settings toggle to withdraw consent.
4. Name the provider and data types in the privacy policy and in the App Privacy "Data Shared" answers.
5. Mention the provider, the data and the consent location in the review notes.
6. Move API keys to a server and proxy requests. The proxy still requires consent.
