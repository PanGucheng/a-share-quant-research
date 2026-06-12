# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `300`
- Cost: `5.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1`

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
| gross_annualized_return | `0.042556` |
| net_annualized_return | `0.039411` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.027538` |
| net_annualized_excess | `0.024440` |
| gross_excess_ir | `0.372462` |
| net_excess_ir | `0.335758` |
| net_max_drawdown | `-0.247445` |
| average_turnover | `0.479905` |
| max_turnover | `1.000000` |
| average_eligible_count | `1123.057143` |
| average_selected_count | `300.000000` |
| label | `label_20d_t1` |
| topk | `300` |
| rebalance_every | `20` |
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
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 300 | 1.000000 | 0.000500 | 0.047874 | -0.002832 | 0.049466 | 3.746667 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 300 | 0.480000 | 0.000240 | 0.027371 | 0.044414 | -0.016877 | 3.650000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 300 | 0.463333 | 0.000232 | -0.020526 | -0.002538 | -0.018305 | 3.716667 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 300 | 0.466667 | 0.000233 | 0.042515 | 0.061029 | -0.017712 | 3.716667 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 300 | 0.466667 | 0.000233 | -0.005033 | 0.005843 | -0.011492 | 3.633333 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 300 | 0.483333 | 0.000242 | 0.002456 | 0.029714 | -0.027833 | 3.656667 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 300 | 0.436667 | 0.000218 | 0.055828 | 0.064252 | -0.008848 | 3.620000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 300 | 0.486667 | 0.000243 | 0.019155 | -0.025757 | 0.044821 | 3.596667 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 300 | 0.533333 | 0.000267 | 0.014228 | -0.007317 | 0.020739 | 3.683333 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 300 | 0.486667 | 0.000243 | 0.047739 | 0.055793 | -0.008121 | 3.700000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.010607 | 1.000000 | 0.000500 | -0.011107 | -0.013386 | 0.002779 | 0.002279 |
| 2021-02-04 | 2021-02-01 | -0.016686 | 0.000000 | 0.000000 | -0.016686 | -0.018752 | 0.002066 | 0.002066 |
| 2021-02-05 | 2021-02-01 | -0.004352 | 0.000000 | 0.000000 | -0.004352 | -0.016112 | 0.011759 | 0.011759 |
| 2021-02-08 | 2021-02-01 | 0.007206 | 0.000000 | 0.000000 | 0.007206 | 0.007470 | -0.000264 | -0.000264 |
| 2021-02-09 | 2021-02-01 | 0.014285 | 0.000000 | 0.000000 | 0.014285 | 0.021414 | -0.007129 | -0.007129 |
| 2021-02-10 | 2021-02-01 | 0.008461 | 0.000000 | 0.000000 | 0.008461 | 0.008609 | -0.000148 | -0.000148 |
| 2021-02-18 | 2021-02-01 | 0.024213 | 0.000000 | 0.000000 | 0.024213 | 0.026714 | -0.002501 | -0.002501 |
| 2021-02-19 | 2021-02-01 | 0.027501 | 0.000000 | 0.000000 | 0.027501 | 0.025629 | 0.001872 | 0.001872 |
| 2021-02-22 | 2021-02-01 | 0.010348 | 0.000000 | 0.000000 | 0.010348 | 0.005639 | 0.004708 | 0.004708 |
| 2021-02-23 | 2021-02-01 | -0.002057 | 0.000000 | 0.000000 | -0.002057 | -0.006207 | 0.004150 | 0.004150 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
