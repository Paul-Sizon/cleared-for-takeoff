# account-deletion: 5.1.1(v)
**Rule:** `missing`

The scanner found sign-up code (`createUser`, `signUp`, `/register`, SignUpView…) and no deletion code or copy.

## Verify
- Search the settings or profile screens yourself. The deletion entry may live in a web view or a server-driven menu. If you find a "Delete account" link that opens a web page, check that the page **completes** deletion (OK) rather than only describing a process (not OK).
- Accounts created only via Sign in with Apple still need deletion, plus token revocation.
- Apps without account creation (login with existing enterprise accounts only) are exempt.

## Fix
- Settings → Account → **Delete Account**:
  1. Explain what gets deleted.
  2. Confirm.
  3. Call the backend to delete the user and their data.
  4. Sign out.
- Firebase: `Auth.auth().currentUser?.delete()` (may need recent login) plus Firestore cleanup.
- Supabase: an edge function using the service role (server-side only) that calls `auth.admin.deleteUser`.
- Sign in with Apple: call `https://appleid.apple.com/auth/revoke` server-side with the refresh token.
- Subscriptions: tell users that deleting the account doesn't cancel the Apple subscription, and link to `https://apps.apple.com/account/subscriptions`.
