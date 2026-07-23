# Market Cache V2

- Scope: `full corrected OOS`
- Cache key: `f9151b5d1bc7070e5d6a167df9fc5eb1d8683805f08de6fbee4bf1ea40d2b99a`
- Rows: `853936`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
