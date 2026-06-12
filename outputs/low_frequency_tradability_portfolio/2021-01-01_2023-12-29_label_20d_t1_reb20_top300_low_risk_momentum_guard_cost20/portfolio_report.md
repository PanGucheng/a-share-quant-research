# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `300`
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
| gross_annualized_return | `0.035007` |
| net_annualized_return | `0.022460` |
| universe_annualized_return | `0.005710` |
| gross_annualized_excess | `0.020326` |
| net_annualized_excess | `0.007965` |
| gross_excess_ir | `0.285901` |
| net_excess_ir | `0.137629` |
| net_max_drawdown | `-0.257693` |
| average_turnover | `0.484095` |
| max_turnover | `1.000000` |
| average_eligible_count | `1123.057143` |
| average_selected_count | `300.000000` |
| label | `label_20d_t1` |
| topk | `300` |
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
| 2021-02-01 | 2021-02-02 | 2021-03-09 | executed | 1116 | 300 | 1.000000 | 0.002000 | 0.043277 | -0.002832 | 0.044896 | 3.720000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-04-07 | executed | 1121 | 300 | 0.473333 | 0.000947 | 0.024924 | 0.044414 | -0.019264 | 3.680000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-05-10 | executed | 1124 | 300 | 0.463333 | 0.000927 | -0.022897 | -0.002538 | -0.020654 | 3.723333 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-06-07 | executed | 1118 | 300 | 0.456667 | 0.000913 | 0.043821 | 0.061029 | -0.016498 | 3.696667 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-07-06 | executed | 1128 | 300 | 0.463333 | 0.000927 | -0.008194 | 0.005843 | -0.014652 | 3.646667 | 100.000000 |
| 2021-07-05 | 2021-07-06 | 2021-08-03 | executed | 1124 | 300 | 0.493333 | 0.000987 | -0.003630 | 0.029714 | -0.033737 | 3.680000 | 100.000000 |
| 2021-08-02 | 2021-08-03 | 2021-08-31 | executed | 1113 | 300 | 0.456667 | 0.000913 | 0.052190 | 0.064252 | -0.012305 | 3.633333 | 100.000000 |
| 2021-08-30 | 2021-08-31 | 2021-09-30 | executed | 1121 | 300 | 0.486667 | 0.000973 | 0.022246 | -0.025757 | 0.047797 | 3.593333 | 100.000000 |
| 2021-09-29 | 2021-09-30 | 2021-11-04 | executed | 1114 | 300 | 0.546667 | 0.001093 | 0.015642 | -0.007317 | 0.022212 | 3.663333 | 100.000000 |
| 2021-11-03 | 2021-11-04 | 2021-12-02 | executed | 1147 | 300 | 0.500000 | 0.001000 | 0.047462 | 0.055793 | -0.008354 | 3.673333 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.011230 | 1.000000 | 0.002000 | -0.013230 | -0.013386 | 0.002157 | 0.000157 |
| 2021-02-04 | 2021-02-01 | -0.016882 | 0.000000 | 0.000000 | -0.016882 | -0.018752 | 0.001870 | 0.001870 |
| 2021-02-05 | 2021-02-01 | -0.004512 | 0.000000 | 0.000000 | -0.004512 | -0.016112 | 0.011599 | 0.011599 |
| 2021-02-08 | 2021-02-01 | 0.007003 | 0.000000 | 0.000000 | 0.007003 | 0.007470 | -0.000467 | -0.000467 |
| 2021-02-09 | 2021-02-01 | 0.013414 | 0.000000 | 0.000000 | 0.013414 | 0.021414 | -0.008000 | -0.008000 |
| 2021-02-10 | 2021-02-01 | 0.008503 | 0.000000 | 0.000000 | 0.008503 | 0.008609 | -0.000106 | -0.000106 |
| 2021-02-18 | 2021-02-01 | 0.024245 | 0.000000 | 0.000000 | 0.024245 | 0.026714 | -0.002469 | -0.002469 |
| 2021-02-19 | 2021-02-01 | 0.028052 | 0.000000 | 0.000000 | 0.028052 | 0.025629 | 0.002423 | 0.002423 |
| 2021-02-22 | 2021-02-01 | 0.010446 | 0.000000 | 0.000000 | 0.010446 | 0.005639 | 0.004806 | 0.004806 |
| 2021-02-23 | 2021-02-01 | -0.003503 | 0.000000 | 0.000000 | -0.003503 | -0.006207 | 0.002704 | 0.002704 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
