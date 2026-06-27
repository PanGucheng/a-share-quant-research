# Factor Research Toolchain Readiness V1

- Overall status: `ready`
- Scope: factor research and factor screening only.
- Boundary: no Qlib baseline replacement, no new model training, no live trading, no evaluator definition changes.

## Conclusion

The factor research toolchain is ready for large-scale multi-source screening and research judgement.

## Readiness Checks

| check_id | status | detail | recommendation |
| --- | --- | --- | --- |
| prefilter_policy | pass | catalog=data_quality,tradability; manifest=data_quality,tradability | Keep data_quality and tradability as mandatory prefilters for every new factor source. |
| open_source_evaluator_systems | pass | systems=alphalens_reloaded,jqfactor_analyzer,qlib_eval,project_current | Do not replace external evaluator definitions; keep Alphalens Reloaded, jqfactor_analyzer, Qlib eval, and project_current coexisting. |
| batch_runner | pass | batch_configs=4 | Use the batch runner for large jobs, with dry-run, resume, manifests, and logs. |
| required_output_contracts | pass | missing_or_failed=0 | Repair missing contracts before launching full-scale screening. |
| runnable_factor_inventory | pass | total_runnable=311 | Use Alpha158 as the reference path and promoted TA/Alpha101 sources to validate the multi-source machinery before adding more families. |
| new_source_adapter_inventory | pass | new_source_runnable=141 | Keep the promoted non-Alpha158 catalog as a large-scale screening input and add later sources through the same adapter gate. |
| generic_multi_source_screening | pass | contracts=6, failed=0 | Use the generic multi-source screening contract as the entry point for Alpha158, TA, Alpha101, and future factors. |
| generic_multi_source_judgement | pass | contracts=4, failed=0 | Use the multi-source judgement board to triage Alpha158, TA, Alpha101, and future promoted factors before model training. |

## Catalog Summary

| catalog_id | path | status | factor_count | enabled_count | runnable_count | role |
| --- | --- | --- | --- | --- | --- | --- |
| project_main_catalog | factor_research/factor_catalog.yaml | pass | 15 | 15 | 15 | Project planning catalog and currently registered seed factors. |
| alpha158_full_runnable_catalog | outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml | pass | 155 | 155 | 155 | Promoted Qlib Alpha158 catalog after expression validation and V4 batch evaluation. |
| ta_promoted_catalog | outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml | pass | 77 | 77 | 77 | Promoted TA factors after adapter smoke and remaining batch V4 validation. |
| kunquant_alpha101_metadata_catalog | outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml | pass | 82 | 0 | 0 | KunQuant Alpha101 metadata catalog after source audit; adapter pending and non-runnable. |
| kunquant_alpha101_promoted_catalog | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_promoted64.yaml | pass | 64 | 64 | 64 | Promoted KunQuant Alpha101 factors after smoke and candidate71 batch V4 evaluation. |
| qlib_alpha360_smoke_catalog | outputs/factor_catalog_alpha360_v1/alpha360_catalog_smoke.yaml | pass | 24 | 0 | 0 | Qlib Alpha360 smoke catalog after source audit; disabled/non-runnable until V4 evaluation. |
| qlib_alpha360_batch_candidate_catalog | outputs/factor_catalog_alpha360_v1/alpha360_catalog_batch_candidate358.yaml | pass | 358 | 0 | 0 | Qlib Alpha360 batch candidate catalog after smoke V4; disabled/non-runnable until batch promotion. |

## Source Readiness

| source_project | declared_status | license | local_path_status | source_file_status | runnable_factor_count | readiness | readiness_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ginkgo_alpha101 | metadata_registered_adapter_pending | MIT | available | available | 0 | adapter_pending | source registered but calculation adapter is not promoted |
| qlib_alpha360 | source_audit_adapter_smoke_pending | MIT | available | available | 0 | adapter_pending | source registered but calculation adapter is not promoted |
| kunquant_alpha101 | source_audit_passed_adapter_pending | Apache-2.0 | available | available | 64 | ready | runnable catalog entries available |
| qlib_alpha158 | formula_inventory_passed_expression_adapter_pending | MIT | available | available | 155 | ready | runnable catalog entries available |
| ta | metadata_registered_adapter_pending | MIT | available | available | 77 | ready | runnable catalog entries available |
| qlib_factor_platform_presets | design_reference | MIT | available | available | 0 | reference_only | design reference, not a runnable factor source |
| alphalens_reloaded | factor_research/external/adapters.py::to_alphalens_factor_data | Apache-2.0 | available | available | 0 | reference_or_evaluator | Primary open-source factor evaluation reference. |
| factortest | future data inventory and exposure adapters | MIT | available | available | 0 | reference_or_evaluator | A-share data layer, factor test, industry/style exposure reference. |
| jqfactor_analyzer | factor_research/external/adapters.py::to_jqfactor_inputs | MIT | available | available | 0 | reference_or_evaluator | A-share style factor analysis reference with group, neutralization, and Chinese reporting conventions. |
| kunquant | factor_research/alpha101_source.py::compute_alpha101_features | Apache-2.0 | available | available | 0 | reference_or_evaluator | Alpha101/Alpha158 formula and high-performance factor calculation reference. |
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
| multi_source_screening_input | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_screening_input.csv | pass | 319 | 200 | 173225 |
| multi_source_candidate_board | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_candidate_board.csv | pass | 319 | 200 | 192054 |
| multi_source_candidate_pool | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_candidate_pool.csv | pass | 319 | 200 | 192054 |
| multi_source_alpha_candidates | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_alpha_candidates.csv | pass | 14 | 1 | 8594 |
| multi_source_holdouts | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_holdouts.csv | pass | 23 | 1 | 11872 |
| multi_source_contract_status | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_contract_status.csv | pass | 7 | 7 | 316 |
| multi_source_judgement_board | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv | pass | 319 | 300 | 179814 |
| multi_source_research_candidates | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_research_candidates.csv | pass | 43 | 1 | 26427 |
| multi_source_new_source_alpha_probes | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv | pass | 29 | 5 | 20229 |
| multi_source_judgement_contract_status | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_judgement_contract_status.csv | pass | 6 | 6 | 378 |
| open_source_factor_expansion_candidates | source_expansion_audit | outputs/open_source_factor_expansion_audit_v1/current/open_source_factor_source_candidates.csv | pass | 8 | 8 | 5113 |
| open_source_factor_expansion_next_steps | source_expansion_audit | outputs/open_source_factor_expansion_audit_v1/current/open_source_factor_expansion_next_steps.csv | pass | 3 | 3 | 467 |
| alpha360_formula_inventory | alpha360_source_audit | outputs/factor_catalog_alpha360_v1/alpha360_formula_inventory.csv | pass | 360 | 360 | 96173 |
| alpha360_smoke_catalog | alpha360_source_audit | outputs/factor_catalog_alpha360_v1/alpha360_catalog_smoke.yaml | pass | 24 | 24 | 14817 |
| alpha360_smoke_expression_table | alpha360_adapter_smoke | outputs/alpha360_expression_frame_v1/smoke/expression_table.csv | pass | 24 | 24 | 6485 |
| alpha360_smoke_expression_summary | alpha360_adapter_smoke | outputs/alpha360_expression_frame_v1/smoke/expression_frame_summary.csv | pass | 24 | 24 | 2948 |
| alpha360_smoke_external_factor_summary | alpha360_v4_smoke | outputs/factor_evaluation_v4/alpha360_smoke_v1/external_factor_frame/external_factor_frame_summary.csv | pass | 22 | 22 | 1127 |
| alpha360_smoke_evaluator_status | alpha360_v4_smoke | outputs/factor_evaluation_v4/alpha360_smoke_v1/evaluator_status.csv | pass | 66 | 66 | 9872 |
| alpha360_smoke_metric_index | alpha360_v4_smoke | outputs/factor_evaluation_v4/alpha360_smoke_v1/open_source_metric_index.csv | pass | 396 | 1 | 83230 |
| alpha360_smoke_context_metric_index | alpha360_v4_smoke | outputs/factor_evaluation_v4/alpha360_smoke_v1/context/context_metric_index.csv | pass | 4224 | 1 | 1369306 |
| alpha360_batch_candidate_catalog | alpha360_batch_catalog | outputs/factor_catalog_alpha360_v1/alpha360_catalog_batch_candidate358.yaml | pass | 358 | 358 | 232594 |
| alpha360_adapter_holdout_catalog | alpha360_batch_catalog | outputs/factor_catalog_alpha360_v1/alpha360_catalog_adapter_holdout2.yaml | pass | 2 | 2 | 1805 |
| alpha360_batch_catalog_audit | alpha360_batch_catalog | outputs/factor_catalog_alpha360_v1/alpha360_batch_catalog_audit.csv | pass | 4 | 4 | 425 |
| alpha360_batch_dry_run_manifest | alpha360_batch_dry_run | outputs/factor_evaluation_batch_v1/alpha360_candidate358_batch1/batch_manifest.csv | pass | 72 | 72 | 27210 |
| alpha360_batch_dry_run_selected_catalog | alpha360_batch_dry_run | outputs/factor_evaluation_batch_v1/alpha360_candidate358_batch1/selected_factor_catalog.csv | pass | 358 | 358 | 138212 |
| alpha101_source_summary | alpha101_source_audit | outputs/factor_catalog_alpha101_v1/source_audit/alpha101_source_summary.csv | pass | 2 | 2 | 574 |
| kunquant_alpha101_inventory | alpha101_source_audit | outputs/factor_catalog_alpha101_v1/source_audit/kunquant_alpha101_inventory.csv | pass | 82 | 80 | 19926 |
| kunquant_alpha101_metadata_catalog | alpha101_source_audit | outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml | pass | 82 | 80 | 51857 |
| alpha101_adapter_inventory | alpha101_adapter | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_inventory.csv | pass | 82 | 80 | 19466 |
| alpha101_smoke_external_factor_summary | alpha101_v4_smoke | outputs/factor_evaluation_v4/alpha101_smoke_v1/external_factor_frame/external_factor_frame_summary.csv | pass | 5 | 5 | 341 |
| alpha101_smoke_evaluator_status | alpha101_v4_smoke | outputs/factor_evaluation_v4/alpha101_smoke_v1/evaluator_status.csv | pass | 15 | 15 | 2633 |
| alpha101_smoke_metric_index | alpha101_v4_smoke | outputs/factor_evaluation_v4/alpha101_smoke_v1/open_source_metric_index.csv | pass | 90 | 1 | 20988 |
| alpha101_smoke_promotion_audit | alpha101_adapter | outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_smoke_promotion_audit.csv | pass | 5 | 5 | 470 |
| alpha101_smoke_passed_catalog | alpha101_adapter | outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_catalog_smoke_passed.yaml | pass | 5 | 5 | 4082 |
| alpha101_batch_candidate_catalog | alpha101_adapter | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_batch_candidate71.yaml | pass | 71 | 70 | 42641 |
| alpha101_adapter_holdout_catalog | alpha101_adapter | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_adapter_holdout6.yaml | pass | 6 | 1 | 4322 |
| alpha101_batch_promotion_audit | alpha101_adapter | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_batch_promotion_audit.csv | pass | 71 | 70 | 6912 |
| alpha101_batch_promoted_catalog | alpha101_adapter | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_promoted64.yaml | pass | 64 | 60 | 38088 |
| alpha101_holdout_catalog | alpha101_adapter | outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_holdout18.yaml | pass | 18 | 1 | 11857 |
| alpha101_candidate71_batch_metric_index | alpha101_v4_batch | outputs/factor_evaluation_batch_v1/alpha101_candidate71_batch1/alpha101_candidate71_metric_index.csv | pass | 1170 | 1 | 320385 |
| alpha101_candidate71_batch_manifest | alpha101_v4_batch | outputs/factor_evaluation_batch_v1/alpha101_candidate71_batch1/batch_manifest.csv | pass | 15 | 15 | 6488 |

## Stage Counts

| catalog_id | source_project | stage | enabled | runnable | factor_count |
| --- | --- | --- | --- | --- | --- |
| alpha158_full_runnable_catalog | qlib_alpha158 | alpha158_first20_v4_smoke_passed | True | True | 20 |
| alpha158_full_runnable_catalog | qlib_alpha158 | alpha158_remaining138_v4_batch_passed | True | True | 135 |
| kunquant_alpha101_metadata_catalog | kunquant_alpha101 | alpha101_source_audit_adapter_pending | False | False | 82 |
| kunquant_alpha101_promoted_catalog | kunquant_alpha101 | alpha101_adapter_v4_batch_passed | True | True | 59 |
| kunquant_alpha101_promoted_catalog | kunquant_alpha101 | alpha101_adapter_v4_smoke_passed | True | True | 5 |
| project_main_catalog | qlib_baseline_basic | current_v4_seed | True | True | 5 |
| project_main_catalog | qlib_baseline_basic | project_basic_available | True | True | 10 |
| qlib_alpha360_batch_candidate_catalog | qlib_alpha360 | alpha360_adapter_batch_v4_pending | False | False | 358 |
| qlib_alpha360_smoke_catalog | qlib_alpha360 | alpha360_smoke_adapter_pending | False | False | 24 |
| ta_promoted_catalog | ta | ta_adapter_v4_batch_passed | True | True | 72 |
| ta_promoted_catalog | ta | ta_adapter_v4_smoke_passed | True | True | 5 |

## Next Step

1. Keep Alpha158 as the validated reference pipeline, not the next research bottleneck.
2. Treat promoted TA and Alpha101 catalogs as the first non-Alpha158 screening inputs.
3. Use the generic multi-source screening and judgement contracts before promoting new-source factors into model or portfolio inputs.
4. Continue Qlib Alpha360 through V4 smoke before any promotion.
5. Start broad factor discovery by adding more open-source factor families through the same adapter, V4 batch, promotion, holdout, and judgement gates.
