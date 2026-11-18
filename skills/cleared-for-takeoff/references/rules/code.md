# code: APIs, dynamic code, quitting, review prompts
**Rules:** `uiwebview`, `private-api`, `dlopen`, `eval`, `js-eval-native`, `deprecated`, `exit`, `ota`, `custom-review-prompt`, `review-gating`

- **UIWebView (ITMS-90809):** rejected at upload, even when referenced only by an SDK. Find the source with `grep -rl UIWebView Pods/ node_modules/*/ios` and update the SDK.
- **Private API (2.5.1):** Apple's scanner matches **selector names**. A method of yours named like a private selector (e.g. `_setBackgroundColor:`) can trigger a false positive. Rename it.
- **Dynamic code (2.5.2):** apps may not download or execute code that adds or changes features. JS run in a WebView or JSContext, or OTA updates (expo-updates, CodePush, Shorebird), are allowed for bug fixes and content that doesn't change the app's primary purpose or add features not in the review build (DPLA 3.3.1(b)).
- **Quitting (`exit(0)`, `SystemNavigator.pop`, `BackHandler.exitApp`):** looks like a crash to reviewers. iOS apps never quit themselves.
- **Review prompts (5.6.1):** use only the system API (`requestReview`, `expo-store-review`, `in_app_review`). A custom "Rate us" dialog is not allowed. A user-initiated button linking to `…?action=write-review` is fine. "Do you enjoy the app?" pre-filters that route unhappy users elsewhere count as manipulation.
- **Deprecated APIs:** not a rejection by themselves, but `UIAlertView`, AddressBook and AssetsLibrary signal an unmaintained app. Migrate them.
