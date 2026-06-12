# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `200`
- Cost: `20.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,rev_5:0.25`

## Summary

| metric | value |
| --- | ---: |
| start_date | `2021-02-03` |
| end_date | `2023-12-22` |
| trading_days | `700` |
| rebalance_count | `36` |
| executed_rebalances | `35` |
| skipped_rebalances | `1` |
| skipped_rebalance_rate | `0.027778` |
| gross_annualized_return | `0.030087` |
| net_annualized_return | `0.017119` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.013100` |
| net_annualized_excess | `0.000354` |
| gross_excess_ir | `0.183754` |
| net_excess_ir | `0.051314` |
| net_max_drawdown | `-0.244380` |
| average_turnover | `0.503000` |
| max_turnover | `1.000000` |
| average_eligible_count | `1123.057143` |
| average_selected_count | `200.000000` |
| label | `label_20d_t1` |
| topk | `200` |
| rebalance_every | `20` |
| cost_bps | `20.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| window_start | `2021-01-01` |
| window_end | `2023-12-29` |
| weight_preset | `low_risk_rev` |
| score_weights | `std_20:-1,amplitude_20:-1,rev_5:0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 200 | 1.000000 | 0.002000 | 0.055219 | -0.002832 | 0.056468 | 3.745000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 200 | 0.485000 | 0.000970 | 0.025523 | 0.044414 | -0.018766 | 3.660000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 200 | 0.485000 | 0.000970 | -0.028827 | -0.002538 | -0.026739 | 3.685000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 200 | 0.445000 | 0.000890 | 0.032370 | 0.061029 | -0.027361 | 3.685000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 200 | 0.485000 | 0.000970 | -0.011804 | 0.005843 | -0.018324 | 3.605000 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 200 | 0.530000 | 0.001060 | -0.010533 | 0.029714 | -0.040636 | 3.645000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 200 | 0.470000 | 0.000940 | 0.060368 | 0.064252 | -0.004791 | 3.620000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 200 | 0.525000 | 0.001050 | 0.027279 | -0.025757 | 0.052916 | 3.575000 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 200 | 0.605000 | 0.001210 | 0.005461 | -0.007317 | 0.011922 | 3.540000 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 200 | 0.545000 | 0.001090 | 0.037014 | 0.055793 | -0.018335 | 3.650000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.009829 | 1.000000 | 0.002000 | -0.011829 | -0.013386 | 0.003557 | 0.001557 |
| 2021-02-04 | 2021-02-01 | -0.015937 | 0.000000 | 0.000000 | -0.015937 | -0.018752 | 0.002815 | 0.002815 |
| 2021-02-05 | 2021-02-01 | -0.000499 | 0.000000 | 0.000000 | -0.000499 | -0.016112 | 0.015612 | 0.015612 |
| 2021-02-08 | 2021-02-01 | 0.007033 | 0.000000 | 0.000000 | 0.007033 | 0.007470 | -0.000437 | -0.000437 |
| 2021-02-09 | 2021-02-01 | 0.011827 | 0.000000 | 0.000000 | 0.011827 | 0.021414 | -0.009587 | -0.009587 |
| 2021-02-10 | 2021-02-01 | 0.005880 | 0.000000 | 0.000000 | 0.005880 | 0.008609 | -0.002729 | -0.002729 |
| 2021-02-18 | 2021-02-01 | 0.024242 | 0.000000 | 0.000000 | 0.024242 | 0.026714 | -0.002472 | -0.002472 |
| 2021-02-19 | 2021-02-01 | 0.027180 | 0.000000 | 0.000000 | 0.027180 | 0.025629 | 0.001551 | 0.001551 |
| 2021-02-22 | 2021-02-01 | 0.012322 | 0.000000 | 0.000000 | 0.012322 | 0.005639 | 0.006683 | 0.006683 |
| 2021-02-23 | 2021-02-01 | -0.002124 | 0.000000 | 0.000000 | -0.002124 | -0.006207 | 0.004083 | 0.004083 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
