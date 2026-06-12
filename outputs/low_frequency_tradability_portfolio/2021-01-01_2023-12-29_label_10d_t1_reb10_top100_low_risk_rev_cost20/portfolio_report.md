# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `100`
- Cost: `20.0` bps per one-way turnover
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
| gross_annualized_return | `0.046736` |
| net_annualized_return | `0.025384` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.027303` |
| net_annualized_excess | `0.006361` |
| gross_excess_ir | `0.288164` |
| net_excess_ir | `0.112517` |
| net_max_drawdown | `-0.213602` |
| average_turnover | `0.408857` |
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
| weight_preset | `low_risk_rev` |
| score_weights | `std_20:-1,amplitude_20:-1,rev_5:0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 100 | 1.000000 | 0.002000 | 0.057516 | 0.040415 | 0.015302 | 3.830000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 100 | 0.370000 | 0.000740 | 0.001143 | -0.042360 | 0.043983 | 3.830000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 100 | 0.330000 | 0.000660 | 0.020223 | 0.023996 | -0.004115 | 3.670000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 100 | 0.350000 | 0.000700 | 0.003610 | 0.019674 | -0.016122 | 3.760000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 100 | 0.410000 | 0.000820 | -0.008441 | 0.004745 | -0.013535 | 3.760000 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 100 | 0.330000 | 0.000660 | -0.022413 | -0.004462 | -0.018178 | 3.750000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 100 | 0.420000 | 0.000840 | 0.015798 | 0.021835 | -0.006024 | 3.750000 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 100 | 0.410000 | 0.000820 | 0.006041 | 0.037367 | -0.030601 | 3.570000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 100 | 0.430000 | 0.000860 | -0.012123 | 0.005246 | -0.017735 | 3.570000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 100 | 0.450000 | 0.000900 | 0.001035 | 0.002039 | -0.001694 | 3.590000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.005223 | 1.000000 | 0.002000 | -0.007223 | -0.013386 | 0.008163 | 0.006163 |
| 2021-02-04 | 2021-02-01 | -0.012857 | 0.000000 | 0.000000 | -0.012857 | -0.018752 | 0.005895 | 0.005895 |
| 2021-02-05 | 2021-02-01 | 0.006108 | 0.000000 | 0.000000 | 0.006108 | -0.016112 | 0.022219 | 0.022219 |
| 2021-02-08 | 2021-02-01 | 0.005200 | 0.000000 | 0.000000 | 0.005200 | 0.007470 | -0.002271 | -0.002271 |
| 2021-02-09 | 2021-02-01 | 0.007896 | 0.000000 | 0.000000 | 0.007896 | 0.021414 | -0.013518 | -0.013518 |
| 2021-02-10 | 2021-02-01 | 0.005520 | 0.000000 | 0.000000 | 0.005520 | 0.008609 | -0.003089 | -0.003089 |
| 2021-02-18 | 2021-02-01 | 0.020410 | 0.000000 | 0.000000 | 0.020410 | 0.026714 | -0.006304 | -0.006304 |
| 2021-02-19 | 2021-02-01 | 0.022622 | 0.000000 | 0.000000 | 0.022622 | 0.025629 | -0.003007 | -0.003007 |
| 2021-02-22 | 2021-02-01 | 0.011113 | 0.000000 | 0.000000 | 0.011113 | 0.005639 | 0.005474 | 0.005474 |
| 2021-02-23 | 2021-02-01 | -0.002156 | 0.000000 | 0.000000 | -0.002156 | -0.006207 | 0.004051 | 0.004051 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
