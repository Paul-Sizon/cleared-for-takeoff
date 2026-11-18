# export-compliance
**Rule:** `missing` (INFO)

If `ITSAppUsesNonExemptEncryption` is absent, App Store Connect asks the encryption question for every build, and the build sits in *Missing Compliance*. It isn't a rejection, but it blocks TestFlight and submission until someone answers.

- Only HTTPS, Apple CryptoKit / CommonCrypto for standard purposes, or encryption exempt under category 5 part 2 → set `ITSAppUsesNonExemptEncryption = NO`. Expo: `ios.config.usesNonExemptEncryption: false`.
- Proprietary or non-standard encryption, or E2E messaging with custom crypto → `YES`. You may need an export compliance document or an ERN (France distribution needs extra docs).
- Crypto wallets and E2E messengers: judge case by case. Don't blindly set `NO`.
