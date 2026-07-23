# Market Cache V3 — Unit Semantics Correction

- Scope: `full corrected OOS`
- Cache key: `55d7a4f0a86e4bb095d6d63ea9180000c8152cde5aa6b328ed74dc54208ab4e9`
- Rows: `853936`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
- Community volume is converted from adjusted board lots with `factor × 100`; amount is converted from CNY thousands with `×1000`.
