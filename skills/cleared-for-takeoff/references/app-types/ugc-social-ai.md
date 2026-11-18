# UGC, social, chat and AI apps (1.2, 5.1.2(i))

## UGC / social / chat (1.2)
Includes social networks, comments, reviews, chat, forums, dating, file sharing, and **AI content creation apps** (Oct 2026).
- [ ] Filtering of objectionable material before it is posted (text filters, image moderation).
- [ ] Report content and users, with a timely response. Act on reports within 24h by removing the content and ejecting the offender.
- [ ] Block users. Blocked users' content disappears immediately, and blocking notifies the developer.
- [ ] Published contact information, in the app and on the support URL.
- [ ] Terms or EULA stating **zero tolerance** for objectionable content and abusive users, accepted via an **unchecked** checkbox or an explicit button **before** first posting or login.
- [ ] Safeguards against nonconsensual intimate imagery, including AI-generated imagery (Oct 2026).
- [ ] Random or anonymous chat is in 1.2 scope (Feb 2026). Apps used *primarily* for it don't belong on the store.
- [ ] Age rating: the UGC and social-media questions are answered. Dating → 18+ (Nov 2026).
- [ ] Prepare a device screen recording of terms acceptance, reporting and blocking. Reviewers ask for it.

## AI features
- [ ] **5.1.2(i)**: if personal data (prompts, chats, photos, voice, documents) goes to a third-party AI, directly or via your backend, then before the first request:
  - name the provider and the data types sent;
  - get an affirmative opt-in;
  - make it withdrawable in Settings;
  - name the provider in the privacy policy and in the App Privacy "Data Shared" answers.
  Scanner: `ai-consent`.
- [ ] AI generators (image, video, text) count as UGC. They need prompt and output filtering, reporting, and NCII prevention.
- [ ] Age rating reflects what the model can generate. Chatbots usually need a higher rating unless strictly filtered.
- [ ] No impersonation of real people. Don't present AI output as human or authoritative medical, legal or financial advice without disclaimers (1.4.1).
- [ ] China storefront: a generative AI app needs a CAC filing number, and AI brand terms (ChatGPT, Gemini…) are not allowed in metadata in any locale shown in China.
- [ ] Metadata must not use other AI brands in ways implying affiliation (e.g. "ChatGPT" in the name) (5.2.1, 2.3.7).
- [ ] Apple Foundation Models (on-device) avoids 5.1.2(i) third-party sharing.
