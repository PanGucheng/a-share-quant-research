# Multi-Source Judgement V1

- Pool name: `multi_source_judgement_v1`
- Scope: research judgement only; no model training, no strategy optimization, no evaluator redefinition.
- Alpha158 roles are preserved from the existing Alpha158 candidate pool.
- TA and Alpha101 promoted factors can become `new_source_alpha_probe`, but are not downstream defaults.

## Rule Snapshot

| min_probe_coverage | max_probe_missing_rate | min_metric_value_count | weak_abs_ic | consistent_abs_ic | strong_abs_ic | consistent_abs_qlib_ir | strong_abs_qlib_ir | min_direction_agreement_ratio | strong_direction_agreement_ratio | min_new_source_probes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.900000 | 0.100000 | 8 | 0.015000 | 0.030000 | 0.050000 | 3.000000 | 4.000000 | 0.670000 | 0.830000 | 5 |

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| row_alignment | pass | source=319, board=319 |
| alpha158_role_preserved | pass | source_alpha=14, board_alpha=14 |
| new_source_probe_count | pass | new_source_alpha_probe=29 |
| holdout_not_research_included | pass | research_included=43 |
| new_source_not_downstream_default | pass | new_source_downstream_default=0 |
| strict_new_source_metrics | pass | strict_new_source_rows=141 |

## Role Counts

| source_family | judgement_role | count |
| --- | --- | --- |
| alpha101 | holdout | 18 |
| alpha101 | new_source_alpha_probe | 14 |
| alpha101 | new_source_data_watch | 16 |
| alpha101 | new_source_mixed_signal | 7 |
| alpha101 | new_source_monitor | 27 |
| alpha158 | alpha_candidate | 14 |
| alpha158 | excluded_high_turnover | 33 |
| alpha158 | excluded_redundant | 55 |
| alpha158 | excluded_unstable_context | 16 |
| alpha158 | holdout | 3 |
| alpha158 | monitor | 37 |
| ta | holdout | 2 |
| ta | new_source_alpha_probe | 15 |
| ta | new_source_data_watch | 43 |
| ta | new_source_mixed_signal | 13 |
| ta | new_source_monitor | 6 |

## Label Counts

| source_family | judgement_label | count |
| --- | --- | --- |
| alpha101 | consistent_signal_probe | 6 |
| alpha101 | data_quality_watch | 16 |
| alpha101 | holdout | 18 |
| alpha101 | mixed_direction | 7 |
| alpha101 | monitor | 9 |
| alpha101 | strong_signal_probe | 8 |
| alpha101 | weak_signal | 18 |
| alpha158 | consistent_signal | 4 |
| alpha158 | high_turnover | 33 |
| alpha158 | holdout | 3 |
| alpha158 | redundant | 55 |
| alpha158 | review | 33 |
| alpha158 | strong_signal | 10 |
| alpha158 | unstable_context | 16 |
| alpha158 | weak_signal | 4 |
| ta | consistent_signal_probe | 3 |
| ta | data_quality_watch | 43 |
| ta | holdout | 2 |
| ta | mixed_direction | 13 |
| ta | monitor | 2 |
| ta | strong_signal_probe | 12 |
| ta | weak_signal | 4 |

## Research Candidates

| factor | source_family | judgement_role | judgement_label | consensus_direction | max_abs_mean_ic | max_abs_qlib_ir |
| --- | --- | --- | --- | --- | --- | --- |
| alpha158_QTLD60 | alpha158 | alpha_candidate | strong_signal | positive |  | 9.130774 |
| alpha158_MIN60 | alpha158 | alpha_candidate | strong_signal | positive |  | 9.095609 |
| alpha158_IMIN60 | alpha158 | alpha_candidate | strong_signal | positive |  | 8.580686 |
| alpha158_MIN30 | alpha158 | alpha_candidate | strong_signal | positive |  | 8.235351 |
| alpha158_ROC60 | alpha158 | alpha_candidate | strong_signal | positive |  | 7.803887 |
| alpha158_ROC30 | alpha158 | alpha_candidate | strong_signal | positive |  | 7.792869 |
| alpha158_QTLD30 | alpha158 | alpha_candidate | strong_signal | positive |  | 7.571623 |
| alpha158_IMIN30 | alpha158 | alpha_candidate | strong_signal | positive |  | 7.026954 |
| alpha158_MIN10 | alpha158 | alpha_candidate | strong_signal | positive |  | 6.863699 |
| alpha158_MIN5 | alpha158 | alpha_candidate | strong_signal | positive |  | 6.534079 |
| alpha158_IMIN20 | alpha158 | alpha_candidate | consistent_signal | positive |  | 5.566941 |
| alpha158_VSUMN60 | alpha158 | alpha_candidate | consistent_signal | positive |  | 4.543268 |
| alpha158_QTLD10 | alpha158 | alpha_candidate | consistent_signal | positive |  | 4.540188 |
| alpha158_ROC10 | alpha158 | alpha_candidate | consistent_signal | positive |  | 3.970544 |
| ta_volatility_atr | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.127568 | 9.604630 |
| ta_volume_vwap | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.120504 | 9.053554 |
| ta_trend_sma_fast | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.119505 | 9.062298 |
| ta_volatility_kcc | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.119373 | 9.147213 |
| ta_trend_ichimoku_conv | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.118935 | 9.110528 |
| ta_volatility_kch | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.118736 | 9.061716 |
| ta_trend_ema_fast | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.118668 | 9.011919 |
| ta_momentum_kama | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.117594 | 9.190937 |
| ta_volatility_kcl | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.117208 | 8.963050 |
| ta_trend_ichimoku_b | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.114848 | 8.553694 |
| ta_volatility_kcw | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.094221 | 8.151400 |
| ta_volatility_ui | ta | new_source_alpha_probe | strong_signal_probe | negative | 0.074378 | 6.496057 |
| ta_trend_adx | ta | new_source_alpha_probe | consistent_signal_probe | negative | 0.049011 | 7.480529 |
| ta_volume_sma_em | ta | new_source_alpha_probe | consistent_signal_probe | positive | 0.038526 | 4.532767 |
| ta_trend_vortex_ind_pos | ta | new_source_alpha_probe | consistent_signal_probe | positive | 0.034170 | 3.914867 |
| kunquant_alpha101_alpha083 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.072538 | 5.668160 |
| kunquant_alpha101_alpha088 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.067655 | 10.102395 |
| kunquant_alpha101_alpha042 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.065690 | 5.387349 |
| kunquant_alpha101_alpha041 | alpha101 | new_source_alpha_probe | strong_signal_probe | negative | 0.065687 | 5.385930 |
| kunquant_alpha101_alpha040 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.064238 | 11.004408 |
| kunquant_alpha101_alpha005 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.062534 | 5.124935 |
| kunquant_alpha101_alpha094 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.058646 | 6.151593 |
| kunquant_alpha101_alpha011 | alpha101 | new_source_alpha_probe | strong_signal_probe | positive | 0.056459 | 5.625899 |
| kunquant_alpha101_alpha064 | alpha101 | new_source_alpha_probe | consistent_signal_probe | negative | 0.036358 | 9.255099 |
| kunquant_alpha101_alpha013 | alpha101 | new_source_alpha_probe | consistent_signal_probe | positive | 0.035391 | 6.452576 |
| kunquant_alpha101_alpha055 | alpha101 | new_source_alpha_probe | consistent_signal_probe | positive | 0.033451 | 6.058841 |
| kunquant_alpha101_alpha074 | alpha101 | new_source_alpha_probe | consistent_signal_probe | negative | 0.032551 | 8.454882 |
| kunquant_alpha101_alpha020 | alpha101 | new_source_alpha_probe | consistent_signal_probe | negative | 0.031684 | 4.412716 |
| kunquant_alpha101_alpha003 | alpha101 | new_source_alpha_probe | consistent_signal_probe | positive | 0.031336 | 7.160174 |

## New Source Alpha Probes

| factor | source_family | judgement_label | consensus_direction | primary_mean_ic | max_abs_mean_ic | max_abs_qlib_ir | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ta_volatility_atr | ta | strong_signal_probe | negative | -0.127568 | 0.127568 | 9.604630 | 0.959502 |
| ta_volume_vwap | ta | strong_signal_probe | negative | -0.120504 | 0.120504 | 9.053554 | 0.912755 |
| ta_trend_sma_fast | ta | strong_signal_probe | negative | -0.119505 | 0.119505 | 9.062298 | 0.925253 |
| ta_volatility_kcc | ta | strong_signal_probe | negative | -0.119373 | 0.119373 | 9.147213 | 0.937750 |
| ta_trend_ichimoku_conv | ta | strong_signal_probe | negative | -0.118935 | 0.118935 | 9.110528 | 0.943998 |
| ta_volatility_kch | ta | strong_signal_probe | negative | -0.118736 | 0.118736 | 9.061716 | 0.997745 |
| ta_trend_ema_fast | ta | strong_signal_probe | negative | -0.118668 | 0.118668 | 9.011919 | 0.937327 |
| ta_momentum_kama | ta | strong_signal_probe | negative | -0.117594 | 0.117594 | 9.190937 | 0.915621 |
| ta_volatility_kcl | ta | strong_signal_probe | negative | -0.117208 | 0.117208 | 8.963050 | 0.997745 |
| ta_trend_ichimoku_b | ta | strong_signal_probe | negative | -0.114848 | 0.114848 | 8.553694 | 0.999812 |
| ta_volatility_kcw | ta | strong_signal_probe | negative | -0.094221 | 0.094221 | 8.151400 | 0.937750 |
| ta_volatility_ui | ta | strong_signal_probe | negative | -0.074378 | 0.074378 | 6.496057 | 0.912755 |
| ta_trend_adx | ta | consistent_signal_probe | negative | -0.049011 | 0.049011 | 7.480529 | 0.967395 |
| ta_volume_sma_em | ta | consistent_signal_probe | positive | 0.038526 | 0.038526 | 4.532767 | 0.906601 |
| ta_trend_vortex_ind_pos | ta | consistent_signal_probe | positive | 0.034170 | 0.034170 | 3.914867 | 0.906601 |
| kunquant_alpha101_alpha083 | alpha101 | strong_signal_probe | positive | 0.072538 | 0.072538 | 5.668160 | 0.952517 |
| kunquant_alpha101_alpha088 | alpha101 | strong_signal_probe | positive | 0.057117 | 0.067655 | 10.102395 | 0.948663 |
| kunquant_alpha101_alpha042 | alpha101 | strong_signal_probe | positive | 0.065690 | 0.065690 | 5.387349 | 0.993685 |
| kunquant_alpha101_alpha041 | alpha101 | strong_signal_probe | negative | -0.065687 | 0.065687 | 5.385930 | 0.993685 |
| kunquant_alpha101_alpha040 | alpha101 | strong_signal_probe | positive | 0.056049 | 0.064238 | 11.004408 | 0.935899 |
| kunquant_alpha101_alpha005 | alpha101 | strong_signal_probe | positive | 0.062534 | 0.062534 | 5.124935 | 0.935899 |
| kunquant_alpha101_alpha094 | alpha101 | strong_signal_probe | positive | 0.058646 | 0.058646 | 6.151593 | 0.923146 |
| kunquant_alpha101_alpha011 | alpha101 | strong_signal_probe | positive | 0.056459 | 0.056459 | 5.625899 | 0.974292 |
| kunquant_alpha101_alpha064 | alpha101 | consistent_signal_probe | negative | -0.027989 | 0.036358 | 9.255099 | 1.000000 |
| kunquant_alpha101_alpha013 | alpha101 | consistent_signal_probe | positive | 0.007253 | 0.035391 | 6.452576 | 0.967854 |
| kunquant_alpha101_alpha055 | alpha101 | consistent_signal_probe | positive | 0.010146 | 0.033451 | 6.058841 | 1.000000 |
| kunquant_alpha101_alpha074 | alpha101 | consistent_signal_probe | negative | -0.032551 | 0.032551 | 8.454882 | 1.000000 |
| kunquant_alpha101_alpha020 | alpha101 | consistent_signal_probe | negative | -0.031684 | 0.031684 | 4.412716 | 0.987213 |
| kunquant_alpha101_alpha003 | alpha101 | consistent_signal_probe | positive | 0.013729 | 0.031336 | 7.160174 | 1.000000 |

## Holdouts

| factor | source_family | promotion_reason | alphalens_status | jqfactor_status | qlib_status |
| --- | --- | --- | --- | --- | --- |
| alpha158_IMAX5 | alpha158 | alphalens=partial_pass | partial_pass | partial_pass | pass |
| alpha158_CNTN5 | alpha158 | alphalens=partial_pass | partial_pass | partial_pass | pass |
| alpha158_RANK5 | alpha158 | alphalens=partial_pass | partial_pass | partial_pass | pass |
| ta_volatility_bbli | ta | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| ta_volatility_kchi | ta | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha081 | alpha101 | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha065 | alpha101 | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha007 | alpha101 | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha099 | alpha101 | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha001 | alpha101 | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha075 | alpha101 | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha019 | alpha101 | nan | nan | nan | nan |
| kunquant_alpha101_alpha021 | alpha101 | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha023 | alpha101 | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha027 | alpha101 | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha032 | alpha101 | nan | nan | nan | nan |
| kunquant_alpha101_alpha036 | alpha101 | nan | nan | nan | nan |
| kunquant_alpha101_alpha037 | alpha101 | nan | nan | nan | nan |
| kunquant_alpha101_alpha039 | alpha101 | nan | nan | nan | nan |
| kunquant_alpha101_alpha052 | alpha101 | nan | nan | nan | nan |
| kunquant_alpha101_alpha061 | alpha101 | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha068 | alpha101 | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha086 | alpha101 | alphalens_reloaded_not_run | not_run | not_run | pass |

## Output Files

- `multi_source_judgement_board.csv`
- `multi_source_research_candidates.csv`
- `multi_source_new_source_alpha_probes.csv`
- `multi_source_judgement_monitor.csv`
- `multi_source_judgement_holdouts.csv`
- `multi_source_judgement_contract_status.csv`
- `multi_source_judgement_pool.json`

## Notes

- This layer only reads already generated evaluator metrics from Alphalens Reloaded, jqfactor_analyzer, and Qlib eval.
- `new_source_alpha_probe` is a research queue, not a trading signal and not an automatic model input.
- Coverage and missing-rate gates are intentionally stricter than source promotion so weak data does not look like alpha.
