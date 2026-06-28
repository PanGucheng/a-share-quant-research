# New-Source Probe Diagnostics V1

- Probe input: `outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv`
- Output dir: `outputs/new_source_probe_diagnostics_v1/current`
- Scope: diagnostics only; no model training, no strategy optimization, no evaluator definition changes.
- New-source probes remain research queue entries, not downstream defaults.

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| probe_count | pass | probes=328 |
| frame_selection_count | pass | selected=120 |
| portfolio_selection_count | pass | selected=50 |
| correlation_pairs | pass | pairs=200 |
| portfolio_smoke_executed | pass | executed_rebalances=4 |
| new_source_not_downstream_default | pass | downstream_default=0 |

## Source Counts

| source_family | judgement_label | count |
| --- | --- | --- |
| alpha101 | consistent_signal_probe | 6 |
| alpha101 | strong_signal_probe | 8 |
| alpha360 | consistent_signal_probe | 86 |
| alpha360 | strong_signal_probe | 213 |
| ta | consistent_signal_probe | 3 |
| ta | strong_signal_probe | 12 |

## Diagnostic Counts

| source_family | diagnostic_label | count |
| --- | --- | --- |
| alpha101 | metric_only_probe | 6 |
| alpha101 | redundancy_watch | 3 |
| alpha101 | tradability_exposure_watch | 5 |
| alpha360 | frame_diagnostic_probe | 1 |
| alpha360 | metric_only_probe | 199 |
| alpha360 | portfolio_smoke_probe | 39 |
| alpha360 | redundancy_watch | 60 |
| ta | frame_diagnostic_probe | 1 |
| ta | metric_only_probe | 3 |
| ta | portfolio_smoke_probe | 11 |

## Selection

- Frame diagnostics selected: `120`
- Portfolio smoke selected: `50`
- Correlation meta: `{'enabled': True, 'method': 'daily_cross_section_spearman_mean', 'available_factor_count': 120, 'candidate_date_count': 60, 'used_date_count': 60, 'min_instruments': 100}`

## Portfolio Smoke Summary

| start_date | end_date | trading_days | rebalance_count | executed_rebalances | skipped_rebalances | skipped_rebalance_rate | gross_annualized_return | net_annualized_return | universe_annualized_return | gross_annualized_excess | net_annualized_excess | gross_excess_ir | net_excess_ir | net_max_drawdown | average_turnover | max_turnover | average_eligible_count | average_selected_count | label | topk | rebalance_every | cost_bps | min_liquidity_bucket | min_tradability_score | min_capacity_multiple | status | candidate_count | score_policy | score_clip | min_score_components |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-06-07 | 80 | 6 | 4 | 2 | 0.333333 | 0.585825 | 0.576004 | 0.351943 | 0.168969 | 0.161770 | 2.871573 | 2.752063 | -0.035710 | 0.490000 | 1.000000 | 78.000000 | 50.000000 | label_20d_t1 | 50 | 20 | 10.000000 | 3 | 75.000000 | 1.200000 | pass | 50 | equal_directional_zscore_from_probe_consensus | 3.000000 | 5 |

## Top Correlation Pairs

| factor_a | factor_b | mean_daily_spearman_corr | abs_mean_daily_spearman_corr | date_count |
| --- | --- | --- | --- | --- |
| ta_trend_sma_fast | ta_volatility_kcc | 0.999893 | 0.999893 | 56 |
| kunquant_alpha101_alpha041 | kunquant_alpha101_alpha005 | -0.999856 | 0.999856 | 57 |
| ta_volatility_kcc | ta_trend_ema_fast | 0.999811 | 0.999811 | 56 |
| ta_trend_sma_fast | ta_trend_ema_fast | 0.999798 | 0.999798 | 56 |
| kunquant_alpha101_alpha042 | kunquant_alpha101_alpha005 | 0.999775 | 0.999775 | 57 |
| kunquant_alpha101_alpha042 | kunquant_alpha101_alpha041 | -0.999774 | 0.999774 | 60 |
| ta_volume_vwap | ta_trend_sma_fast | 0.999755 | 0.999755 | 55 |
| ta_volatility_kcc | ta_trend_ichimoku_conv | 0.999726 | 0.999726 | 57 |
| ta_volatility_kcc | ta_volatility_kch | 0.999702 | 0.999702 | 57 |
| ta_volume_vwap | ta_trend_ema_fast | 0.999698 | 0.999698 | 55 |
| ta_volume_vwap | ta_volatility_kcc | 0.999680 | 0.999680 | 55 |
| ta_trend_sma_fast | ta_volatility_kcl | 0.999664 | 0.999664 | 56 |
| ta_trend_ichimoku_conv | ta_trend_ema_fast | 0.999656 | 0.999656 | 56 |
| ta_trend_ichimoku_conv | ta_volatility_kch | 0.999648 | 0.999648 | 57 |
| ta_volatility_kcc | ta_volatility_kcl | 0.999648 | 0.999648 | 57 |
| ta_trend_sma_fast | ta_trend_ichimoku_conv | 0.999648 | 0.999648 | 56 |
| ta_trend_sma_fast | ta_volatility_kch | 0.999622 | 0.999622 | 56 |
| ta_trend_ema_fast | ta_volatility_kcl | 0.999612 | 0.999612 | 56 |
| ta_volume_vwap | ta_trend_ichimoku_conv | 0.999610 | 0.999610 | 55 |
| ta_volatility_kch | ta_trend_ema_fast | 0.999563 | 0.999563 | 56 |

## Top Tradability Exposure

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
| alpha360_VOLUME48 | -0.282007 | 40 | -0.279395 | 40 | -0.184803 | 40 | -0.219954 | 0.233610 | -0.453564 | 0.282007 |

## Output Files

- `new_source_probe_inventory.csv`
- `new_source_probe_diagnostic_board.csv`
- `selected_probe_factor_coverage.csv`
- `selected_probe_correlation_summary.csv`
- `selected_probe_correlation_top_pairs.csv`
- `selected_probe_tradability_exposure.csv`
- `portfolio_smoke_summary.csv`
- `portfolio_smoke_weights.csv`
- `portfolio_smoke_liquidity_exposure.csv`
- `new_source_probe_diagnostics_contract_status.csv`
