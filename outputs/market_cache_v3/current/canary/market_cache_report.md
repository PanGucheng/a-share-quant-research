# Market Cache V3 — Unit Semantics Correction

- Scope: `canary`
- Cache key: `b97c2c0c9e79c73d9cd089b23d8e5db17af31a23f2c92d12f4b7f6c58322ebdd`
- Rows: `1830`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
- Community volume is converted from adjusted board lots with `factor × 100`; amount is converted from CNY thousands with `×1000`.
