# Kids Category and child audiences (1.3, 5.1.4)

- [ ] No third-party analytics or ads that send personally identifiable info or device data (5.1.4). Only kid-safe, human-reviewed ad networks. No behavioural ads.
- [ ] No links out, purchases, or other distractions without a **parental gate**. The gate must be an adult challenge, not "tap OK".
- [ ] No ATT prompt. Kids apps must not track.
- [ ] Privacy policy covers COPPA (US), GDPR-K and local laws. Verifiable parental consent before collecting personal data.
- [ ] Age band selected correctly (5 and under, 6–8, 9–11). Content appropriate for that band.
- [ ] No Sign in with Google/Facebook flows aimed at children.
- [ ] Declared Age Range API / age assurance where the jurisdiction requires it (Texas, Utah, Louisiana, Brazil, Australia, Singapore).
- [ ] Even outside the Kids Category, apps likely used by kids must not collect data without parental consent (5.1.4).

Scanner hints: tracking SDKs (`att/missing`) and ads SDKs are high-severity here. Upgrade them to BLOCKER.
