# Performance Program Closeout

Status: **CLOSED**.

Final execution baselines:

- Fast: `fast_research_mt_v2` (screening-only, 8T with 1T fallback).
- Full: `full_research_accelerated_v3` (non-authoritative performance profile;
  exact preparation/model parity qualified against `full_research_exact_mt_v2`).

The reference chain is preserved in place: frozen Full V1 1T -> exact Full MT V2
8T -> preparation acceleration V3. Phase H outer-worker contention benchmarking was
intentionally not pursued. Reopen this program only if measured research runtime
again becomes a material blocker. This archive is historical context, not a current
development entrypoint.
