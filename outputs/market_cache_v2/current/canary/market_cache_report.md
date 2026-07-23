# Market Cache V2

- Scope: `canary`
- Cache key: `5a75d49bb356bf0b163c376c932698cd19306c8bb5f50ddbf67d389bd65c9d86`
- Rows: `1830`
- Open execution uses current open, previous close, lagged 20-day median volume and PIT state only.
- Same-day close is consumed only at the after-close valuation timestamp; no backward fill is permitted.
- Missing historical ST/suspension/terminal-event sources keep authoritative execution blocked.
