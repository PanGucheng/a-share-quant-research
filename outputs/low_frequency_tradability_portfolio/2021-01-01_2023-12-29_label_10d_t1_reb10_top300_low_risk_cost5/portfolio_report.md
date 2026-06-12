# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `300`
- Cost: `5.0` bps per one-way turnover
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
| gross_annualized_return | `0.041022` |
| net_annualized_return | `0.036099` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.028030` |
| net_annualized_excess | `0.023172` |
| gross_excess_ir | `0.373965` |
| net_excess_ir | `0.317060` |
| net_max_drawdown | `-0.250581` |
| average_turnover | `0.376143` |
| max_turnover | `1.000000` |
| average_eligible_count | `1124.685714` |
| average_selected_count | `300.000000` |
| label | `label_10d_t1` |
| topk | `300` |
| rebalance_every | `10` |
| cost_bps | `5.000000` |
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
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 300 | 1.000000 | 0.000500 | 0.057870 | 0.040415 | 0.016341 | 3.746667 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 300 | 0.373333 | 0.000187 | -0.003968 | -0.042360 | 0.039051 | 3.726667 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 300 | 0.353333 | 0.000177 | 0.020637 | 0.023996 | -0.003604 | 3.650000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 300 | 0.370000 | 0.000185 | 0.009444 | 0.019674 | -0.010338 | 3.573333 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 300 | 0.370000 | 0.000185 | 0.002435 | 0.004745 | -0.002516 | 3.716667 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 300 | 0.380000 | 0.000190 | -0.028036 | -0.004462 | -0.023793 | 3.656667 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 300 | 0.373333 | 0.000187 | 0.020742 | 0.021835 | -0.001157 | 3.716667 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 300 | 0.363333 | 0.000182 | 0.020755 | 0.037367 | -0.016236 | 3.686667 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 300 | 0.383333 | 0.000192 | 0.000051 | 0.005246 | -0.005515 | 3.633333 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 300 | 0.383333 | 0.000192 | -0.005091 | 0.002039 | -0.007566 | 3.666667 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.010716 | 1.000000 | 0.000500 | -0.011216 | -0.013386 | 0.002670 | 0.002170 |
| 2021-02-04 | 2021-02-01 | -0.016753 | 0.000000 | 0.000000 | -0.016753 | -0.018752 | 0.001999 | 0.001999 |
| 2021-02-05 | 2021-02-01 | -0.004550 | 0.000000 | 0.000000 | -0.004550 | -0.016112 | 0.011561 | 0.011561 |
| 2021-02-08 | 2021-02-01 | 0.007181 | 0.000000 | 0.000000 | 0.007181 | 0.007470 | -0.000289 | -0.000289 |
| 2021-02-09 | 2021-02-01 | 0.014377 | 0.000000 | 0.000000 | 0.014377 | 0.021414 | -0.007037 | -0.007037 |
| 2021-02-10 | 2021-02-01 | 0.008504 | 0.000000 | 0.000000 | 0.008504 | 0.008609 | -0.000105 | -0.000105 |
| 2021-02-18 | 2021-02-01 | 0.024249 | 0.000000 | 0.000000 | 0.024249 | 0.026714 | -0.002465 | -0.002465 |
| 2021-02-19 | 2021-02-01 | 0.027231 | 0.000000 | 0.000000 | 0.027231 | 0.025629 | 0.001602 | 0.001602 |
| 2021-02-22 | 2021-02-01 | 0.010392 | 0.000000 | 0.000000 | 0.010392 | 0.005639 | 0.004752 | 0.004752 |
| 2021-02-23 | 2021-02-01 | -0.002067 | 0.000000 | 0.000000 | -0.002067 | -0.006207 | 0.004140 | 0.004140 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
