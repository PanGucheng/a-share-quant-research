# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `200`
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
| gross_annualized_return | `0.039314` |
| net_annualized_return | `0.036023` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.022015` |
| net_annualized_excess | `0.018781` |
| gross_excess_ir | `0.275409` |
| net_excess_ir | `0.242352` |
| net_max_drawdown | `-0.233206` |
| average_turnover | `0.503857` |
| max_turnover | `1.000000` |
| average_eligible_count | `1123.057143` |
| average_selected_count | `200.000000` |
| label | `label_20d_t1` |
| topk | `200` |
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
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 200 | 1.000000 | 0.000500 | 0.057659 | -0.002832 | 0.058852 | 3.750000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 200 | 0.480000 | 0.000240 | 0.026360 | 0.044414 | -0.017949 | 3.655000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 200 | 0.495000 | 0.000247 | -0.027212 | -0.002538 | -0.025093 | 3.715000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 200 | 0.455000 | 0.000227 | 0.034227 | 0.061029 | -0.025606 | 3.680000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 200 | 0.505000 | 0.000253 | -0.011182 | 0.005843 | -0.017684 | 3.590000 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 200 | 0.535000 | 0.000267 | -0.007409 | 0.029714 | -0.037558 | 3.620000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 200 | 0.480000 | 0.000240 | 0.061103 | 0.064252 | -0.004015 | 3.600000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 200 | 0.495000 | 0.000247 | 0.023837 | -0.025757 | 0.049714 | 3.585000 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 200 | 0.600000 | 0.000300 | 0.010971 | -0.007317 | 0.017284 | 3.625000 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 200 | 0.525000 | 0.000263 | 0.039457 | 0.055793 | -0.016031 | 3.670000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.008852 | 1.000000 | 0.000500 | -0.009352 | -0.013386 | 0.004535 | 0.004035 |
| 2021-02-04 | 2021-02-01 | -0.015213 | 0.000000 | 0.000000 | -0.015213 | -0.018752 | 0.003540 | 0.003540 |
| 2021-02-05 | 2021-02-01 | -0.001469 | 0.000000 | 0.000000 | -0.001469 | -0.016112 | 0.014643 | 0.014643 |
| 2021-02-08 | 2021-02-01 | 0.008382 | 0.000000 | 0.000000 | 0.008382 | 0.007470 | 0.000912 | 0.000912 |
| 2021-02-09 | 2021-02-01 | 0.011910 | 0.000000 | 0.000000 | 0.011910 | 0.021414 | -0.009504 | -0.009504 |
| 2021-02-10 | 2021-02-01 | 0.006497 | 0.000000 | 0.000000 | 0.006497 | 0.008609 | -0.002112 | -0.002112 |
| 2021-02-18 | 2021-02-01 | 0.023599 | 0.000000 | 0.000000 | 0.023599 | 0.026714 | -0.003115 | -0.003115 |
| 2021-02-19 | 2021-02-01 | 0.026592 | 0.000000 | 0.000000 | 0.026592 | 0.025629 | 0.000963 | 0.000963 |
| 2021-02-22 | 2021-02-01 | 0.012012 | 0.000000 | 0.000000 | 0.012012 | 0.005639 | 0.006373 | 0.006373 |
| 2021-02-23 | 2021-02-01 | -0.001298 | 0.000000 | 0.000000 | -0.001298 | -0.006207 | 0.004909 | 0.004909 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
