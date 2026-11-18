# Payments, IAP and subscriptions (3.1)

**What must use IAP (3.1.1):** digital content, premium features, subscriptions, in-app currency, ad removal, and tips to the developer.

**Exceptions:**
- 3.1.3(a) reader apps, with the External Link Account entitlement
- 3.1.3(b) multiplatform services, where content bought elsewhere is accessible
- 3.1.3(c) enterprise services
- 3.1.3(d) person-to-person real-time services (tutoring, fitness coaching)
- 3.1.3(e) physical goods and real-world services
- 3.1.3(f) free stand-alone companion apps
- 3.1.3(g) advertising management
- Storefront terms: US (buttons and links to web purchase allowed), EU (Attachment 14, from Oct 1 2026), Brazil (Attachment 12), Korea, Japan (MSCA)

**Checklist:**
- [ ] Restore Purchases is visible on the paywall and in settings (3.1.1). Scanner: `payments/no-restore`.
- [ ] Paywall shows: title, duration, the **billed amount as the most prominent price**, trial length and what happens after it, and auto-renewal (3.1.2(c)).
- [ ] Functional links to Terms of Use (the Apple standard EULA is OK) and Privacy Policy on the paywall, and in the App Store description or EULA field. Scanner: `payments/sub-disclosure`.
- [ ] Prices come from StoreKit or the SDK, never hardcoded. Scanner: `payments/hardcoded-price`.
- [ ] Subscriptions give ongoing value. Don't make a one-off feature a subscription.
- [ ] Credits and currency never expire (3.1.1).
- [ ] Loot boxes disclose odds before purchase (3.1.1). Scanner: `payments/lootbox-odds`.
- [ ] No unlocking of features for reviews, ratings or social shares (3.1.1 / 5.6).
- [ ] Free trial via a non-subscription IAP is named "XX-day Trial" and states the charge afterwards (3.1.2).
- [ ] IAP products are attached to the version in App Store Connect. First IAPs must be submitted with a binary.
- [ ] Group purchases and multiseat (iOS 27): if enabled, test them.
- [ ] Apps that only show a paywall: make sure the reviewer can see what they'd pay for (screenshots or demo content), or provide a promo code in the review notes.

**RevenueCat / Adapty / Superwall:** remote paywalls are fine, but every paywall variant must meet 3.1.2(c), and the reviewed variant must be the one served to the reviewer.
