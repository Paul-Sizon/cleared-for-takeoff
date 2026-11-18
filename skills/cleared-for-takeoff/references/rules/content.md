# content: placeholder, other platforms, beta copy
**Rules:** `placeholder` (2.1/2.3.3), `other-platform` (2.3.10), `beta-copy` (2.2)

- **Placeholder:** "Coming soon", lorem ipsum, TODO, dummy data, and disabled "not implemented" buttons all read as incomplete (2.1). Remove the entry point until the feature ships. Server-driven placeholders count too.
- **Other platforms (2.3.10):** don't mention Android or Google Play in the app or its metadata. Exceptions: legitimate cross-platform features (e.g. "Invite friends on any device"), or support docs explaining multi-platform sync. Phrase those neutrally.
- **Beta copy (2.2):** betas, demos and trials belong on TestFlight. "Beta" labels on individual features are tolerated but invite scrutiny.

## Verify
The scanner only looks at string literals and same-line JSX text. Copy loaded from localisation files (`Localizable.xcstrings`, `intl_*.arb`, `i18n/*.json`) is not scanned, so grep them too:
```bash
grep -rniE "lorem|coming soon|android|google play|beta" --include="*.xcstrings" --include="*.strings" --include="*.arb" --include="*.json" .
```
