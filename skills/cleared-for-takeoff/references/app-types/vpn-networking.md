# VPN, networking, MDM and content blockers (5.4, 5.5)

- [ ] VPN apps use the **NEVPNManager / NetworkExtension** API, and must be offered by an organisation, not an individual (5.4).
- [ ] Clear declaration of what user data is collected and how it is used, shown in the app before purchase or use.
- [ ] No selling, using or disclosing user data to third parties.
- [ ] VPN licences where required (China and other storefronts restrict VPNs entirely).
- [ ] Parental control, ad blocking and security apps from approved providers may use NetworkExtension. Explain the use in the review notes.
- [ ] MDM apps need a business/education/government org and must use the MDM capability (5.5).
- [ ] Local network access: `NSLocalNetworkUsageDescription` plus `NSBonjourServices` if you browse services.
- [ ] Don't claim "unlimited" or "military-grade" without substantiation (2.3.1).
