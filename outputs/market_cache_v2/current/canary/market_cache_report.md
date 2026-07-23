# Market Cache V2

- Scope: `canary`
- Cache key: `9ea9a8923f451456ccbb8ac91067b13248c51775630c38ed2988dd289f1ff150`
- Rows: `1830`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
