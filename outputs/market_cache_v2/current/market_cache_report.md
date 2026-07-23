# Market Cache V2

- Scope: `full corrected OOS`
- Cache key: `c9fc766fc201b267dfbdc0813f8f0fd421bcb6e9d25cb1859455760941b742bc`
- Rows: `853936`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
