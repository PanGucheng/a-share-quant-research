# Factor Research Toolchain Readiness V1

- Overall status: `ready`
- Scope: factor research and factor screening only.
- Boundary: no Qlib baseline replacement, no new model training, no live trading, no evaluator definition changes.

## Conclusion

The factor research toolchain is ready for large-scale multi-source screening.

## Readiness Checks

| check_id | status | detail | recommendation |
| --- | --- | --- | --- |
| prefilter_policy | pass | catalog=data_quality,tradability; manifest=data_quality,tradability | Keep data_quality and tradability as mandatory prefilters for every new factor source. |
| open_source_evaluator_systems | pass | systems=alphalens_reloaded,jqfactor_analyzer,qlib_eval,project_current | Do not replace external evaluator definitions; keep Alphalens Reloaded, jqfactor_analyzer, Qlib eval, and project_current coexisting. |
| batch_runner | pass | batch_configs=3 | Use the batch runner for large jobs, with dry-run, resume, manifests, and logs. |
| required_output_contracts | pass | missing_or_failed=0 | Repair missing contracts before launching full-scale screening. |
| runnable_factor_inventory | pass | total_runnable=247 | Use Alpha158 and the promoted TA source to validate the machinery, then add more sources through the same gates. |
| new_source_adapter_inventory | pass | new_source_runnable=77 | Keep the promoted non-Alpha158 catalog as a large-scale screening input and add later sources through the same adapter gate. |
| generic_multi_source_screening | pass | contracts=6, failed=0 | Use the generic multi-source screening contract as the entry point for Alpha158, TA, Alpha101, and future factors. |

## Catalog Summary

| catalog_id | path | status | factor_count | enabled_count | runnable_count | role |
| --- | --- | --- | --- | --- | --- | --- |
| project_main_catalog | factor_research/factor_catalog.yaml | pass | 15 | 15 | 15 | Project planning catalog and currently registered seed factors. |
| alpha158_full_runnable_catalog | outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml | pass | 155 | 155 | 155 | Promoted Qlib Alpha158 catalog after expression validation and V4 batch evaluation. |
| ta_promoted_catalog | outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml | pass | 77 | 77 | 77 | Promoted TA factors after adapter smoke and remaining batch V4 validation. |
| kunquant_alpha101_metadata_catalog | outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml | pass | 82 | 0 | 0 | KunQuant Alpha101 metadata catalog after source audit; adapter pending and non-runnable. |

## Source Readiness

| source_project | declared_status | license | local_path_status | source_file_status | runnable_factor_count | readiness | readiness_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ginkgo_alpha101 | metadata_registered_adapter_pending | MIT | available | available | 0 | adapter_pending | source registered but calculation adapter is not promoted |
| kunquant_alpha101 | source_audit_passed_adapter_pending | Apache-2.0 | available | available | 0 | adapter_pending | source registered but calculation adapter is not promoted |
| qlib_alpha158 | formula_inventory_passed_expression_adapter_pending | MIT | available | available | 155 | ready | runnable catalog entries available |
| ta | metadata_registered_adapter_pending | MIT | available | available | 77 | ready | runnable catalog entries available |
| qlib_factor_platform_presets | design_reference | MIT | available | available | 0 | reference_only | design reference, not a runnable factor source |
| alphalens_reloaded | factor_research/external/adapters.py::to_alphalens_factor_data | Apache-2.0 | available | available | 0 | reference_or_evaluator | Primary open-source factor evaluation reference. |
| factortest | future data inventory and exposure adapters | MIT | available | available | 0 | reference_or_evaluator | A-share data layer, factor test, industry/style exposure reference. |
| jqfactor_analyzer | factor_research/external/adapters.py::to_jqfactor_inputs | MIT | available | available | 0 | reference_or_evaluator | A-share style factor analysis reference with group, neutralization, and Chinese reporting conventions. |
| kunquant | kunquant_alpha101_adapter_pending | Apache-2.0 | available | available | 0 | reference_or_evaluator | Alpha101/Alpha158 formula and high-performance factor calculation reference. |
| multi_factor | future factor catalog entries after license review | unknown | available | available | 0 | reference_or_evaluator | A-share fundamental factor and single-factor test reference. |
| qlib_evaluate | factor_research/external/adapters.py::to_qlib_score_frame | MIT | available | available | 0 | reference_or_evaluator | Keep compatibility with the baseline framework and Qlib-native risk/evaluation tools. |
| qlib_factor_platform | none | MIT | available | available | 0 | reference_or_evaluator | Reference for factor management, workflow organization, and configurable analysis pages. |

## Required Output Contracts

| contract_id | group | path | status | row_count | min_rows | size_bytes |
| --- | --- | --- | --- | --- | --- | --- |
| alpha158_formula_inventory | alpha158_catalog | outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv | pass | 158 | 158 | 43403 |
| alpha158_full_runnable_catalog | alpha158_catalog | outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml | pass | 155 | 150 | 97673 |
| alpha158_remaining138_holdout_catalog | alpha158_catalog | outputs/factor_catalog_alpha158_v1/alpha158_catalog_remaining138_holdout.yaml | pass | 3 | 1 | 2336 |
| alpha158_first20_metric_index | open_source_evaluation | outputs/factor_evaluation_v4/alpha158_first20_smoke/alpha158_first20_metric_index.csv | pass | 4200 | 1 | 1373341 |
| alpha158_remaining138_metric_index | open_source_evaluation | outputs/factor_evaluation_batch_v1/alpha158_remaining138/alpha158_remaining138_metric_index.csv | pass | 28948 | 1 | 10409604 |
| alpha158_screening_input | screening | outputs/factor_screening_alpha158_v1/full158/alpha158_factor_screening_input.csv | pass | 158 | 158 | 216221 |
| alpha158_judgement_board | screening | outputs/factor_judgement_alpha158_v1/full158/alpha158_judgement_board.csv | pass | 158 | 1 | 80536 |
| alpha158_candidate_pool | candidate_pool | outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_candidate_pool.csv | pass | 158 | 1 | 81473 |
| alpha158_alpha_candidates | candidate_pool | outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv | pass | 14 | 1 | 7666 |
| alpha158_main_portfolio_diagnostics | portfolio_smoke | outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/single_factor_summary.csv | pass | 14 | 1 | 5454 |
| alpha158_recent_oos_portfolio_diagnostics | portfolio_smoke | outputs/alpha158_portfolio_diagnostics_v1/recent_oos_2024_2026/single_factor_summary.csv | pass | 14 | 1 | 5448 |
| alpha158_stability_diagnostics | stability | outputs/alpha158_stability_diagnostics_v1/main_vs_recent_oos/single_factor_stability.csv | pass | 14 | 1 | 3900 |
| ta_adapter_inventory | ta_adapter | outputs/ta_factor_adapter_v1/smoke/ta_factor_inventory.csv | pass | 86 | 80 | 17525 |
| ta_smoke_passed_catalog | ta_adapter | outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke_passed.yaml | pass | 5 | 5 | 3780 |
| ta_promoted_catalog | ta_adapter | outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml | pass | 77 | 77 | 48274 |
| ta_holdout_catalog | ta_adapter | outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_holdout2.yaml | pass | 2 | 2 | 1873 |
| ta_batch_promotion_audit | ta_adapter | outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_audit.csv | pass | 74 | 74 | 6567 |
| ta_remaining74_metric_index | ta_v4_batch | outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/ta_remaining74_metric_index.csv | pass | 1332 | 1 | 333759 |
| ta_smoke_evaluator_status | ta_v4_smoke | outputs/factor_evaluation_v4/ta_smoke_v1/evaluator_status.csv | pass | 15 | 15 | 2231 |
| ta_smoke_metric_index | ta_v4_smoke | outputs/factor_evaluation_v4/ta_smoke_v1/open_source_metric_index.csv | pass | 90 | 1 | 18595 |
| ta_smoke_promotion_audit | ta_adapter | outputs/ta_factor_adapter_v1/smoke/ta_factor_smoke_promotion_audit.csv | pass | 5 | 5 | 418 |
| multi_source_screening_input | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_screening_input.csv | pass | 237 | 200 | 127160 |
| multi_source_candidate_board | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_candidate_board.csv | pass | 237 | 200 | 140199 |
| multi_source_candidate_pool | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_candidate_pool.csv | pass | 237 | 200 | 140199 |
| multi_source_alpha_candidates | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_alpha_candidates.csv | pass | 14 | 1 | 8594 |
| multi_source_holdouts | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_holdouts.csv | pass | 5 | 1 | 3550 |
| multi_source_contract_status | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_contract_status.csv | pass | 7 | 7 | 314 |
| alpha101_source_summary | alpha101_source_audit | outputs/factor_catalog_alpha101_v1/source_audit/alpha101_source_summary.csv | pass | 2 | 2 | 574 |
| kunquant_alpha101_inventory | alpha101_source_audit | outputs/factor_catalog_alpha101_v1/source_audit/kunquant_alpha101_inventory.csv | pass | 82 | 80 | 19926 |
| kunquant_alpha101_metadata_catalog | alpha101_source_audit | outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml | pass | 82 | 80 | 51857 |

## Stage Counts

| catalog_id | source_project | stage | enabled | runnable | factor_count |
| --- | --- | --- | --- | --- | --- |
| alpha158_full_runnable_catalog | qlib_alpha158 | alpha158_first20_v4_smoke_passed | True | True | 20 |
| alpha158_full_runnable_catalog | qlib_alpha158 | alpha158_remaining138_v4_batch_passed | True | True | 135 |
| kunquant_alpha101_metadata_catalog | kunquant_alpha101 | alpha101_source_audit_adapter_pending | False | False | 82 |
| project_main_catalog | qlib_baseline_basic | current_v4_seed | True | True | 5 |
| project_main_catalog | qlib_baseline_basic | project_basic_available | True | True | 10 |
| ta_promoted_catalog | ta | ta_adapter_v4_batch_passed | True | True | 72 |
| ta_promoted_catalog | ta | ta_adapter_v4_smoke_passed | True | True | 5 |

## Next Step

1. Keep Alpha158 as the validated reference pipeline, not the next research bottleneck.
2. Treat the promoted TA catalog as the first large-scale non-Alpha158 input.
3. Use the generic multi-source screening contract as the standard entry point for candidate-pool construction.
4. Start broad factor discovery by adding more open-source factor families through the same adapter, V4 batch, promotion, and holdout gates.
