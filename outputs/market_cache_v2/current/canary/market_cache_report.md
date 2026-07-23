# Market Cache V2

- Scope: `canary`
- Cache key: `b89c9d291da8bdb7afa102faa0fe82630df9ce49952bce239aedc7c78c0e4ddb`
- Rows: `1830`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
