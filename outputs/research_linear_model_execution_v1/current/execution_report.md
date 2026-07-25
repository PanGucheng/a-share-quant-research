# Research Linear Model Qlib Execution V1

- Scope: `full`.
- Splits / methods: 3 / 2.
- Orders / fills: 33,505 / 28,152.
- Market semantics: corrected Market Cache V3, date-aware fees, dynamic lot rules, T+1 and participation limit.
- Successful / expected scenarios: 4 / 6.
- Operational status: `blocked`.
- Classified failures: 2.
- A held position that exceeds the frozen 20-trading-day stale valuation horizon is blocked; prices are not silently carried forward and positions are not liquidated using future knowledge.
- Historical execution remains non-authoritative under Instrument State Decision B.
- Production model selected: false.
