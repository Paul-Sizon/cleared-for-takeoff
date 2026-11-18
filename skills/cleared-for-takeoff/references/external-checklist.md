# External verification checklist

These are things the code can't prove. Include in the report **only the sections that apply** to this app. Fill in the real URLs, SDKs and flows you discovered.

## Always
- [ ] Archive uses the **Release** configuration and was built with the current minimum SDK: the iOS 26 SDK today, the iOS 27 SDK from April 2027.
- [ ] Fresh install on a **real device**: launch, onboarding, core flow, no crash.
- [ ] Tested on **iPad** if the app is universal, including rotation and split view.
- [ ] Tested on an **IPv6-only network**: macOS Internet Sharing → "Create NAT64 Network".
- [ ] Privacy policy and support URLs load (not 404 or login-gated) and are app-specific.
- [ ] App Privacy answers in App Store Connect match the SDKs in the build.
- [ ] The age-rating questionnaire is answered, including the social-media questions and the Nov 2026 descriptors.
- [ ] Export compliance is answered (or `ITSAppUsesNonExemptEncryption` is set).

## Accounts
- [ ] The demo account works, has no 2FA or expiring code, and contains sample data.
- [ ] Account deletion completes end-to-end. Sign in with Apple token revocation is called.
- [ ] Sign in with Apple works with a Hide-My-Email relay address (`privaterelay.appleid.com` **and** `private.icloud.com`).

## Payments
- [ ] IAP products are "Ready to Submit" and attached to this version (first IAPs must be submitted **with** the binary).
- [ ] Purchase and restore work in sandbox on a device. Prices come from StoreKit.
- [ ] The paywall shows the price per period, trial terms, and working Terms of Use and Privacy links.
- [ ] Paid Applications Agreement and banking/tax are active.

## Push / background
- [ ] Production APNs key or certificate is configured on the server. Push arrives on a TestFlight build.
- [ ] Every background mode can be demonstrated, and is explained in the review notes.

## Links & deep links
- [ ] Universal Links: `apple-app-site-association` served over HTTPS without redirects; associated domains match.
- [ ] Every in-app link (terms, help, social) opens.

## Backend
- [ ] Production backend is up and seeded. Feature flags are ON for review. Geo-restrictions don't block Cupertino or other reviewer regions.
- [ ] Firebase/Supabase security rules are not left in test mode (`allow read, write: if true`).

## AI / UGC
- [ ] The AI consent screen appears before the first request on a fresh install.
- [ ] Report, block and terms flows work. Optionally record a device video in case the reviewer asks.

## Release timing
- [ ] Avoid submitting right before the US holiday review slowdown (late December). Use phased release for risky updates.
