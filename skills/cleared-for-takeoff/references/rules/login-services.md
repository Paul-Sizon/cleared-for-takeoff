# login-services: 4.8 Sign in with Apple or equivalent
**Rule:** `no-equivalent`

The scanner detects Google, Facebook, X, GitHub, Microsoft, LINE or Kakao login without Sign in with Apple.

## Verify
- Is the social login used for the **primary account**? If Google sign-in only connects Google Drive for import, 4.8 doesn't apply.
- Exemptions:
  - apps using only your own company's accounts;
  - education or enterprise apps that require existing accounts;
  - government or industry citizen ID;
  - a client for a specific third-party service (a Gmail client needs Google login);
  - alternative-marketplace login.
- An "equivalent" option other than Sign in with Apple must limit data to name and email, offer a private email, and do no ad tracking without consent. Most custom options fail this. Email/password is **not** a login *service*, so it doesn't count.

## Fix
- **Swift:** `SignInWithAppleButton` (SwiftUI) or `ASAuthorizationAppleIDProvider`, plus the capability.
- **Expo:** `expo-apple-authentication`, plus `"ios": {"usesAppleSignIn": true}`.
- **RN:** `@invertase/react-native-apple-authentication`.
- **Flutter:** `sign_in_with_apple`.
- **Firebase/Supabase:** enable the Apple provider and configure the Services ID and key.
- Show the button with the same prominence as the other options. Handle the private relay email, and support **both** relay domains.
