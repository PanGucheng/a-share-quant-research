# Open Source Factor Expansion Audit V1

- Scope: source and data-family audit only; no model training, no strategy tuning, no direct GPL/unknown-license code import.
- Boundary: every future source still needs data_quality, tradability, adapter smoke, V4 batch, promotion/holdout, screening, and judgement.

## Policy

| compatible_licenses | caution_licenses | required_prefilter |
| --- | --- | --- |
| MIT,Apache-2.0,BSD | GPL-3.0,unknown | data_quality,tradability |

## Recommendation Counts

| recommendation | count |
| --- | --- |
| data_audit_next | 1 |
| direct_adapter_next | 1 |
| reference_only_due_gpl | 2 |
| reference_only_until_license_review | 4 |

## Candidate Ranking

| candidate_id | detected_license | data_fit | adapter_complexity | priority_score | recommendation | candidate_item_count | source_file_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qlib_alpha360 | MIT | high | low | 12 | direct_adapter_next | 360.000000 | pass |
| factortest_exposure_diagnostics | MIT | medium | medium | 9 | data_audit_next |  | pass |
| get_astock_factors | unknown | external | low | 5 | reference_only_until_license_review |  | pass |
| techfactor_gtja191 | GPL-3.0 | high | high | 4 | reference_only_due_gpl | 191.000000 | pass |
| alphatrading_notebook_workflow | unknown | medium | high | 3 | reference_only_until_license_review |  | pass |
| multi_factor_fundamental_formulas | unknown | low | high | 1 | reference_only_until_license_review | 11.000000 | pass |
| parsnip77_multi_factor_model | unknown | medium | medium | 1 | reference_only_until_license_review |  | missing_local_path |
| china_ashare_equity_characteristics | GPL-3.0 | low | high | 0 | reference_only_due_gpl | 115.000000 | pass |

## Next Steps

| step_order | candidate_id | action | reason |
| --- | --- | --- | --- |
| 1 | qlib_alpha360 | build_adapter_smoke_plan | Best compatible high-fit source for immediate factor-pool expansion. |
| 2 | factortest_exposure_diagnostics | build_data_capability_audit | Useful for industry/style/fundamental expansion but requires data mapping first. |
| 3 | get_astock_factors,techfactor_gtja191,alphatrading_notebook_workflow | keep_reference_only | License, runtime, or data assumptions are not safe for direct import yet. |

## Output Files

- `open_source_factor_source_candidates.csv`
- `open_source_factor_expansion_next_steps.csv`
- `open_source_factor_expansion_manifest.json`
- `open_source_factor_expansion_report.md`
