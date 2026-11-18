# Accounts and login (4.8, 5.1.1(v))

- [ ] **Account deletion in the app** (5.1.1(v)). It must be easy to find (Settings → Account) and must delete the account and its associated data. It can't just deactivate. A link straight to a web page that completes deletion is OK, but a page that only explains how to email support is not. Regulated industries (banking, health) may require extra steps; explain them in the app. Scanner: `account-deletion`.
- [ ] **Sign in with Apple token revocation** on deletion, via the REST `/auth/revoke` endpoint.
- [ ] **4.8**: if a third-party or social login (Google, Facebook, X, LinkedIn, Amazon, WeChat…) sets up the **primary** account, also offer an equivalent option that limits data to name and email, lets users hide their email, and doesn't track for ads without consent. Sign in with Apple satisfies this. Scanner: `login-services`.
- [ ] Don't require login for features that don't need an account (5.1.1(v)). Let users browse first where possible.
- [ ] No mandatory personal data beyond what the feature needs (5.1.1(iii)).
- [ ] The demo account is in the review notes, with no 2FA to your phone and with data loaded.
- [ ] Accept relay email domains `privaterelay.appleid.com` **and** `private.icloud.com` (Aug 2026).
- [ ] Sign in with Apple button follows the HIG (style, size, label). Don't hide it below the other options.
- [ ] Password reset works, and support contact is reachable from the login screen.
