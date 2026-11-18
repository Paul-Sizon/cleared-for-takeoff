# payments: IAP, restore, subscription disclosure, prices, loot boxes
**Guidelines:** 3.1.1 · 3.1.2(c) · 3.1.3 · **Rules:** `no-restore`, `sub-disclosure`, `hardcoded-price`, `external-payment`, `lootbox-odds`

## Verify
- `external-payment`: decide what is sold. Physical goods, real-world services and P2P services are fine. Digital goods need IAP unless a storefront exception applies. US: links and buttons to web purchase are allowed with no entitlement since 2025. EU, Brazil and Korea have their own terms. Write the conclusion in the report.
- `no-restore`: SDK paywalls (RevenueCat Paywalls, SubscriptionStoreView with `.storeButton(.visible, for: .restorePurchases)`) may include restore. Check the config.
- `sub-disclosure`: `SubscriptionStoreView` shows the policies only if you add `.subscriptionStorePolicyDestination` or terms in App Store Connect. Remote paywalls: check every template.
- `hardcoded-price`: prices in comments, tests or marketing strings that aren't shown are not a problem.

## Fix
- **Restore:**
  - StoreKit 2: `try await AppStore.sync()`
  - RevenueCat: `Purchases.shared.restorePurchases()` / `Purchases.restorePurchases()`
  - `react-native-iap`: `getAvailablePurchases()`
  - Flutter `in_app_purchase`: `InAppPurchase.instance.restorePurchases()`
- **Paywall must show:**
  - the plan name;
  - the billed amount per period as the most prominent price (e.g. "$59.99/year"). A per-month breakdown must be smaller;
  - the trial length and the price after the trial;
  - "auto-renews unless cancelled 24h before";
  - links to Terms of Use (`https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`) and Privacy.
- **Prices:** `product.displayPrice` (SK2), `package.product.priceString` (RevenueCat), `ProductDetails.price` (Flutter).
