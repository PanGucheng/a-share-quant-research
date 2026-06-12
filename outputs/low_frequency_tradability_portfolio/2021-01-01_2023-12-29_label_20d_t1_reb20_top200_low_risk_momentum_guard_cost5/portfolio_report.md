# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `200`
- Cost: `5.0` bps per one-way turnover
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
| gross_annualized_return | `0.042101` |
| net_annualized_return | `0.038712` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.024862` |
| net_annualized_excess | `0.021531` |
| gross_excess_ir | `0.304226` |
| net_excess_ir | `0.270328` |
| net_max_drawdown | `-0.237083` |
| average_turnover | `0.517571` |
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
| weight_preset | `low_risk_momentum_guard` |
| score_weights | `std_20:-1,amplitude_20:-1,ret_20:-0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 200 | 1.000000 | 0.000500 | 0.059967 | -0.002832 | 0.061173 | 3.725000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 200 | 0.505000 | 0.000253 | 0.024719 | 0.044414 | -0.019550 | 3.680000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 200 | 0.510000 | 0.000255 | -0.027250 | -0.002538 | -0.025133 | 3.705000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 200 | 0.480000 | 0.000240 | 0.037778 | 0.061029 | -0.022245 | 3.700000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 200 | 0.510000 | 0.000255 | -0.010779 | 0.005843 | -0.017321 | 3.565000 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 200 | 0.535000 | 0.000267 | -0.007746 | 0.029714 | -0.037931 | 3.630000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 200 | 0.465000 | 0.000232 | 0.054490 | 0.064252 | -0.010306 | 3.625000 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 200 | 0.530000 | 0.000265 | 0.028631 | -0.025757 | 0.054208 | 3.580000 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 200 | 0.615000 | 0.000307 | 0.018613 | -0.007317 | 0.025034 | 3.615000 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 200 | 0.555000 | 0.000277 | 0.045344 | 0.055793 | -0.010469 | 3.655000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.009730 | 1.000000 | 0.000500 | -0.010230 | -0.013386 | 0.003656 | 0.003156 |
| 2021-02-04 | 2021-02-01 | -0.015919 | 0.000000 | 0.000000 | -0.015919 | -0.018752 | 0.002833 | 0.002833 |
| 2021-02-05 | 2021-02-01 | -0.000271 | 0.000000 | 0.000000 | -0.000271 | -0.016112 | 0.015841 | 0.015841 |
| 2021-02-08 | 2021-02-01 | 0.007296 | 0.000000 | 0.000000 | 0.007296 | 0.007470 | -0.000175 | -0.000175 |
| 2021-02-09 | 2021-02-01 | 0.012073 | 0.000000 | 0.000000 | 0.012073 | 0.021414 | -0.009340 | -0.009340 |
| 2021-02-10 | 2021-02-01 | 0.005702 | 0.000000 | 0.000000 | 0.005702 | 0.008609 | -0.002907 | -0.002907 |
| 2021-02-18 | 2021-02-01 | 0.024789 | 0.000000 | 0.000000 | 0.024789 | 0.026714 | -0.001925 | -0.001925 |
| 2021-02-19 | 2021-02-01 | 0.027419 | 0.000000 | 0.000000 | 0.027419 | 0.025629 | 0.001790 | 0.001790 |
| 2021-02-22 | 2021-02-01 | 0.012741 | 0.000000 | 0.000000 | 0.012741 | 0.005639 | 0.007102 | 0.007102 |
| 2021-02-23 | 2021-02-01 | -0.001754 | 0.000000 | 0.000000 | -0.001754 | -0.006207 | 0.004453 | 0.004453 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
