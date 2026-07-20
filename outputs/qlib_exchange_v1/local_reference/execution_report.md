# Qlib Exchange V1 Local Reference Execution

- Operational status: `pass`
- Reference readiness: `blocked_incomplete_tradability_and_pit_universe`
- Instruments: `30`
- Trading days: `80`
- Orders / fills: `993` / `981`
- Signal: transparent trailing momentum, observed at t close and executed at t+1 open.
- Unit semantics: the public schema uses original prices/raw shares; the adapter converts to and from Qlib adjusted units.
- Tradability limitation: suspension and price-limit flags are volume/change proxies, not authoritative PIT labels.
