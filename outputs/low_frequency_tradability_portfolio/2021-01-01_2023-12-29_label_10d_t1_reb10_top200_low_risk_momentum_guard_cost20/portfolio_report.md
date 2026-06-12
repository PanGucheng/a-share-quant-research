# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `200`
- Cost: `20.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,ret_20:-0.25`

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
| gross_annualized_return | `0.035344` |
| net_annualized_return | `0.014616` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.020193` |
| net_annualized_excess | `-0.000216` |
| gross_excess_ir | `0.253680` |
| net_excess_ir | `0.046365` |
| net_max_drawdown | `-0.242547` |
| average_turnover | `0.401071` |
| max_turnover | `1.000000` |
| average_eligible_count | `1124.685714` |
| average_selected_count | `200.000000` |
| label | `label_10d_t1` |
| topk | `200` |
| rebalance_every | `10` |
| cost_bps | `20.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| window_start | `2021-01-01` |
| window_end | `2023-12-29` |
| weight_preset | `low_risk_momentum_guard` |
| score_weights | `std_20:-1,amplitude_20:-1,ret_20:-0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 200 | 1.000000 | 0.002000 | 0.061096 | 0.040415 | 0.019296 | 3.735000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 200 | 0.385000 | 0.000770 | -0.000132 | -0.042360 | 0.042910 | 3.740000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 200 | 0.340000 | 0.000680 | 0.018323 | 0.023996 | -0.005940 | 3.680000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 200 | 0.405000 | 0.000810 | 0.005703 | 0.019674 | -0.014030 | 3.610000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 200 | 0.380000 | 0.000760 | -0.003900 | 0.004745 | -0.008889 | 3.705000 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 200 | 0.350000 | 0.000700 | -0.026852 | -0.004462 | -0.022615 | 3.675000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 200 | 0.415000 | 0.000830 | 0.018025 | 0.021835 | -0.003829 | 3.700000 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 200 | 0.360000 | 0.000720 | 0.009806 | 0.037367 | -0.026863 | 3.630000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 200 | 0.400000 | 0.000800 | -0.007311 | 0.005246 | -0.012890 | 3.565000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 200 | 0.435000 | 0.000870 | -0.005113 | 0.002039 | -0.007763 | 3.630000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.009590 | 1.000000 | 0.002000 | -0.011590 | -0.013386 | 0.003797 | 0.001797 |
| 2021-02-04 | 2021-02-01 | -0.015582 | 0.000000 | 0.000000 | -0.015582 | -0.018752 | 0.003170 | 0.003170 |
| 2021-02-05 | 2021-02-01 | -0.000375 | 0.000000 | 0.000000 | -0.000375 | -0.016112 | 0.015737 | 0.015737 |
| 2021-02-08 | 2021-02-01 | 0.007454 | 0.000000 | 0.000000 | 0.007454 | 0.007470 | -0.000017 | -0.000017 |
| 2021-02-09 | 2021-02-01 | 0.012294 | 0.000000 | 0.000000 | 0.012294 | 0.021414 | -0.009120 | -0.009120 |
| 2021-02-10 | 2021-02-01 | 0.006081 | 0.000000 | 0.000000 | 0.006081 | 0.008609 | -0.002528 | -0.002528 |
| 2021-02-18 | 2021-02-01 | 0.024489 | 0.000000 | 0.000000 | 0.024489 | 0.026714 | -0.002225 | -0.002225 |
| 2021-02-19 | 2021-02-01 | 0.026891 | 0.000000 | 0.000000 | 0.026891 | 0.025629 | 0.001262 | 0.001262 |
| 2021-02-22 | 2021-02-01 | 0.012381 | 0.000000 | 0.000000 | 0.012381 | 0.005639 | 0.006742 | 0.006742 |
| 2021-02-23 | 2021-02-01 | -0.001703 | 0.000000 | 0.000000 | -0.001703 | -0.006207 | 0.004504 | 0.004504 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
