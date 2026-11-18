# Health, fitness and medical (1.4.1, 5.1.3, 27.x)

- [ ] **HealthKit**: the entitlement is present; `NSHealthShareUsageDescription` / `NSHealthUpdateUsageDescription` are specific; HealthKit data is never used for ads or data mining, never stored in iCloud outside HealthKit, and never shared with third parties without consent (5.1.3).
- [ ] The UI makes clear the app integrates with Apple Health (HIG). Reviewers look for it.
- [ ] Medical claims: no diagnosis or treatment claims without regulatory clearance (1.4.1). Measurement apps (blood pressure, glucose, oxygen) using only phone sensors get rejected.
- [ ] Disclaimers: "not medical advice; consult a doctor" where relevant. Dosage calculators need approval from a regulated entity.
- [ ] **Regulated medical device declaration** in App Store Connect for Health & Fitness / Medical apps in the EEA, UK and US (Mar 2026). Existing apps must declare by early 2027.
- [ ] Health research needs informed consent and ethics board approval (5.1.3(iii)/(iv)).
- [ ] Workout or step data: the motion purpose string is present. Background location for runs is justified.
- [ ] AI health coaching: follow the 5.1.2(i) consent rules, and remember health data is sensitive. Get explicit consent per provider.
