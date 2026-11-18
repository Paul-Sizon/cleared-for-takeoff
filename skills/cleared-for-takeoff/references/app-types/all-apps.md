# Every app

| # | Check | Guideline | Scanner |
|---|---|---|---|
| 1 | No crashes or broken flows on a fresh install, on both iPhone and iPad (if universal) | 2.1 | – (manual) |
| 2 | No placeholder, "coming soon", lorem or beta copy | 2.1, 2.2 | `content` |
| 3 | Every protected API has a specific purpose string | 5.1.1(ii), ITMS-90683 | `privacy-strings` |
| 4 | A privacy manifest in **every** bundle that uses required-reason APIs | ITMS-91053 | `privacy-manifest` |
| 5 | Listed third-party SDKs ship manifests and signatures | ITMS-91061/91065 | `dependencies` |
| 6 | Launch screen, a 1024 icon without alpha, iPad orientations | ITMS-90475/90717/90474 | `assets` |
| 7 | Valid version and build numbers. Extension IDs prefixed and versions matched | ITMS-90060/90355/90473 | `build-config` |
| 8 | ATS not globally disabled. No IPv4 literals. No cleartext URLs | 2.5.5, ATS | `networking` |
| 9 | Only public APIs. No UIWebView. No downloaded executable code | 2.5.1, 2.5.2 | `code` |
| 10 | Background modes are justified and used | 2.5.4 | `entitlements` |
| 11 | No hidden, dormant or reviewer-aware features | 2.5.19 | `hidden-features` |
| 12 | Privacy policy in App Store Connect **and** in the app | 5.1.1(i) | semantic |
| 13 | Metadata matches the app; no price words or other platforms | 2.3.x | metadata |
| 14 | Age-rating questionnaire is current (social media, Shared Location, Dating) | 2.3.6 | metadata |
| 15 | Review notes cover demo access, flags and new features | 2.1, 2.3.1 | metadata |
| 16 | Native value beyond a website; not a clone | 4.2, 4.3 | semantic |
| 17 | System review prompt only | 5.6.1 | `code` |
| 18 | No Apple trademarks in the name | 5.2.5 | `build-config` |
| 19 | No secrets in the bundle | 1.6 | `secrets` |
| 20 | Export compliance answered | — | `export-compliance` |
