# Market Cache V2

- Scope: `full corrected OOS`
- Cache key: `68864351e6fb50c7ab793619b31943dbac651469bc0750e8253c1a690dfbc0f4`
- Rows: `853936`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
