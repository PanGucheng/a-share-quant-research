# Market Cache V2

- Scope: `canary`
- Cache key: `d1a09340bed980b2e6bc7bdd00e09e954e392062641f9e12ee5c8bf5326056b4`
- Rows: `1830`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
