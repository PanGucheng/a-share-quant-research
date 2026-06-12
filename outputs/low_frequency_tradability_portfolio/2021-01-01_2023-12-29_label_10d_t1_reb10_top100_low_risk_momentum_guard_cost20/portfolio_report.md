# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `100`
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
| gross_annualized_return | `0.043213` |
| net_annualized_return | `0.021565` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.024137` |
| net_annualized_excess | `0.002899` |
| gross_excess_ir | `0.262242` |
| net_excess_ir | `0.083015` |
| net_max_drawdown | `-0.206008` |
| average_turnover | `0.416000` |
| max_turnover | `1.000000` |
| average_eligible_count | `1124.685714` |
| average_selected_count | `100.000000` |
| label | `label_10d_t1` |
| topk | `100` |
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
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 100 | 1.000000 | 0.002000 | 0.060205 | 0.040415 | 0.017943 | 3.820000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 100 | 0.410000 | 0.000820 | 0.004735 | -0.042360 | 0.047654 | 3.830000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 100 | 0.330000 | 0.000660 | 0.021115 | 0.023996 | -0.003273 | 3.690000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 100 | 0.390000 | 0.000780 | 0.002850 | 0.019674 | -0.016881 | 3.730000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 100 | 0.400000 | 0.000800 | -0.007599 | 0.004745 | -0.012661 | 3.740000 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 100 | 0.330000 | 0.000660 | -0.023008 | -0.004462 | -0.018780 | 3.760000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 100 | 0.420000 | 0.000840 | 0.015996 | 0.021835 | -0.005819 | 3.750000 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 100 | 0.420000 | 0.000840 | 0.006436 | 0.037367 | -0.030193 | 3.540000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 100 | 0.430000 | 0.000860 | -0.013864 | 0.005246 | -0.019508 | 3.560000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 100 | 0.450000 | 0.000900 | 0.000435 | 0.002039 | -0.002325 | 3.570000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.005007 | 1.000000 | 0.002000 | -0.007007 | -0.013386 | 0.008379 | 0.006379 |
| 2021-02-04 | 2021-02-01 | -0.013318 | 0.000000 | 0.000000 | -0.013318 | -0.018752 | 0.005434 | 0.005434 |
| 2021-02-05 | 2021-02-01 | 0.004858 | 0.000000 | 0.000000 | 0.004858 | -0.016112 | 0.020970 | 0.020970 |
| 2021-02-08 | 2021-02-01 | 0.005751 | 0.000000 | 0.000000 | 0.005751 | 0.007470 | -0.001720 | -0.001720 |
| 2021-02-09 | 2021-02-01 | 0.008380 | 0.000000 | 0.000000 | 0.008380 | 0.021414 | -0.013034 | -0.013034 |
| 2021-02-10 | 2021-02-01 | 0.006351 | 0.000000 | 0.000000 | 0.006351 | 0.008609 | -0.002258 | -0.002258 |
| 2021-02-18 | 2021-02-01 | 0.020264 | 0.000000 | 0.000000 | 0.020264 | 0.026714 | -0.006449 | -0.006449 |
| 2021-02-19 | 2021-02-01 | 0.022971 | 0.000000 | 0.000000 | 0.022971 | 0.025629 | -0.002658 | -0.002658 |
| 2021-02-22 | 2021-02-01 | 0.012654 | 0.000000 | 0.000000 | 0.012654 | 0.005639 | 0.007014 | 0.007014 |
| 2021-02-23 | 2021-02-01 | -0.001700 | 0.000000 | 0.000000 | -0.001700 | -0.006207 | 0.004507 | 0.004507 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
