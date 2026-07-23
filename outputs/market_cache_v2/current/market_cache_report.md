# Market Cache V2

- Scope: `full corrected OOS`
- Cache key: `2f7b1507e4231e71d344ae2a2ddcdfce82b924df66a2609d9722fa460517da1e`
- Rows: `853936`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
