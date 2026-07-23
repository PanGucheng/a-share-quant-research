# Market Cache V2

- Scope: `full corrected OOS`
- Cache key: `f48d995e00738928cb219bdf0a038e23dd29b4718b3093c8d1e0ab81d564229e`
- Rows: `853936`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
