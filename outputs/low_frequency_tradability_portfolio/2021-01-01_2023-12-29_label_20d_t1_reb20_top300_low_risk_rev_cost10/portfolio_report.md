# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `300`
- Cost: `10.0` bps per one-way turnover
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
| gross_annualized_return | `0.042152` |
| net_annualized_return | `0.035921` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.027317` |
| net_annualized_excess | `0.021178` |
| gross_excess_ir | `0.370155` |
| net_excess_ir | `0.297116` |
| net_max_drawdown | `-0.256851` |
| average_turnover | `0.476190` |
| max_turnover | `1.000000` |
| average_eligible_count | `1123.057143` |
| average_selected_count | `300.000000` |
| label | `label_20d_t1` |
| topk | `300` |
| rebalance_every | `20` |
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
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 300 | 1.000000 | 0.001000 | 0.045813 | -0.002832 | 0.047443 | 3.750000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 300 | 0.466667 | 0.000467 | 0.024275 | 0.044414 | -0.019837 | 3.680000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 300 | 0.466667 | 0.000467 | -0.021977 | -0.002538 | -0.019783 | 3.713333 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 300 | 0.456667 | 0.000457 | 0.045492 | 0.061029 | -0.014922 | 3.713333 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 300 | 0.450000 | 0.000450 | -0.009364 | 0.005843 | -0.015823 | 3.673333 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 300 | 0.473333 | 0.000473 | 0.002883 | 0.029714 | -0.027405 | 3.680000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 300 | 0.463333 | 0.000463 | 0.060416 | 0.064252 | -0.004550 | 3.610000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 300 | 0.493333 | 0.000493 | 0.021058 | -0.025757 | 0.046598 | 3.590000 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 300 | 0.513333 | 0.000513 | 0.011619 | -0.007317 | 0.018201 | 3.630000 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 300 | 0.520000 | 0.000520 | 0.052009 | 0.055793 | -0.004024 | 3.696667 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.011440 | 1.000000 | 0.001000 | -0.012440 | -0.013386 | 0.001947 | 0.000947 |
| 2021-02-04 | 2021-02-01 | -0.016694 | 0.000000 | 0.000000 | -0.016694 | -0.018752 | 0.002058 | 0.002058 |
| 2021-02-05 | 2021-02-01 | -0.004570 | 0.000000 | 0.000000 | -0.004570 | -0.016112 | 0.011542 | 0.011542 |
| 2021-02-08 | 2021-02-01 | 0.007577 | 0.000000 | 0.000000 | 0.007577 | 0.007470 | 0.000107 | 0.000107 |
| 2021-02-09 | 2021-02-01 | 0.014754 | 0.000000 | 0.000000 | 0.014754 | 0.021414 | -0.006660 | -0.006660 |
| 2021-02-10 | 2021-02-01 | 0.008410 | 0.000000 | 0.000000 | 0.008410 | 0.008609 | -0.000199 | -0.000199 |
| 2021-02-18 | 2021-02-01 | 0.024289 | 0.000000 | 0.000000 | 0.024289 | 0.026714 | -0.002425 | -0.002425 |
| 2021-02-19 | 2021-02-01 | 0.027177 | 0.000000 | 0.000000 | 0.027177 | 0.025629 | 0.001548 | 0.001548 |
| 2021-02-22 | 2021-02-01 | 0.010113 | 0.000000 | 0.000000 | 0.010113 | 0.005639 | 0.004474 | 0.004474 |
| 2021-02-23 | 2021-02-01 | -0.002396 | 0.000000 | 0.000000 | -0.002396 | -0.006207 | 0.003811 | 0.003811 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
