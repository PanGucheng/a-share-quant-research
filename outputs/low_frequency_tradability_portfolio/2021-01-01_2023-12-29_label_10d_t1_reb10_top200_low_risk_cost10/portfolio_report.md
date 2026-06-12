# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `200`
- Cost: `10.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1`

## Summary

| metric | value |
| --- | ---: |
| start_date | `2021-02-03` |
| end_date | `2023-12-22` |
| trading_days | `700` |
| rebalance_count | `71` |
| executed_rebalances | `70` |
| skipped_rebalances | `1` |
| skipped_rebalance_rate | `0.014085` |
| gross_annualized_return | `0.040849` |
| net_annualized_return | `0.030520` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.025466` |
| net_annualized_excess | `0.015296` |
| gross_excess_ir | `0.307561` |
| net_excess_ir | `0.204879` |
| net_max_drawdown | `-0.233017` |
| average_turnover | `0.395714` |
| max_turnover | `1.000000` |
| average_eligible_count | `1124.685714` |
| average_selected_count | `200.000000` |
| label | `label_10d_t1` |
| topk | `200` |
| rebalance_every | `10` |
| cost_bps | `10.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| window_start | `2021-01-01` |
| window_end | `2023-12-29` |
| weight_preset | `low_risk` |
| score_weights | `std_20:-1,amplitude_20:-1` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 200 | 1.000000 | 0.001000 | 0.062017 | 0.040415 | 0.020131 | 3.755000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 200 | 0.390000 | 0.000390 | 0.000393 | -0.042360 | 0.043443 | 3.740000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 200 | 0.345000 | 0.000345 | 0.020938 | 0.023996 | -0.003362 | 3.655000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 200 | 0.400000 | 0.000400 | 0.005796 | 0.019674 | -0.013938 | 3.585000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 200 | 0.400000 | 0.000400 | -0.003018 | 0.004745 | -0.008006 | 3.715000 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 200 | 0.360000 | 0.000360 | -0.024989 | -0.004462 | -0.020749 | 3.660000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 200 | 0.425000 | 0.000425 | 0.016958 | 0.021835 | -0.004871 | 3.680000 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 200 | 0.375000 | 0.000375 | 0.009396 | 0.037367 | -0.027270 | 3.630000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 200 | 0.400000 | 0.000400 | -0.004910 | 0.005246 | -0.010515 | 3.585000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 200 | 0.440000 | 0.000440 | -0.004925 | 0.002039 | -0.007509 | 3.595000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.008836 | 1.000000 | 0.001000 | -0.009836 | -0.013386 | 0.004551 | 0.003551 |
| 2021-02-04 | 2021-02-01 | -0.015175 | 0.000000 | 0.000000 | -0.015175 | -0.018752 | 0.003577 | 0.003577 |
| 2021-02-05 | 2021-02-01 | -0.001496 | 0.000000 | 0.000000 | -0.001496 | -0.016112 | 0.014615 | 0.014615 |
| 2021-02-08 | 2021-02-01 | 0.008425 | 0.000000 | 0.000000 | 0.008425 | 0.007470 | 0.000955 | 0.000955 |
| 2021-02-09 | 2021-02-01 | 0.011998 | 0.000000 | 0.000000 | 0.011998 | 0.021414 | -0.009415 | -0.009415 |
| 2021-02-10 | 2021-02-01 | 0.006511 | 0.000000 | 0.000000 | 0.006511 | 0.008609 | -0.002098 | -0.002098 |
| 2021-02-18 | 2021-02-01 | 0.023771 | 0.000000 | 0.000000 | 0.023771 | 0.026714 | -0.002942 | -0.002942 |
| 2021-02-19 | 2021-02-01 | 0.026186 | 0.000000 | 0.000000 | 0.026186 | 0.025629 | 0.000557 | 0.000557 |
| 2021-02-22 | 2021-02-01 | 0.012149 | 0.000000 | 0.000000 | 0.012149 | 0.005639 | 0.006510 | 0.006510 |
| 2021-02-23 | 2021-02-01 | -0.001381 | 0.000000 | 0.000000 | -0.001381 | -0.006207 | 0.004826 | 0.004826 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
