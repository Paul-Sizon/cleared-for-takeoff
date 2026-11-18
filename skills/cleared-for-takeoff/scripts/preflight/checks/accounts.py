"""Accounts: login services (4.8) and in-app account deletion (5.1.1(v))."""
from __future__ import annotations

from ..finding import BLOCKER, INFO, JUDGMENT, REVIEW_RISK, WARNING
from . import check, make

F48 = make("login-services")
FDEL = make("account-deletion")

THIRD_PARTY_LOGIN = {
    "Google": (r"\bGIDSignIn\b|GoogleSignIn|signInWithGoogle|GoogleAuthProvider|google_sign_in|GoogleSignin\b",
               ("@react-native-google-signin/google-signin", "google_sign_in", "GoogleSignIn", "expo-auth-session/providers/google")),
    "Facebook": (r"FBSDKLoginKit|LoginManager\(\)\.logIn|FacebookLogin|FacebookAuthProvider|flutter_facebook_auth",
                 ("react-native-fbsdk-next", "flutter_facebook_auth", "FBSDKLoginKit")),
    "X/Twitter": (r"TwitterAuthProvider|twitter_login", ("twitter_login",)),
    "GitHub": (r"GithubAuthProvider|GitHubAuthProvider", ()),
    "Microsoft": (r"MSALPublicClientApplication|OAuthProvider\(providerID:\s*\"microsoft", ("react-native-msal", "msal_flutter")),
    "LINE / Kakao / other social": (r"LineSDK|KakaoSDK|kakao_flutter_sdk", ("kakao_flutter_sdk", "@react-native-seoul/kakao-login")),
}
SIWA = r"ASAuthorizationAppleIDProvider|SignInWithAppleButton|AppleAuthentication|appleAuth\b|SignInWithApple|sign_in_with_apple|OAuthProvider\(providerID:\s*\"apple\.com"
SIWA_DEPS = ("expo-apple-authentication", "@invertase/react-native-apple-authentication", "sign_in_with_apple")

SIGNUP = (r"createUser(WithEmail)?\b|createUserWithEmailAndPassword|\bsignUp\s*\(|\bsignUpWith|auth\.signUp|"
          r"\bregisterUser\b|/(api/)?(v\d/)?(auth/)?(register|signup|sign-up)\b|\bSignUpView\b|\bRegisterView\b|"
          r"\bSignUpScreen\b|\bRegisterScreen\b|\bCreateAccount(View|Screen)\b")
DELETE = (r"(?i)delete[_ -]?account|delete[_ -]?user\b|currentUser\??!?\.delete|\buser\.delete\(|"
          r"auth\.admin\.deleteUser|/(account|user|users|me)/delete|remove[_ -]?account|close[_ -]?account|"
          r"destroy[_ -]?account")


@check("login-services", "Login services (Sign in with Apple)", "Accounts")
def login(proj):
    out = []
    providers = []
    for name, (rx, deps) in THIRD_PARTY_LOGIN.items():
        hit = proj.has_dep(*deps) if deps else []
        if hit:
            providers.append((name, f"dependency {hit[0]}", None, None))
            continue
        hits = proj.grep(rx, limit=1)
        if hits:
            providers.append((name, f"`{hits[0].text[:80]}`", hits[0].file, hits[0].line))
    if not providers:
        return out
    if proj.has_dep(*SIWA_DEPS) or proj.grep(SIWA, limit=1):
        return out
    names = ", ".join(p[0] for p in providers)
    first = providers[0]
    out.append(F48("no-equivalent", f"Third-party login ({names}) without Sign in with Apple or equivalent", WARNING,
                   REVIEW_RISK, "4.8",
                   f"Found {names} login ({first[1]}) and no Sign in with Apple implementation.",
                   "Offer an equivalent login that limits data to name + email, lets users hide their email, and "
                   "does no ad tracking without consent. Sign in with Apple is the simplest way to meet 4.8. "
                   "Exempt if the app only uses your own accounts, is an enterprise/education app, or a client "
                   "for a specific third-party service.",
                   file=first[2], line=first[3]))
    return out


@check("account-deletion", "In-app account deletion", "Accounts")
def deletion(proj):
    out = []
    signup = proj.grep(SIGNUP, limit=1)
    if not signup:
        return out
    if proj.grep(DELETE, limit=1) or proj.grep_strings(r"(?i)delete (my |your )?account|account deletion"):
        return out
    h = signup[0]
    out.append(FDEL("missing", "Account creation without in-app deletion", BLOCKER, REVIEW_RISK, "5.1.1(v)",
                    f"Sign-up flow found (`{h.text[:90]}`) but nothing that lets users delete their account.",
                    "Add a clearly discoverable Delete Account action (e.g. Settings → Account) that deletes the "
                    "account and associated data, or links straight to a web page that completes deletion. Deactivation "
                    "alone does not count. If you use Sign in with Apple, also revoke the token via the REST API.",
                    file=h.file, line=h.line))
    return out
