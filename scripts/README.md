# Script Index

## Active Entry Points

Daily/Forward: `daily_update.py`, `run_forward_prediction_v1.py`,
`run_paper_portfolio_v1.py`, `update_forward_labels_v1.py`.

Research: `run_fast_research_mt_v2.py`, `run_research_lightgbm_full_mt_v2.py`,
`run_long_history_core_factor_phase0_v1.py`, and `check_quality.py`.

## Pinned Maintenance / Qualification

`audit_lightgbm_thread_determinism_v1.py`,
`qualify_full_research_acceleration_v3.py`, benchmark/audit/validate/freeze tools,
and historical runners remain for evidence reproduction and environment changes.
Their names do not imply a current backlog.

## Consolidation Audit

`repository_consolidation_audit_v1.py` produces the repository inventory and
reference graph. No script is automatically deleted by this audit; dead-code
candidates require a separate, evidence-backed review.
