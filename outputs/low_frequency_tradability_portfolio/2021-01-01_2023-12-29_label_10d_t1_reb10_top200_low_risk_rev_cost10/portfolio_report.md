# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `200`
- Cost: `10.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,rev_5:0.25`

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
| gross_annualized_return | `0.031649` |
| net_annualized_return | `0.021440` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.016289` |
| net_annualized_excess | `0.006238` |
| gross_excess_ir | `0.214204` |
| net_excess_ir | `0.112384` |
| net_max_drawdown | `-0.235013` |
| average_turnover | `0.394500` |
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
| weight_preset | `low_risk_rev` |
| score_weights | `std_20:-1,amplitude_20:-1,rev_5:0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 200 | 1.000000 | 0.001000 | 0.059051 | 0.040415 | 0.017323 | 3.745000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 200 | 0.385000 | 0.000385 | -0.001719 | -0.042360 | 0.041240 | 3.740000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 200 | 0.355000 | 0.000355 | 0.019342 | 0.023996 | -0.004947 | 3.660000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 200 | 0.400000 | 0.000400 | 0.006098 | 0.019674 | -0.013660 | 3.595000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 200 | 0.380000 | 0.000380 | -0.004453 | 0.004745 | -0.009457 | 3.685000 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 200 | 0.335000 | 0.000335 | -0.025799 | -0.004462 | -0.021558 | 3.675000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 200 | 0.405000 | 0.000405 | 0.018023 | 0.021835 | -0.003841 | 3.685000 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 200 | 0.375000 | 0.000375 | 0.012029 | 0.037367 | -0.024712 | 3.630000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 200 | 0.400000 | 0.000400 | -0.006763 | 0.005246 | -0.012350 | 3.600000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 200 | 0.415000 | 0.000415 | -0.003934 | 0.002039 | -0.006556 | 3.620000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.009994 | 1.000000 | 0.001000 | -0.010994 | -0.013386 | 0.003393 | 0.002393 |
| 2021-02-04 | 2021-02-01 | -0.016038 | 0.000000 | 0.000000 | -0.016038 | -0.018752 | 0.002714 | 0.002714 |
| 2021-02-05 | 2021-02-01 | -0.000796 | 0.000000 | 0.000000 | -0.000796 | -0.016112 | 0.015315 | 0.015315 |
| 2021-02-08 | 2021-02-01 | 0.006997 | 0.000000 | 0.000000 | 0.006997 | 0.007470 | -0.000474 | -0.000474 |
| 2021-02-09 | 2021-02-01 | 0.011966 | 0.000000 | 0.000000 | 0.011966 | 0.021414 | -0.009448 | -0.009448 |
| 2021-02-10 | 2021-02-01 | 0.005944 | 0.000000 | 0.000000 | 0.005944 | 0.008609 | -0.002664 | -0.002664 |
| 2021-02-18 | 2021-02-01 | 0.024296 | 0.000000 | 0.000000 | 0.024296 | 0.026714 | -0.002418 | -0.002418 |
| 2021-02-19 | 2021-02-01 | 0.026774 | 0.000000 | 0.000000 | 0.026774 | 0.025629 | 0.001145 | 0.001145 |
| 2021-02-22 | 2021-02-01 | 0.012388 | 0.000000 | 0.000000 | 0.012388 | 0.005639 | 0.006749 | 0.006749 |
| 2021-02-23 | 2021-02-01 | -0.002138 | 0.000000 | 0.000000 | -0.002138 | -0.006207 | 0.004068 | 0.004068 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
