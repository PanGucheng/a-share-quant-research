# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `100`
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
| gross_annualized_return | `0.054990` |
| net_annualized_return | `0.041071` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.033287` |
| net_annualized_excess | `0.019663` |
| gross_excess_ir | `0.336439` |
| net_excess_ir | `0.224076` |
| net_max_drawdown | `-0.195677` |
| average_turnover | `0.527714` |
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
| weight_preset | `low_risk_rev` |
| score_weights | `std_20:-1,amplitude_20:-1,rev_5:0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 100 | 1.000000 | 0.002000 | 0.064230 | -0.002832 | 0.064611 | 3.830000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 100 | 0.490000 | 0.000980 | 0.024554 | 0.044414 | -0.019787 | 3.670000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 100 | 0.540000 | 0.001080 | -0.025345 | -0.002538 | -0.023398 | 3.760000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 100 | 0.480000 | 0.000960 | 0.027527 | 0.061029 | -0.032003 | 3.750000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 100 | 0.530000 | 0.001060 | -0.013730 | 0.005843 | -0.020419 | 3.580000 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 100 | 0.530000 | 0.001060 | -0.017951 | 0.029714 | -0.048332 | 3.660000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 100 | 0.420000 | 0.000840 | 0.070497 | 0.064252 | 0.004478 | 3.690000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 100 | 0.500000 | 0.001000 | 0.024618 | -0.025757 | 0.050046 | 3.580000 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 100 | 0.610000 | 0.001220 | 0.002137 | -0.007317 | 0.008316 | 3.490000 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 100 | 0.600000 | 0.001200 | 0.030185 | 0.055793 | -0.024910 | 3.640000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.005230 | 1.000000 | 0.002000 | -0.007230 | -0.013386 | 0.008156 | 0.006156 |
| 2021-02-04 | 2021-02-01 | -0.013127 | 0.000000 | 0.000000 | -0.013127 | -0.018752 | 0.005626 | 0.005626 |
| 2021-02-05 | 2021-02-01 | 0.006505 | 0.000000 | 0.000000 | 0.006505 | -0.016112 | 0.022616 | 0.022616 |
| 2021-02-08 | 2021-02-01 | 0.005256 | 0.000000 | 0.000000 | 0.005256 | 0.007470 | -0.002214 | -0.002214 |
| 2021-02-09 | 2021-02-01 | 0.007790 | 0.000000 | 0.000000 | 0.007790 | 0.021414 | -0.013623 | -0.013623 |
| 2021-02-10 | 2021-02-01 | 0.005216 | 0.000000 | 0.000000 | 0.005216 | 0.008609 | -0.003393 | -0.003393 |
| 2021-02-18 | 2021-02-01 | 0.020120 | 0.000000 | 0.000000 | 0.020120 | 0.026714 | -0.006594 | -0.006594 |
| 2021-02-19 | 2021-02-01 | 0.023099 | 0.000000 | 0.000000 | 0.023099 | 0.025629 | -0.002530 | -0.002530 |
| 2021-02-22 | 2021-02-01 | 0.011015 | 0.000000 | 0.000000 | 0.011015 | 0.005639 | 0.005375 | 0.005375 |
| 2021-02-23 | 2021-02-01 | -0.002119 | 0.000000 | 0.000000 | -0.002119 | -0.006207 | 0.004088 | 0.004088 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
