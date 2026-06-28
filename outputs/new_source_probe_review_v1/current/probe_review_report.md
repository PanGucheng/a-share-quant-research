# New-Source Probe Review V1

- Diagnostic board: `outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostic_board.csv`
- Scope: review triage only; no model training, no strategy optimization, no evaluator definition changes.

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| review_board_rows | pass | rows=328 |
| redundancy_pairs_present | pass | pairs=200 |
| redundancy_groups_present | pass | groups=4 |
| tradability_exposure_watchlist_present | pass | watchlist=19 |
| oos_candidates_present | pass | candidates=3 |
| no_downstream_default | pass | downstream_default=0 |

## Review Action Counts

| source_family | review_action | count |
| --- | --- | --- |
| alpha101 | metric_only_defer | 6 |
| alpha101 | tradability_exposure_review | 8 |
| alpha360 | frame_review_candidate | 13 |
| alpha360 | metric_only_defer | 199 |
| alpha360 | redundancy_representative_review | 3 |
| alpha360 | redundant_holdout_candidate | 84 |
| ta | frame_review_candidate | 1 |
| ta | metric_only_defer | 3 |
| ta | tradability_exposure_review | 11 |

## Redundancy Groups

| group_id | representative_factor | group_size | source_families | factor_list |
| --- | --- | --- | --- | --- |
| redundancy_group_001 | ta_momentum_kama | 12 | alpha101,ta | kunquant_alpha101_alpha005,kunquant_alpha101_alpha041,kunquant_alpha101_alpha042,ta_momentum_kama,ta_trend_ema_fast,ta_trend_ichimoku_b,ta_trend_ichimoku_conv,ta_trend_sma_fast,ta_volatility_kcc,ta_volatility_kch,ta_volatility_kcl,ta_volume_vwap |
| redundancy_group_002 | alpha360_HIGH40 | 80 | alpha360 | alpha360_CLOSE38,alpha360_CLOSE39,alpha360_CLOSE40,alpha360_CLOSE41,alpha360_CLOSE42,alpha360_CLOSE43,alpha360_CLOSE44,alpha360_CLOSE45,alpha360_CLOSE46,alpha360_CLOSE47,alpha360_CLOSE48,alpha360_CLOSE49,alpha360_CLOSE50,alpha360_CLOSE51,alpha360_CLOSE52,alpha360_CLOSE53,alpha360_HIGH38,alpha360_HIGH39,alpha360_HIGH40,alpha360_HIGH41,alpha360_HIGH42,alpha360_HIGH43,alpha360_HIGH44,alpha360_HIGH45,alpha360_HIGH46,alpha360_HIGH47,alpha360_HIGH48,alpha360_HIGH49,alpha360_HIGH50,alpha360_HIGH51,alpha360_HIGH52,alpha360_HIGH53,alpha360_HIGH54,alpha360_LOW38,alpha360_LOW39,alpha360_LOW40,alpha360_LOW41,alpha360_LOW42,alpha360_LOW43,alpha360_LOW44,alpha360_LOW45,alpha360_LOW46,alpha360_LOW47,alpha360_LOW48,alpha360_LOW49,alpha360_LOW50,alpha360_OPEN37,alpha360_OPEN38,alpha360_OPEN39,alpha360_OPEN40,alpha360_OPEN41,alpha360_OPEN42,alpha360_OPEN43,alpha360_OPEN44,alpha360_OPEN45,alpha360_OPEN46,alpha360_OPEN47,alpha360_OPEN48,alpha360_OPEN49,alpha360_OPEN50,alpha360_OPEN51,alpha360_OPEN52,alpha360_OPEN53,alpha360_VWAP38,alpha360_VWAP39,alpha360_VWAP40,alpha360_VWAP41,alpha360_VWAP42,alpha360_VWAP43,alpha360_VWAP44,alpha360_VWAP45,alpha360_VWAP46,alpha360_VWAP47,alpha360_VWAP48,alpha360_VWAP49,alpha360_VWAP50,alpha360_VWAP51,alpha360_VWAP52,alpha360_VWAP53,alpha360_VWAP54 |
| redundancy_group_003 | alpha360_HIGH37 | 4 | alpha360 | alpha360_CLOSE37,alpha360_HIGH37,alpha360_OPEN36,alpha360_VWAP37 |
| redundancy_group_004 | alpha360_HIGH36 | 3 | alpha360 | alpha360_HIGH36,alpha360_OPEN35,alpha360_VWAP36 |

## Tradability Exposure Watchlist

| factor | mean_spearman_liquidity_value | liquidity_value_date_count | mean_spearman_liquidity_bucket | liquidity_bucket_date_count | mean_spearman_tradability_score | tradability_score_date_count | high_liquidity_z_mean | low_liquidity_z_mean | high_minus_low_liquidity_z | max_abs_tradability_exposure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha083 | -0.784104 | 40 | -0.761590 | 40 | -0.628829 | 40 | -0.356860 | 0.471912 | -0.828772 | 0.784104 |
| ta_volatility_atr | 0.721224 | 40 | 0.697949 | 40 | 0.525581 | 40 | 0.370638 | -0.450581 | 0.821220 | 0.721224 |
| kunquant_alpha101_alpha042 | -0.657406 | 40 | -0.634948 | 40 | -0.489410 | 40 | -0.267459 | 0.269146 | -0.536605 | 0.657406 |
| kunquant_alpha101_alpha041 | 0.657051 | 40 | 0.634574 | 40 | 0.489918 | 40 | 0.386002 | -0.463089 | 0.849090 | 0.657051 |
| kunquant_alpha101_alpha005 | -0.656661 | 40 | -0.634614 | 40 | -0.488510 | 40 | -0.563299 | 0.670108 | -1.233407 | 0.656661 |
| ta_volatility_kch | 0.654013 | 40 | 0.631549 | 40 | 0.487921 | 40 | 0.385063 | -0.460832 | 0.845895 | 0.654013 |
| ta_trend_ichimoku_conv | 0.651987 | 40 | 0.629777 | 40 | 0.487376 | 40 | 0.387102 | -0.463416 | 0.850519 | 0.651987 |
| ta_trend_ema_fast | 0.649670 | 40 | 0.627139 | 40 | 0.484550 | 40 | 0.388857 | -0.461152 | 0.850009 | 0.649670 |
| ta_volatility_kcc | 0.649433 | 40 | 0.627335 | 40 | 0.485562 | 40 | 0.385588 | -0.462591 | 0.848179 | 0.649433 |
| ta_volume_vwap | 0.648960 | 40 | 0.626905 | 40 | 0.485329 | 40 | 0.387869 | -0.464278 | 0.852146 | 0.648960 |
| ta_trend_sma_fast | 0.648570 | 40 | 0.626371 | 40 | 0.485077 | 40 | 0.385574 | -0.462696 | 0.848270 | 0.648570 |
| ta_volatility_kcl | 0.644547 | 40 | 0.622254 | 40 | 0.482805 | 40 | 0.388524 | -0.462677 | 0.851201 | 0.644547 |
| ta_momentum_kama | 0.642989 | 40 | 0.621540 | 40 | 0.482527 | 40 | 0.426164 | -0.481823 | 0.907988 | 0.642989 |
| ta_trend_ichimoku_b | 0.636455 | 40 | 0.613776 | 40 | 0.477290 | 40 | 0.388400 | -0.459344 | 0.847744 | 0.636455 |
| kunquant_alpha101_alpha094 | -0.463381 | 40 | -0.446381 | 40 | -0.301414 | 40 | -0.443568 | 0.521929 | -0.965498 | 0.463381 |
| kunquant_alpha101_alpha011 | -0.443038 | 40 | -0.418437 | 40 | -0.336248 | 40 | -0.285677 | 0.365132 | -0.650809 | 0.443038 |
| kunquant_alpha101_alpha040 | -0.430243 | 40 | -0.418429 | 40 | -0.327467 | 40 | -0.361895 | 0.489752 | -0.851646 | 0.430243 |
| ta_volatility_kcw | 0.331646 | 40 | 0.320855 | 40 | 0.180566 | 40 | 0.311398 | -0.319188 | 0.630586 | 0.331646 |
| kunquant_alpha101_alpha088 | -0.317993 | 40 | -0.314466 | 40 | -0.175520 | 40 | -0.307111 | 0.325709 | -0.632820 | 0.317993 |

## OOS Extension Candidates

| pool_name | factor | source_family | source_project | category | screening_gate | promotion_decision | promotion_reason | upstream_role | judgement_role | research_included | downstream_default_included | judgement_label | judgement_reason | source_policy | expected_direction | consensus_direction | consensus_direction_sign | direction_agreement_count | direction_observation_count | direction_agreement_ratio | primary_mean_ic | max_abs_mean_ic | max_abs_qlib_ir | max_abs_ann_alpha | coverage | missing_rate | valid_rows | total_rows | metric_value_count | alphalens_status | jqfactor_status | qlib_status | alphalens_mean_ic_10d | alphalens_mean_ic_20d | jqfactor_mean_ic_10d | jqfactor_mean_ic_20d | qlib_information_ratio_10d | qlib_information_ratio_20d | alphalens_ann_alpha_10d | alphalens_ann_alpha_20d | judgement_issue_tags | license | compute_adapter | frame_diagnostic_selected | portfolio_smoke_selected | horizon_pair_count | horizon_consistent_count | horizon_consistency_ratio | frame_status | valid_rows_frame | total_rows_frame | coverage_frame | missing_rate_frame | strongest_corr_factor | strongest_corr | strongest_abs_corr | mean_spearman_liquidity_value | liquidity_value_date_count | mean_spearman_liquidity_bucket | liquidity_bucket_date_count | mean_spearman_tradability_score | tradability_score_date_count | high_liquidity_z_mean | low_liquidity_z_mean | high_minus_low_liquidity_z | max_abs_tradability_exposure | high_redundancy_watch | high_tradability_exposure_watch | horizon_unstable_watch | diagnostic_label | max_abs_tradability_exposure_review | mean_spearman_liquidity_value_review | mean_spearman_liquidity_bucket_review | redundancy_representative | review_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multi_source_judgement_v1 | alpha360_HIGH36 | alpha360 | qlib_alpha360 | alpha360_high_window | strict_screening_input | promoted | required_pass_allowed_partials_only | monitor | new_source_alpha_probe | True | False | strong_signal_probe | passes_strong_ic_qlib_ir_direction_rules | new_source_research_probe_rules | watch | positive | 1 | 6 | 6 | 1.000000 | 0.077548 | 0.077548 | 8.640702 | 0.164544 | 0.993333 | 0.006667 | 88205.000000 | 88797.000000 | 18.000000 | pass | partial_pass | pass | 0.067448 | 0.077548 | 0.067448 | 0.077548 | 6.641171 | 8.640702 | 0.125473 | 0.164544 |  | MIT | qlib_expression_adapter_pending | True | False | 3 | 3 | 1.000000 | available | 88205.000000 | 88797.000000 | 0.993333 | 0.006667 | alpha360_VWAP36 | 0.994735 | 0.994735 | -0.219284 | 40.000000 | -0.220010 | 40.000000 | -0.136029 | 40.000000 | -0.196525 | 0.218567 | -0.415092 | 0.220010 | True | False | False | redundancy_watch | 0.220010 | -0.219284 | -0.220010 | alpha360_HIGH36 | redundancy_representative_review |
| multi_source_judgement_v1 | alpha360_HIGH37 | alpha360 | qlib_alpha360 | alpha360_high_window | strict_screening_input | promoted | required_pass_allowed_partials_only | monitor | new_source_alpha_probe | True | False | strong_signal_probe | passes_strong_ic_qlib_ir_direction_rules | new_source_research_probe_rules | watch | positive | 1 | 6 | 6 | 1.000000 | 0.078303 | 0.078303 | 8.592490 | 0.160038 | 0.993344 | 0.006656 | 88206.000000 | 88797.000000 | 18.000000 | pass | partial_pass | pass | 0.068568 | 0.078303 | 0.068568 | 0.078303 | 6.696397 | 8.592490 | 0.133301 | 0.160038 |  | MIT | qlib_expression_adapter_pending | True | False | 3 | 3 | 1.000000 | available | 88206.000000 | 88797.000000 | 0.993344 | 0.006656 | alpha360_VWAP37 | 0.995177 | 0.995177 | -0.219684 | 40.000000 | -0.221220 | 40.000000 | -0.136195 | 40.000000 | -0.197205 | 0.221636 | -0.418841 | 0.221220 | True | False | False | redundancy_watch | 0.221220 | -0.219684 | -0.221220 | alpha360_HIGH37 | redundancy_representative_review |
| multi_source_judgement_v1 | alpha360_HIGH40 | alpha360 | qlib_alpha360 | alpha360_high_window | strict_screening_input | promoted | required_pass_allowed_partials_only | monitor | new_source_alpha_probe | True | False | strong_signal_probe | passes_strong_ic_qlib_ir_direction_rules | new_source_research_probe_rules | watch | positive | 1 | 6 | 6 | 1.000000 | 0.082376 | 0.082376 | 8.588899 | 0.158233 | 0.993468 | 0.006532 | 88217.000000 | 88797.000000 | 18.000000 | pass | partial_pass | pass | 0.073413 | 0.082376 | 0.073413 | 0.082376 | 6.970457 | 8.588899 | 0.152144 | 0.158233 |  | MIT | qlib_expression_adapter_pending | True | True | 3 | 3 | 1.000000 | available | 88217.000000 | 88797.000000 | 0.993468 | 0.006532 | alpha360_VWAP40 | 0.995515 | 0.995515 | -0.227261 | 40.000000 | -0.229257 | 40.000000 | -0.143745 | 40.000000 | -0.204843 | 0.228004 | -0.432846 | 0.229257 | True | False | False | portfolio_smoke_probe | 0.229257 | -0.227261 | -0.229257 | alpha360_HIGH40 | redundancy_representative_review |

## Notes

- `oos_extension_candidate` is still a research queue label, not a model input.
- Redundant and tradability-exposed probes should be reviewed before any training stage.
