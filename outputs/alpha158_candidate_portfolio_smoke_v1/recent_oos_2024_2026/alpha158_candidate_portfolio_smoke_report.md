# Alpha158 Candidate Portfolio Smoke V1

- Candidate pool: `outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv`
- Expression frame: `outputs\alpha158_expression_frame_v1\candidates_recent_oos_2024_2026`
- Tradability dir: `outputs\tradability\all_stock_shsz_liquid2000_2024-01-01_2026-06-09`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_20d_t1`
- Score policy: `equal_directional_zscore`
- Rebalance every: `20` trading days
- TopK: `100`
- Cost: `10.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2024-02-01` |
| end_date | `2026-06-02` |
| trading_days | `560` |
| rebalance_count | `30` |
| executed_rebalances | `28` |
| skipped_rebalances | `2` |
| skipped_rebalance_rate | `0.066667` |
| gross_annualized_return | `0.281803` |
| net_annualized_return | `0.268842` |
| universe_annualized_return | `0.237643` |
| gross_annualized_excess | `0.030122` |
| net_annualized_excess | `0.019804` |
| gross_excess_ir | `0.303577` |
| net_excess_ir | `0.221295` |
| net_max_drawdown | `-0.153772` |
| average_turnover | `0.799286` |
| max_turnover | `1.000000` |
| average_eligible_count | `1071.285714` |
| average_selected_count | `100.000000` |
| label | `label_20d_t1` |
| topk | `100` |
| rebalance_every | `20` |
| cost_bps | `10.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| candidate_count | `14` |
| warning_low_monotonicity_count | `4` |
| positive_direction_count | `14` |
| negative_direction_count | `0` |
| score_policy | `equal_directional_zscore` |
| score_clip | `3.000000` |
| min_score_components | `8` |

## Candidate Weights

| factor | judgement_label | consensus_direction | primary_rank_ic | issue_tags | weight |
| --- | --- | --- | --- | --- | --- |
| alpha158_MIN60 | strong_signal | positive | 0.099945 |  | 1.000000 |
| alpha158_QTLD60 | strong_signal | positive | 0.097826 |  | 1.000000 |
| alpha158_ROC60 | strong_signal | positive | 0.083509 |  | 1.000000 |
| alpha158_MIN30 | strong_signal | positive | 0.083258 |  | 1.000000 |
| alpha158_ROC30 | strong_signal | positive | 0.080597 |  | 1.000000 |
| alpha158_QTLD30 | strong_signal | positive | 0.072863 |  | 1.000000 |
| alpha158_IMIN60 | strong_signal | positive | 0.068445 |  | 1.000000 |
| alpha158_MIN10 | strong_signal | positive | 0.061041 |  | 1.000000 |
| alpha158_IMIN30 | strong_signal | positive | 0.057858 |  | 1.000000 |
| alpha158_MIN5 | strong_signal | positive | 0.055802 | low_monotonicity | 1.000000 |
| alpha158_IMIN20 | consistent_signal | positive | 0.040908 |  | 1.000000 |
| alpha158_QTLD10 | consistent_signal | positive | 0.038871 | low_monotonicity | 1.000000 |
| alpha158_VSUMN60 | consistent_signal | positive | 0.035648 | low_monotonicity | 1.000000 |
| alpha158_ROC10 | consistent_signal | positive | 0.034488 | low_monotonicity | 1.000000 |

## Low Monotonicity Warnings

| factor | judgement_label | consensus_direction | primary_rank_ic | issue_tags | weight |
| --- | --- | --- | --- | --- | --- |
| alpha158_MIN5 | strong_signal | positive | 0.055802 | low_monotonicity | 1.000000 |
| alpha158_QTLD10 | consistent_signal | positive | 0.038871 | low_monotonicity | 1.000000 |
| alpha158_VSUMN60 | consistent_signal | positive | 0.035648 | low_monotonicity | 1.000000 |
| alpha158_ROC10 | consistent_signal | positive | 0.034488 | low_monotonicity | 1.000000 |

## Score Component Coverage

| factor | weight | valid_rows | coverage |
| --- | --- | --- | --- |
| alpha158_MIN60 | 1.000000 | 1093663 | 0.997657 |
| alpha158_QTLD60 | 1.000000 | 1093663 | 0.997657 |
| alpha158_ROC60 | 1.000000 | 1091903 | 0.996052 |
| alpha158_MIN30 | 1.000000 | 1093663 | 0.997657 |
| alpha158_ROC30 | 1.000000 | 1091734 | 0.995898 |
| alpha158_QTLD30 | 1.000000 | 1093663 | 0.997657 |
| alpha158_IMIN60 | 1.000000 | 1096215 | 0.999985 |
| alpha158_MIN10 | 1.000000 | 1093663 | 0.997657 |
| alpha158_IMIN30 | 1.000000 | 1095986 | 0.999777 |
| alpha158_MIN5 | 1.000000 | 1093663 | 0.997657 |
| alpha158_IMIN20 | 1.000000 | 1095763 | 0.999573 |
| alpha158_QTLD10 | 1.000000 | 1093663 | 0.997657 |
| alpha158_VSUMN60 | 1.000000 | 1096214 | 0.999984 |
| alpha158_ROC10 | 1.000000 | 1091859 | 0.996012 |

## First Rebalances

| signal_date | status | eligible_count | selected_count | turnover | execution_date | period_end_date | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-01-02 00:00:00 | skipped_insufficient_eligible_count | 0 | 0 |  | NaT | NaT |  |  |  |  |  |  |
| 2024-01-30 00:00:00 | executed | 1106 | 100 | 1.000000 | 2024-01-31 00:00:00 | 2024-03-07 00:00:00 | 0.001000 | 0.177727 | 0.099066 | 0.079458 | 3.950000 | 100.000000 |
| 2024-03-06 00:00:00 | executed | 1120 | 100 | 0.970000 | 2024-03-07 00:00:00 | 2024-04-08 00:00:00 | 0.000970 | 0.015995 | 0.017612 | -0.002376 | 3.590000 | 100.000000 |
| 2024-04-03 00:00:00 | executed | 1116 | 100 | 0.760000 | 2024-04-08 00:00:00 | 2024-05-09 00:00:00 | 0.000760 | 0.031890 | 0.018991 | 0.012893 | 4.100000 | 100.000000 |
| 2024-05-08 00:00:00 | executed | 1112 | 100 | 0.850000 | 2024-05-09 00:00:00 | 2024-06-06 00:00:00 | 0.000850 | -0.088982 | -0.080777 | -0.008975 | 3.940000 | 100.000000 |
| 2024-06-05 00:00:00 | executed | 1121 | 100 | 0.820000 | 2024-06-06 00:00:00 | 2024-07-05 00:00:00 | 0.000820 | 0.011811 | -0.038954 | 0.054200 | 3.590000 | 100.000000 |
| 2024-07-04 00:00:00 | executed | 1114 | 100 | 0.860000 | 2024-07-05 00:00:00 | 2024-08-02 00:00:00 | 0.000860 | 0.009945 | 0.011259 | -0.000338 | 4.050000 | 100.000000 |
| 2024-08-01 00:00:00 | executed | 1090 | 100 | 0.860000 | 2024-08-02 00:00:00 | 2024-08-30 00:00:00 | 0.000860 | -0.028218 | -0.030422 | 0.001645 | 4.250000 | 100.000000 |
| 2024-08-29 00:00:00 | executed | 1098 | 100 | 0.770000 | 2024-08-30 00:00:00 | 2024-10-08 00:00:00 | 0.000770 | 0.325451 | 0.329407 | -0.003137 | 4.170000 | 100.000000 |
| 2024-09-30 00:00:00 | executed | 759 | 100 | 0.890000 | 2024-10-08 00:00:00 | 2024-11-05 00:00:00 | 0.000890 | -0.017207 | 0.007250 | -0.029315 | 4.210000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 00:00:00 | 2024-01-30 00:00:00 | -0.003905 | 1.000000 | 0.001000 | -0.004905 | -0.010359 | 0.006454 | 0.005454 |
| 2024-02-02 00:00:00 | 2024-01-30 00:00:00 | -0.048342 | 0.000000 | 0.000000 | -0.048342 | -0.030013 | -0.018329 | -0.018329 |
| 2024-02-05 00:00:00 | 2024-01-30 00:00:00 | -0.089367 | 0.000000 | 0.000000 | -0.089367 | -0.055785 | -0.033583 | -0.033583 |
| 2024-02-06 00:00:00 | 2024-01-30 00:00:00 | 0.051578 | 0.000000 | 0.000000 | 0.051578 | 0.044952 | 0.006626 | 0.006626 |
| 2024-02-07 00:00:00 | 2024-01-30 00:00:00 | 0.018870 | 0.000000 | 0.000000 | 0.018870 | 0.017902 | 0.000967 | 0.000967 |
| 2024-02-08 00:00:00 | 2024-01-30 00:00:00 | 0.069423 | 0.000000 | 0.000000 | 0.069423 | 0.039482 | 0.029941 | 0.029941 |
| 2024-02-19 00:00:00 | 2024-01-30 00:00:00 | 0.032205 | 0.000000 | 0.000000 | 0.032205 | 0.021911 | 0.010294 | 0.010294 |
| 2024-02-20 00:00:00 | 2024-01-30 00:00:00 | 0.020463 | 0.000000 | 0.000000 | 0.020463 | 0.008361 | 0.012102 | 0.012102 |
| 2024-02-21 00:00:00 | 2024-01-30 00:00:00 | 0.012731 | 0.000000 | 0.000000 | 0.012731 | 0.009584 | 0.003147 | 0.003147 |
| 2024-02-22 00:00:00 | 2024-01-30 00:00:00 | 0.032913 | 0.000000 | 0.000000 | 0.032913 | 0.017981 | 0.014932 | 0.014932 |

## Output Files

- `summary.csv`
- `daily_returns.csv`
- `rebalance_summary.csv`
- `positions.csv`
- `candidate_weight_table.csv`
- `score_component_summary.csv`
- `alpha158_candidate_portfolio_smoke_report.md`

## Notes

- This is an interface smoke test, not a production strategy.
- The input is restricted to `role == alpha_candidate` from the frozen candidate pool.
- Tradability labels are applied before holdings are selected.
