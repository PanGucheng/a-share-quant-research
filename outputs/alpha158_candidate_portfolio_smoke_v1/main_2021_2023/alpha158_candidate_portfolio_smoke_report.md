# Alpha158 Candidate Portfolio Smoke V1

- Candidate pool: `outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv`
- Expression frame: `outputs\alpha158_expression_frame_v1\full158_main_research`
- Tradability dir: `outputs\tradability\all_stock_shsz_liquid2000_2021-01-01_2023-12-29`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Score policy: `equal_directional_zscore`
- Rebalance every: `20` trading days
- TopK: `100`
- Cost: `10.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2021-02-03` |
| end_date | `2023-12-22` |
| trading_days | `700` |
| rebalance_count | `37` |
| executed_rebalances | `35` |
| skipped_rebalances | `2` |
| skipped_rebalance_rate | `0.054054` |
| gross_annualized_return | `0.076916` |
| net_annualized_return | `0.065788` |
| universe_annualized_return | `0.003545` |
| gross_annualized_excess | `0.071703` |
| net_annualized_excess | `0.060632` |
| gross_excess_ir | `0.639603` |
| net_excess_ir | `0.552843` |
| net_max_drawdown | `-0.321708` |
| average_turnover | `0.824857` |
| max_turnover | `1.000000` |
| average_eligible_count | `1131.942857` |
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
| alpha158_MIN60 | 1.000000 | 1409879 | 0.996499 |
| alpha158_QTLD60 | 1.000000 | 1409879 | 0.996499 |
| alpha158_ROC60 | 1.000000 | 1406924 | 0.994411 |
| alpha158_MIN30 | 1.000000 | 1409879 | 0.996499 |
| alpha158_ROC30 | 1.000000 | 1406754 | 0.994290 |
| alpha158_QTLD30 | 1.000000 | 1409879 | 0.996499 |
| alpha158_IMIN60 | 1.000000 | 1413485 | 0.999048 |
| alpha158_MIN10 | 1.000000 | 1409879 | 0.996499 |
| alpha158_IMIN30 | 1.000000 | 1413286 | 0.998907 |
| alpha158_MIN5 | 1.000000 | 1409879 | 0.996499 |
| alpha158_IMIN20 | 1.000000 | 1412965 | 0.998680 |
| alpha158_QTLD10 | 1.000000 | 1409879 | 0.996499 |
| alpha158_VSUMN60 | 1.000000 | 1413475 | 0.999041 |
| alpha158_ROC10 | 1.000000 | 1407171 | 0.994585 |

## First Rebalances

| signal_date | status | eligible_count | selected_count | turnover | execution_date | period_end_date | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-01-04 00:00:00 | skipped_insufficient_eligible_count | 0 | 0 |  | NaT | NaT |  |  |  |  |  |  |
| 2021-02-01 00:00:00 | executed | 1123 | 100 | 1.000000 | 2021-02-02 00:00:00 | 2021-03-09 00:00:00 | 0.001000 | 0.057432 | -0.002609 | 0.061557 | 3.630000 | 100.000000 |
| 2021-03-08 00:00:00 | executed | 1134 | 100 | 0.970000 | 2021-03-09 00:00:00 | 2021-04-07 00:00:00 | 0.000970 | 0.072529 | 0.044430 | 0.026698 | 4.580000 | 100.000000 |
| 2021-04-06 00:00:00 | executed | 1136 | 100 | 0.840000 | 2021-04-07 00:00:00 | 2021-05-10 00:00:00 | 0.000840 | -0.018094 | -0.002559 | -0.015596 | 3.950000 | 100.000000 |
| 2021-05-07 00:00:00 | executed | 1143 | 100 | 0.780000 | 2021-05-10 00:00:00 | 2021-06-07 00:00:00 | 0.000780 | 0.098549 | 0.060644 | 0.035979 | 3.900000 | 100.000000 |
| 2021-06-04 00:00:00 | executed | 1148 | 100 | 0.910000 | 2021-06-07 00:00:00 | 2021-07-06 00:00:00 | 0.000910 | -0.014622 | 0.006717 | -0.021969 | 3.690000 | 100.000000 |
| 2021-07-05 00:00:00 | executed | 1137 | 100 | 0.800000 | 2021-07-06 00:00:00 | 2021-08-03 00:00:00 | 0.000800 | -0.042054 | 0.028371 | -0.069516 | 3.940000 | 100.000000 |
| 2021-08-02 00:00:00 | executed | 1122 | 100 | 0.690000 | 2021-08-03 00:00:00 | 2021-08-31 00:00:00 | 0.000690 | 0.033291 | 0.063781 | -0.029450 | 3.920000 | 100.000000 |
| 2021-08-30 00:00:00 | executed | 1128 | 100 | 0.840000 | 2021-08-31 00:00:00 | 2021-09-30 00:00:00 | 0.000840 | 0.057429 | -0.025838 | 0.081354 | 3.830000 | 100.000000 |
| 2021-09-29 00:00:00 | executed | 1124 | 100 | 0.940000 | 2021-09-30 00:00:00 | 2021-11-04 00:00:00 | 0.000940 | 0.009295 | -0.007264 | 0.016976 | 3.730000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 00:00:00 | 2021-02-01 00:00:00 | -0.023781 | 1.000000 | 0.001000 | -0.024781 | -0.013378 | -0.010403 | -0.011403 |
| 2021-02-04 00:00:00 | 2021-02-01 00:00:00 | -0.024764 | 0.000000 | 0.000000 | -0.024764 | -0.018734 | -0.006030 | -0.006030 |
| 2021-02-05 00:00:00 | 2021-02-01 00:00:00 | -0.014607 | 0.000000 | 0.000000 | -0.014607 | -0.016022 | 0.001415 | 0.001415 |
| 2021-02-08 00:00:00 | 2021-02-01 00:00:00 | -0.003915 | 0.000000 | 0.000000 | -0.003915 | 0.007444 | -0.011359 | -0.011359 |
| 2021-02-09 00:00:00 | 2021-02-01 00:00:00 | 0.019733 | 0.000000 | 0.000000 | 0.019733 | 0.021374 | -0.001640 | -0.001640 |
| 2021-02-10 00:00:00 | 2021-02-01 00:00:00 | 0.007764 | 0.000000 | 0.000000 | 0.007764 | 0.008562 | -0.000798 | -0.000798 |
| 2021-02-18 00:00:00 | 2021-02-01 00:00:00 | 0.045841 | 0.000000 | 0.000000 | 0.045841 | 0.026767 | 0.019074 | 0.019074 |
| 2021-02-19 00:00:00 | 2021-02-01 00:00:00 | 0.047437 | 0.000000 | 0.000000 | 0.047437 | 0.025714 | 0.021724 | 0.021724 |
| 2021-02-22 00:00:00 | 2021-02-01 00:00:00 | 0.021838 | 0.000000 | 0.000000 | 0.021838 | 0.005539 | 0.016299 | 0.016299 |
| 2021-02-23 00:00:00 | 2021-02-01 00:00:00 | -0.013594 | 0.000000 | 0.000000 | -0.013594 | -0.006133 | -0.007461 | -0.007461 |

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
