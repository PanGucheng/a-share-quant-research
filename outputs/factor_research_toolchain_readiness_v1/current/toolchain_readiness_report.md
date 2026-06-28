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
| batch_runner | pass | batch_configs=7 | Use the batch runner for large jobs, with dry-run, resume, manifests, and logs. |
| required_output_contracts | pass | missing_or_failed=0 | Repair missing contracts before launching full-scale screening. |
| runnable_factor_inventory | pass | total_runnable=669 | Use Alpha158 as the reference path and promoted TA/Alpha101/Alpha360 sources to validate the multi-source machinery before adding more families. |
| new_source_adapter_inventory | pass | new_source_runnable=499 | Keep the promoted non-Alpha158 catalog as a large-scale screening input and add later sources through the same adapter gate. |
| generic_multi_source_screening | pass | contracts=6, failed=0 | Use the generic multi-source screening contract as the entry point for Alpha158, TA, Alpha101, Alpha360, and future factors. |
| generic_multi_source_judgement | pass | contracts=4, failed=0 | Use the multi-source judgement board to triage Alpha158, TA, Alpha101, Alpha360, and future promoted factors before model training. |
| new_source_probe_diagnostics | pass | contracts=8, failed=0 | Use probe diagnostics for correlation, tradability exposure, stability, and portfolio-smoke checks before training. |
| new_source_probe_review | pass | contracts=6, failed=0 | Use probe review actions to separate redundancy, tradability exposure, and strict OOS-extension candidates. |
| alpha360_strict_oos_extension | pass | contracts=5, failed=0 | Use strict OOS outputs as the recent-window diagnostic reference for reviewed Alpha360 probes. |
| alpha360_strict_oos_stability | pass | contracts=3, failed=0 | Use main-vs-recent stability outputs to keep strict OOS candidates in the research queue. |
| tradability_exposure_attribution | pass | contracts=3, failed=0 | Use exposure attribution actions before residualized evaluation or raw-factor training. |
| exposure_data_capability_audit | pass | contracts=3, failed=0 | Use exposure data capability outputs to decide whether size, industry, Barra, or liquidity residualization can run. |

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
| qlib_alpha360_promoted_catalog | outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml | pass | 358 | 358 | 358 | Promoted Qlib Alpha360 factors after candidate358 batch V4 evaluation. |

## Source Readiness

| source_project | declared_status | license | local_path_status | source_file_status | runnable_factor_count | readiness | readiness_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ginkgo_alpha101 | metadata_registered_adapter_pending | MIT | available | available | 0 | adapter_pending | source registered but calculation adapter is not promoted |
| kunquant_alpha101 | source_audit_passed_adapter_pending | Apache-2.0 | available | available | 64 | ready | runnable catalog entries available |
| qlib_alpha158 | formula_inventory_passed_expression_adapter_pending | MIT | available | available | 155 | ready | runnable catalog entries available |
| qlib_alpha360 | batch_v4_promoted | MIT | available | available | 358 | ready | runnable catalog entries available |
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
| multi_source_screening_input | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_screening_input.csv | pass | 679 | 600 | 380230 |
| multi_source_candidate_board | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_candidate_board.csv | pass | 679 | 600 | 426019 |
| multi_source_candidate_pool | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_candidate_pool.csv | pass | 679 | 600 | 426019 |
| multi_source_alpha_candidates | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_alpha_candidates.csv | pass | 14 | 1 | 8650 |
| multi_source_holdouts | multi_source_candidate_pool | outputs/multi_source_screening_v1/current/multi_source_holdouts.csv | pass | 25 | 1 | 12582 |
| multi_source_contract_status | multi_source_screening | outputs/multi_source_screening_v1/current/multi_source_contract_status.csv | pass | 7 | 7 | 316 |
| multi_source_judgement_board | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv | pass | 679 | 600 | 417483 |
| multi_source_research_candidates | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_research_candidates.csv | pass | 342 | 300 | 224070 |
| multi_source_new_source_alpha_probes | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv | pass | 328 | 300 | 217816 |
| multi_source_judgement_contract_status | multi_source_judgement | outputs/multi_source_judgement_v1/current/multi_source_judgement_contract_status.csv | pass | 6 | 6 | 380 |
| new_source_probe_inventory | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/new_source_probe_inventory.csv | pass | 328 | 328 | 217816 |
| new_source_probe_diagnostic_board | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostic_board.csv | pass | 328 | 328 | 273650 |
| selected_probe_factor_coverage | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/selected_probe_factor_coverage.csv | pass | 120 | 120 | 10677 |
| selected_probe_correlation_top_pairs | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/selected_probe_correlation_top_pairs.csv | pass | 200 | 100 | 15482 |
| selected_probe_tradability_exposure | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/selected_probe_tradability_exposure.csv | pass | 120 | 120 | 20473 |
| portfolio_smoke_weights | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/portfolio_smoke_weights.csv | pass | 50 | 50 | 2992 |
| portfolio_smoke_summary | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/portfolio_smoke_summary.csv | pass | 1 | 1 | 845 |
| new_source_probe_diagnostics_contract_status | new_source_probe_diagnostics | outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_contract_status.csv | pass | 6 | 6 | 289 |
| probe_review_board | new_source_probe_review | outputs/new_source_probe_review_v1/current/probe_review_board.csv | pass | 328 | 328 | 289515 |
| probe_review_redundancy_pairs | new_source_probe_review | outputs/new_source_probe_review_v1/current/redundancy_pairs.csv | pass | 200 | 1 | 15422 |
| probe_review_redundancy_groups | new_source_probe_review | outputs/new_source_probe_review_v1/current/redundancy_groups.csv | pass | 4 | 1 | 1928 |
| probe_review_tradability_exposure_watchlist | new_source_probe_review | outputs/new_source_probe_review_v1/current/tradability_exposure_watchlist.csv | pass | 19 | 1 | 3453 |
| probe_review_oos_extension_candidates | new_source_probe_review | outputs/new_source_probe_review_v1/current/oos_extension_candidates.csv | pass | 3 | 3 | 4828 |
| probe_review_contract_status | new_source_probe_review | outputs/new_source_probe_review_v1/current/probe_review_contract_status.csv | pass | 6 | 6 | 291 |
| alpha360_strict_oos_expression_summary | alpha360_strict_oos_extension | outputs/alpha360_strict_oos_extension_v1/current/strict_oos_expression_summary.csv | pass | 3 | 3 | 441 |
| alpha360_strict_oos_batch_manifest | alpha360_strict_oos_extension | outputs/alpha360_strict_oos_extension_v1/current/strict_oos_batch_manifest.csv | pass | 1 | 1 | 451 |
| alpha360_strict_oos_metric_summary | alpha360_strict_oos_extension | outputs/alpha360_strict_oos_extension_v1/current/strict_oos_metric_summary.csv | pass | 3 | 3 | 1053 |
| alpha360_strict_oos_evaluator_status | alpha360_strict_oos_extension | outputs/alpha360_strict_oos_extension_v1/current/strict_oos_evaluator_status.csv | pass | 9 | 9 | 1679 |
| alpha360_strict_oos_contract_status | alpha360_strict_oos_extension | outputs/alpha360_strict_oos_extension_v1/current/strict_oos_contract_status.csv | pass | 8 | 8 | 433 |
| alpha360_strict_oos_stability_metrics | alpha360_strict_oos_stability | outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_metrics.csv | pass | 54 | 54 | 8735 |
| alpha360_strict_oos_stability_summary | alpha360_strict_oos_stability | outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_summary.csv | pass | 3 | 3 | 645 |
| alpha360_strict_oos_stability_contract_status | alpha360_strict_oos_stability | outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_contract_status.csv | pass | 8 | 8 | 470 |
| tradability_exposure_attribution_board | tradability_exposure_attribution | outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_board.csv | pass | 19 | 19 | 7404 |
| tradability_exposure_action_summary | tradability_exposure_attribution | outputs/tradability_exposure_attribution_v1/current/tradability_exposure_action_summary.csv | pass | 5 | 1 | 272 |
| tradability_exposure_contract_status | tradability_exposure_attribution | outputs/tradability_exposure_attribution_v1/current/tradability_exposure_contract_status.csv | pass | 6 | 6 | 314 |
| exposure_data_capability_board | exposure_data_capability_audit | outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_board.csv | pass | 6 | 6 | 794 |
| exposure_data_provider_field_probe | exposure_data_capability_audit | outputs/exposure_data_capability_audit_v1/current/provider_field_probe.csv | pass | 14 | 14 | 1146 |
| exposure_data_capability_contract_status | exposure_data_capability_audit | outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_contract_status.csv | pass | 6 | 6 | 357 |
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
| alpha360_batch_expression_table | alpha360_batch_adapter | outputs/alpha360_expression_frame_v1/batch358/expression_table.csv | pass | 358 | 358 | 95658 |
| alpha360_batch_expression_summary | alpha360_batch_adapter | outputs/alpha360_expression_frame_v1/batch358/expression_frame_summary.csv | pass | 358 | 358 | 44933 |
| alpha360_batch_smoke_manifest | alpha360_batch_smoke | outputs/factor_evaluation_batch_v1/alpha360_candidate358_smoke_batch1/batch_manifest.csv | pass | 1 | 1 | 505 |
| alpha360_batch_smoke_output_summary | alpha360_batch_smoke | outputs/factor_evaluation_batch_v1/alpha360_candidate358_smoke_batch1/batch_output_summary.csv | pass | 1 | 1 | 346 |
| alpha360_execution_manifest | alpha360_v4_batch | outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/batch_manifest.csv | pass | 72 | 72 | 28174 |
| alpha360_execution_output_summary | alpha360_v4_batch | outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/batch_output_summary.csv | pass | 72 | 72 | 16392 |
| alpha360_candidate358_metric_index | alpha360_v4_batch | outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/alpha360_candidate358_metric_index.csv | pass | 6444 | 1 | 1648440 |
| alpha360_batch_promotion_audit | alpha360_promotion | outputs/factor_catalog_alpha360_v1/alpha360_batch_promotion_audit.csv | pass | 358 | 358 | 30561 |
| alpha360_batch_promoted_catalog | alpha360_promotion | outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml | pass | 358 | 358 | 225871 |
| alpha360_holdout_catalog | alpha360_promotion | outputs/factor_catalog_alpha360_v1/alpha360_catalog_holdout2.yaml | pass | 2 | 2 | 1902 |
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
| qlib_alpha360_promoted_catalog | qlib_alpha360 | alpha360_adapter_v4_batch_passed | True | True | 358 |
| qlib_alpha360_smoke_catalog | qlib_alpha360 | alpha360_smoke_adapter_pending | False | False | 24 |
| ta_promoted_catalog | ta | ta_adapter_v4_batch_passed | True | True | 72 |
| ta_promoted_catalog | ta | ta_adapter_v4_smoke_passed | True | True | 5 |

## Next Step

1. Keep Alpha158 as the validated reference pipeline, not the next research bottleneck.
2. Treat promoted TA, Alpha101, and Alpha360 catalogs as the first large non-Alpha158 screening inputs.
3. Use the generic multi-source screening and judgement contracts before promoting new-source factors into model or portfolio inputs.
4. Use probe review actions to prioritize strict OOS extension and exposure-data diagnostics before training.
5. Use strict OOS extension outputs as stability diagnostics, not as automatic training admission.
6. Use main-vs-recent stability to keep candidates in research status until exposure diagnostics are ready.
7. Use tradability exposure attribution before raw-factor training or residualized evaluation.
8. Use exposure data capability audit before industry, size, or Barra neutralization.
9. Start broad factor discovery by adding more open-source factor families through the same adapter, V4 batch, promotion, holdout, and judgement gates.
