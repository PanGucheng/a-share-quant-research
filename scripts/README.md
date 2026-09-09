# Script Index

## Active Entry Points

Daily/Forward: `daily_update.py`, `run_forward_prediction_v1.py`,
`run_paper_portfolio_v1.py`, `update_forward_labels_v1.py`.

Research: `run_fast_research_mt_v2.py`, `run_research_lightgbm_full_mt_v2.py`,
`run_long_history_core_factor_phase0_v1.py`, and `check_quality.py`.

Research Protocol V3-MVP: `run_research_protocol_v3_mvp.py` implements the authorized
P0-P2 prepare/audit/canary/finalize stages. Audit years may run in four processes;
engineering model fits stay sequential with eight LightGBM threads. `wide-canary`
uses monthly float64 files and LightGBM Sequence for the 494-column resource check.
Old wide-run claims are withdrawn; fresh recomputation is verified in the V3 report.
`revalidate_research_protocol_v3.py` provides an independent calendar oracle, a
bounded real-data probe, and post-recomputation receipt/count checks.
`verify_research_protocol_v3_postrun.py` reloads all four saved models and checks
every saved prediction against canonical features, writing separate review evidence.
This runner
does not expose pool competition or recent diagnostic execution.

## Pinned Maintenance / Qualification

`audit_lightgbm_thread_determinism_v1.py`,
`qualify_full_research_acceleration_v3.py`, benchmark/audit/validate/freeze tools,
and historical runners remain for evidence reproduction and environment changes.
Their names do not imply a current backlog.

## Consolidation Audit

`repository_consolidation_audit_v1.py` produces the repository inventory and
reference graph. No script is automatically deleted by this audit; dead-code
candidates require a separate, evidence-backed review.

## V3 nine-fold model/prediction precompute

`precompute_research_protocol_v3.ps1` runs Broad494 precompute/replay then Strict332
precompute/replay, 2015–2023 only. User-run long jobs; no outcome evaluation or pool
comparison. See [runbook](../docs/V3_PREDICTION_PRECOMPUTE_RUNBOOK.md).
