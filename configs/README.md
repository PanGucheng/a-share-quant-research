# Configuration Index

Configuration files remain at their original paths because profiles, manifests,
tests, and qualification receipts may bind those paths. Do not move or rename a
configuration based on its version suffix.

## Active Entry Profiles

- `project.yaml`, `project.local.example.yaml`
- `fast_research_mt_v2.yaml` (screening execution)
- `full_research_accelerated_v3.yaml` (performance/development execution)
- `strategy_v1_paper_portfolio_v1.yaml` (frozen Strategy V1)
- `long_history_core_factor_phase0_v1.yaml` (completed Phase 0 reproduction)

## Pinned References

`research_lightgbm_v1.yaml`, `fast_research_v1.yaml`,
`research_lightgbm_full_exact_mt_v2.yaml`, and their qualification configs remain
available as frozen parents or evidence anchors. The same applies to canonical
dataset, Forward, and historical research configs referenced by reports/tests.

## Qualification / Reproduction

Configs named `*_qualification_*`, `*_canary_*`, `*_readiness_*`, or historical
research stages are retained for controlled reproduction. They are not new default
entrypoints and do not authorize model or Strategy changes.

The machine-readable reachability audit is at
`reports/repository_consolidation_v1/classification.csv`.
