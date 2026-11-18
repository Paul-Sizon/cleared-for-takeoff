# networking: ATS, IPv6 and cleartext
**Guidelines:** 2.5.5 (IPv6) · 2.1 · ATS · **Rules:** `ats-disabled`, `ipv4-literal`, `cleartext-http`

- **IPv6:** App Review uses an IPv6-only (NAT64/DNS64) network. Hostnames work through DNS64. IPv4 literals in URLs or sockets fail, and so do backends without AAAA or NAT64 reachability. Test with macOS Internet Sharing → *Create NAT64 Network*.
- **ATS:** `NSAllowsArbitraryLoads = YES` requires justification in App Store Connect. Use `NSExceptionDomains` for specific hosts, or `NSAllowsArbitraryLoadsInWebContent` for browsers. `NSAllowsLocalNetworking` covers LAN devices.
- **Cleartext:** `http://` URLs are blocked by ATS at runtime. The feature silently fails in review.

## Verify
- An IPv4 literal pointing at a LAN device (an IoT setup flow) is legitimate. Make sure it's for local networking, add `NSLocalNetworkUsageDescription`, and explain it in the review notes.
- `http://` defaults that are always overridden in production (e.g. `String.fromEnvironment(..., defaultValue: 'http://…')`) are only a problem if the release build doesn't override them. Check the build script or CI.
