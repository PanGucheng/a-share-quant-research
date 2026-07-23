# PIT Instrument State V1

- Scope: `canary`
- Rows / instruments / dates: `1830` / `183` / `10`
- Listing lifecycle, board and IPO age are materialized from the frozen provider lifecycle.
- Historical ST, pre-open suspension and terminal-event state are unavailable and fail closed for authoritative readiness.
- `execution_*_approximation` columns are explicit non-authoritative inputs; they are never evidence of PIT completeness.
