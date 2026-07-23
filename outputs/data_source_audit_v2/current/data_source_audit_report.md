# Data Source Audit V2 Canary

- Sample: `150` instruments, `2024-08-01` to `2026-02-04`.
- Decision: **Decision B**.
- Community/external close tolerance match: `1.000000`.
- BaoStock / AKShare instrument coverage: `100.00%` / `2.00%`.
- Core raw OHLC is reliable after factor reversal, but Community unit semantics require explicit normalization.
- P0: Market Cache v2 participation volume omitted the board-lot `×100` conversion and is under-scaled 100×.
- P1: Community amount is CNY thousands and requires `×1000`; current execution does not consume amount.
- BaoStock `isST` and `tradestatus` are useful candidates, but before-open availability remains unproven and fail-closed.
- Observed historical ST / non-trading instruments: `13` / `30`.
- AKShare Eastmoney history is not stable in the active proxy environment; failures are retained in query receipts.
- No production provider, Matrix v4, factor selection, model, or authoritative historical OOS artifact was changed.
