# Factor Validation Baseline V1 Audit

- Captured at: `2026-07-12T11:24:56.812542+00:00`
- Branch: `agent/factor-validation-roadmap-v1`
- Commit: `bea43640f76dc4ed3b1d50c6609b6d77caf1933e`
- Overall status: `research_blocked`

## Current Repository Status

The baseline toolchain remains operational. 11/11 critical compact artifacts are readable. V3.39 remains correctly blocked by coverage and has not entered downstream defaults.

## Planned File Scope

Stage 0 adds one audit config, one audit runner, separated core/optional requirements, this compact output directory, and the detailed roadmap documents. It does not change factor evaluation, candidate roles, universe definitions, or portfolio defaults.

## Dependency Compatibility

| distribution | import_name | role | installed | version | import_available | license_record | status | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pyqlib | qlib | existing_core | True | 0.1.dev6 | True | MIT | pass | installed and import target discoverable |
| pandas | pandas | existing_core | True | 2.3.3 | True | BSD-3-Clause | pass | installed and import target discoverable |
| numpy | numpy | existing_core | True | 2.2.6 | True | BSD-3-Clause | pass | installed and import target discoverable |
| scipy | scipy | existing_core | True | 1.15.3 | True | BSD-3-Clause | pass | installed and import target discoverable |
| scikit-learn | sklearn | existing_core | True | 1.7.2 | True | BSD-3-Clause | pass | installed and import target discoverable |
| statsmodels | statsmodels | research_validation_core | True | 0.14.6 | True | BSD-3-Clause | pass | installed and import target discoverable |
| pandera | pandera | phase_1_required | True | 0.32.1 | True | MIT | pass | installed and import target discoverable |
| mlfinpy | mlfinpy | phase_3_required | False |  | False | MIT | warning | not installed during baseline freeze; install and verify only when the owning phase starts |
| Riskfolio-Lib | riskfolio | optional_portfolio | False |  | False | BSD-3-Clause | warning | not installed during baseline freeze; install and verify only when the owning phase starts |

## Baseline Metrics

| metric | observed_value | expected_value | status | source_path | source_column_or_rule |
| --- | --- | --- | --- | --- | --- |
| total_runnable_factors | 669.0 | 669.0 | pass | outputs/factor_research_toolchain_readiness_v1/current/catalog_summary.csv | sum(runnable_count) |
| new_source_runnable_factors | 499.0 | 499.0 | pass | outputs/factor_research_toolchain_readiness_v1/current/catalog_summary.csv | sum(runnable_count) for promoted TA/Alpha101/Alpha360 catalogs |
| multi_source_screening_rows | 679.0 | 679.0 | pass | outputs/multi_source_screening_v1/current/multi_source_screening_input.csv | row_count |
| multi_source_judgement_rows | 679.0 | 679.0 | pass | outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv | row_count |
| multi_source_research_candidate_rows | 342.0 | 342.0 | pass | outputs/multi_source_judgement_v1/current/multi_source_research_candidates.csv | row_count |
| new_source_alpha_probe_rows | 328.0 | 328.0 | pass | outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv | row_count |
| alpha158_candidate_rows | 14.0 | 14.0 | pass | outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv | row_count |
| alpha360_strict_oos_factor_rows | 3.0 | 3.0 | pass | outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_summary.csv | row_count |
| liquidity_watchlist_rows | 19.0 | 19.0 | pass | outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv | contract detail |
| liquidity_residualized_factor_count | 19.0 | 19.0 | pass | outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv | contract detail |
| liquidity_residualized_coverage_min | 0.1495 | 0.1495 | pass | outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv | contract detail |
| liquidity_downstream_default_included | 0.0 | 0.0 | pass | outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv | contract detail |
| liquidity_residualized_required_coverage_min | 0.8 | 0.8 | pass | outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv | roadmap contract threshold |

## Command Verification

| check_id | status | exit_code | expected_exit_codes | duration_seconds |
| --- | --- | --- | --- | --- |
| liquidity_residualized_synthetic_validation | pass | 0 | 0 | 0.874 |
| liquidity_residualized_contract_audit | pass | 1 | 1 | 0.717 |
| factor_research_toolchain_readiness | pass | 0 | 0 | 4.738 |

## Contract

| check_name | status | observed_value | required_value | severity | reason |
| --- | --- | --- | --- | --- | --- |
| critical_artifacts | pass | 0.0 | 0 | critical | All baseline artifacts must exist and be non-empty. |
| baseline_metric_drift | pass | 0.0 | 0 | critical | Frozen metrics must match the declared baseline. |
| existing_core_dependencies | pass | 0.0 | 0 | critical | Existing Qlib runtime dependencies must remain available. |
| research_validation_runtime | pass | 0.0 | 0 | critical | Statsmodels must be available for the validation layer. |
| future_phase_dependency_warnings | warning | 2.0 | recorded | warning | Deferred phase-owned dependencies: mlfinpy, Riskfolio-Lib. |
| command_checks | pass | 0.0 | 0 | critical | Existing lightweight validation and audits must return their expected codes. |
| v3_39_coverage_gate | blocked | 0.1495 | >=0.8 | critical | Known blocker is preserved; do not lower the threshold or promote residualized factors. |
| v3_39_downstream_default | pass | 0.0 | 0 | critical | Blocked residualized factors must remain outside downstream defaults. |

## Risks And Blockers

- V3.39 minimum residualized coverage is 0.1495 versus the unchanged 0.80 requirement. Residualized factors remain excluded from downstream defaults.
- Phase-owned dependencies still deferred: mlfinpy, Riskfolio-Lib. Install and verify each only in its owning phase; do not upgrade the full Qlib environment.
- Riskfolio-Lib is optional. Phase 6 may use SciPy if compatibility is not acceptable.
- Historical industry/size point-in-time data is still unavailable and remains a later-stage blocker.

## Phase 1 Implementation Plan

1. Install the bounded Pandera dependency only and rerun `pip check` plus existing baseline validation.
2. Add immutable Factor, Label, Tradability, Universe Interval, Screening, and Judgement schemas.
3. Add synthetic good/bad/no-mutation tests and compatibility exceptions scoped by file and field.
4. Audit existing compact outputs and emit schema inventory, validation results, contract status, and report.
5. Start phase 2 only after the phase 1 critical contract has no fail or blocked rows.

## Decision

Stage 0 implementation is complete when all non-V3.39 critical checks pass. The `research_blocked` overall status is intentional evidence that V3.39 is not eligible for downstream promotion; it does not prevent implementing the independent schema infrastructure in phase 1.
