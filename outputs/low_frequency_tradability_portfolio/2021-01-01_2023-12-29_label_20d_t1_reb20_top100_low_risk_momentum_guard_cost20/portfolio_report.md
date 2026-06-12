# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `100`
- Cost: `20.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,ret_20:-0.25`

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
| gross_annualized_return | `0.045345` |
| net_annualized_return | `0.031084` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.024033` |
| net_annualized_excess | `0.010073` |
| gross_excess_ir | `0.261091` |
| net_excess_ir | `0.143981` |
| net_max_drawdown | `-0.199316` |
| average_turnover | `0.545714` |
| max_turnover | `1.000000` |
| average_eligible_count | `1123.057143` |
| average_selected_count | `100.000000` |
| label | `label_20d_t1` |
| topk | `100` |
| rebalance_every | `20` |
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
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 100 | 1.000000 | 0.002000 | 0.067418 | -0.002832 | 0.067844 | 3.820000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 100 | 0.530000 | 0.001060 | 0.024679 | 0.044414 | -0.019707 | 3.690000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 100 | 0.540000 | 0.001080 | -0.026417 | -0.002538 | -0.024419 | 3.740000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 100 | 0.490000 | 0.000980 | 0.024888 | 0.061029 | -0.034503 | 3.750000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 100 | 0.520000 | 0.001040 | -0.012507 | 0.005843 | -0.019273 | 3.570000 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 100 | 0.530000 | 0.001060 | -0.016890 | 0.029714 | -0.047228 | 3.640000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 100 | 0.460000 | 0.000920 | 0.048998 | 0.064252 | -0.015718 | 3.690000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 100 | 0.510000 | 0.001020 | 0.023038 | -0.025757 | 0.048427 | 3.570000 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 100 | 0.630000 | 0.001260 | 0.005012 | -0.007317 | 0.011217 | 3.510000 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 100 | 0.600000 | 0.001200 | 0.028685 | 0.055793 | -0.026333 | 3.590000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.004974 | 1.000000 | 0.002000 | -0.006974 | -0.013386 | 0.008413 | 0.006413 |
| 2021-02-04 | 2021-02-01 | -0.013049 | 0.000000 | 0.000000 | -0.013049 | -0.018752 | 0.005703 | 0.005703 |
| 2021-02-05 | 2021-02-01 | 0.004951 | 0.000000 | 0.000000 | 0.004951 | -0.016112 | 0.021062 | 0.021062 |
| 2021-02-08 | 2021-02-01 | 0.005676 | 0.000000 | 0.000000 | 0.005676 | 0.007470 | -0.001795 | -0.001795 |
| 2021-02-09 | 2021-02-01 | 0.008226 | 0.000000 | 0.000000 | 0.008226 | 0.021414 | -0.013188 | -0.013188 |
| 2021-02-10 | 2021-02-01 | 0.006046 | 0.000000 | 0.000000 | 0.006046 | 0.008609 | -0.002563 | -0.002563 |
| 2021-02-18 | 2021-02-01 | 0.020097 | 0.000000 | 0.000000 | 0.020097 | 0.026714 | -0.006617 | -0.006617 |
| 2021-02-19 | 2021-02-01 | 0.023670 | 0.000000 | 0.000000 | 0.023670 | 0.025629 | -0.001959 | -0.001959 |
| 2021-02-22 | 2021-02-01 | 0.012396 | 0.000000 | 0.000000 | 0.012396 | 0.005639 | 0.006757 | 0.006757 |
| 2021-02-23 | 2021-02-01 | -0.001593 | 0.000000 | 0.000000 | -0.001593 | -0.006207 | 0.004614 | 0.004614 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
