"""Payments: IAP vs external payments (3.1.1/3.1.3), restore (3.1.1), subscription disclosure (3.1.2),
hardcoded prices, loot box odds."""
from __future__ import annotations

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, WARNING
from . import check, make

F = make("payments")

IAP_CODE = (r"\bProduct\.products\(|\bSKProductsRequest\b|\bSKPaymentQueue\b|\.purchase\(\)|\bSubscriptionStoreView\b|"
            r"\bStoreView\b|\bProductView\b|Purchases\.(shared|configure)|InAppPurchase\.instance|requestPurchase\(|"
            r"RNIap|getSubscriptions\(|Purchases\.getOfferings")
IAP_DEPS = ("react-native-iap", "expo-iap", "expo-in-app-purchases", "react-native-purchases", "purchases_flutter",
            "in_app_purchase", "flutter_inapp_purchase", "RevenueCat", "purchases-ios", "adapty", "react-native-adapty",
            "adapty_flutter", "superwall", "@superwall/react-native-superwall", "superwallkit_flutter", "Qonversion",
            "react-native-qonversion", "qonversion_flutter", "glassfy")
RESTORE = (r"(?i)restore[_ ]?purchases|restoreCompletedTransactions|AppStore\.sync|restorePurchases|restoreTransactions|"
           r"getAvailablePurchases|\.restore\(|Restore Purchases|storeButton\(\s*\.visible\s*,\s*for:\s*\.restorePurchases")
SUB = (r"\.autoRenewable\b|subscriptionPeriod|SubscriptionStoreView|\bsubscription(s)?\b.*(product|offer|period|monthly|"
       r"yearly|annual)|getSubscriptions|Purchases\.getOfferings|\bpaywall\b")
TERMS = (r"(?i)terms[ _-]?of[ _-]?(use|service)|\bEULA\b|stdeula|/terms\b|subscriptionStorePolicyDestination|"
         r"termsOfService|termsUrl|terms_url")
PRIVACY = r"(?i)privacy[ _-]?policy|/privacy\b|privacyPolicy|privacy_url|privacyUrl"
EXTERNAL_PAY = {
    "Stripe": (r"StripePaymentSheet|STPPaymentHandler|PaymentSheet\(|initPaymentSheet|presentPaymentSheet",
               ("@stripe/stripe-react-native", "flutter_stripe", "Stripe", "StripePaymentSheet", "stripe-ios")),
    "PayPal/Braintree": (r"BTDropInController|PayPalCheckout|BraintreeDropIn", ("react-native-paypal", "flutter_paypal", "Braintree", "BraintreeDropIn")),
    "Razorpay": (r"RazorpayCheckout", ("react-native-razorpay", "razorpay_flutter", "razorpay-pod")),
    "Web checkout": (r"checkout\.stripe\.com|buy\.stripe\.com|paypal\.com/checkout|lemonsqueezy\.com/checkout|gumroad\.com/l/|paddle\.com/checkout", ()),
}
PRICE = r"[$€£¥₹]\s?\d{1,4}[.,]\d{2}\b|\b\d{1,4}[.,]\d{2}\s?(USD|EUR|GBP|€|£)(?!\w)"
LOOTBOX = r"(?i)loot[ _-]?box|gacha|mystery[ _-]?box|lucky[ _-]?draw|card[ _-]?pack"
ODDS = r"(?i)\bodds\b|drop[ _-]?rate|probabilit"


@check("payments", "In-app purchase & subscriptions", "Business")
def run(proj):
    out = []
    iap_dep = proj.has_dep(*IAP_DEPS)
    iap_hits = proj.grep(IAP_CODE, limit=1)
    has_iap = bool(iap_dep or iap_hits)
    where = f"dependency {iap_dep[0]}" if iap_dep else (f"{iap_hits[0].file}:{iap_hits[0].line}" if iap_hits else "")

    # external payment SDKs
    for name, (rx, deps) in EXTERNAL_PAY.items():
        dep = proj.has_dep(*deps) if deps else []
        hits = proj.grep(rx, limit=1) if not dep else []
        if dep or hits:
            h = hits[0] if hits else None
            out.append(F("external-payment", f"{name} payments present", WARNING, JUDGMENT, "3.1.1 / 3.1.3",
                         f"{name} found ({'dependency ' + dep[0] if dep else h.text[:90]}).",
                         "Fine for physical goods and real-world services (3.1.3(e)) or person-to-person services. "
                         "Digital content, subscriptions, premium features and in-app currency must use IAP unless "
                         "a storefront entitlement/exception applies (US link-outs, EU/Brazil/Korea alternative terms). "
                         "State in review notes what is sold.",
                         file=h.file if h else None, line=h.line if h else None))
    if not has_iap:
        return out

    # restore purchases
    if not (proj.grep(RESTORE, limit=1) or proj.grep_strings(r"(?i)restore")):
        out.append(F("no-restore", "No Restore Purchases path", BLOCKER, REVIEW_RISK, "3.1.1",
                     f"IAP is implemented ({where}) but no restore mechanism or 'Restore' UI was found.",
                     "Add a visible 'Restore Purchases' button (paywall + settings) that calls AppStore.sync() / "
                     "Purchases.restorePurchases() / your SDK's restore.", ))
    # subscriptions: terms + privacy links in app
    if proj.grep(SUB, limit=1, flags=0):
        missing = []
        if not (proj.grep(TERMS, limit=1) or proj.grep_strings(TERMS)):
            missing.append("Terms of Use (EULA)")
        if not (proj.grep(PRIVACY, limit=1) or proj.grep_strings(PRIVACY)):
            missing.append("Privacy Policy")
        if missing:
            out.append(F("sub-disclosure", f"Subscription screen missing {' & '.join(missing)} links", BLOCKER, REVIEW_RISK,
                         "3.1.2(c)",
                         "Auto-renewable subscription code found but no in-app link to " + " or ".join(missing) + ".",
                         "On the purchase screen show: title, length, price per period (from StoreKit), and functional "
                         "links to Terms of Use (Apple standard EULA is fine) and Privacy Policy. Add the same links to "
                         "the App Store description / EULA field."))
    # hardcoded prices
    hits = proj.grep_strings(PRICE)
    if hits:
        h = hits[0]
        out.append(F("hardcoded-price", "Hardcoded price strings in UI", WARNING, REVIEW_RISK, "3.1.2(c) / 2.3.1",
                     f"{len(hits)} string(s) look like prices, e.g. `{h.text[:90]}`.",
                     "Display Product.displayPrice / SDK localized price. Hardcoded prices go wrong in other "
                     "storefronts and after price changes, and reviewers flag mismatches with the actual charge.",
                     file=h.file, line=h.line))
    # loot boxes
    lb = proj.grep(LOOTBOX, limit=1) or proj.grep_strings(LOOTBOX)
    if lb and not (proj.grep(ODDS, limit=1) or proj.grep_strings(ODDS)):
        out.append(F("lootbox-odds", "Randomized paid items without odds disclosure", WARNING, REVIEW_RISK, "3.1.1",
                     f"Loot-box style mechanic found (`{lb[0].text[:80]}`) but no odds/drop-rate disclosure.",
                     "Disclose the odds of each item type before purchase.", file=lb[0].file, line=lb[0].line))
    return out
