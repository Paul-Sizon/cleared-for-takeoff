# secrets: hardcoded credentials
**Guidelines:** 1.6 (data security), plus general security · **Rules:** `stripe-secret`, `aws-key`, `private-key`, `openai-key`, `anthropic-key`, `github-token`, `slack-token`, `google-service-account`, `supabase-service-role`, `twilio-secret`

Rejections for secrets are rare. The real risk is **key theft**: anything in an IPA, JS bundle or Dart snapshot can be extracted with `strings` in minutes. AI keys get abused for spend within days.

## Not secrets (designed to ship)
- Firebase `AIza…` (restrict by bundle ID)
- Google Maps keys
- Stripe `pk_live_`
- RevenueCat `appl_`
- Supabase **anon** key (with RLS on)
- Sentry DSN
- Mixpanel / Amplitude tokens

## Fix
1. **Rotate the key now.** Assume it is compromised, because it has been in git history.
2. Move the call server-side (an edge function or proxy that holds the key and authenticates the user or app, e.g. with App Attest).
3. Remove it from git history if the repo is or will be public (`git filter-repo`). Rotation is still mandatory.
4. `--dart-define` / `.env` / xcconfig values are **still embedded** in the build. They only keep keys out of git.
