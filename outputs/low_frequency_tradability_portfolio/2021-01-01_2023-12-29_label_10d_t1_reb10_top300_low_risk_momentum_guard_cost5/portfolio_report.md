# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `300`
- Cost: `5.0` bps per one-way turnover
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
| gross_annualized_return | `0.040572` |
| net_annualized_return | `0.035611` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.027781` |
| net_annualized_excess | `0.022884` |
| gross_excess_ir | `0.369315` |
| net_excess_ir | `0.312267` |
| net_max_drawdown | `-0.257350` |
| average_turnover | `0.379238` |
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
| weight_preset | `low_risk_momentum_guard` |
| score_weights | `std_20:-1,amplitude_20:-1,ret_20:-0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 300 | 1.000000 | 0.000500 | 0.054924 | 0.040415 | 0.013529 | 3.720000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 300 | 0.380000 | 0.000190 | -0.003645 | -0.042360 | 0.039400 | 3.703333 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 300 | 0.340000 | 0.000170 | 0.018631 | 0.023996 | -0.005601 | 3.680000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 300 | 0.383333 | 0.000192 | 0.007898 | 0.019674 | -0.011858 | 3.596667 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 300 | 0.353333 | 0.000177 | 0.002706 | 0.004745 | -0.002226 | 3.723333 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 300 | 0.370000 | 0.000185 | -0.025824 | -0.004462 | -0.021577 | 3.656667 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 300 | 0.366667 | 0.000183 | 0.023254 | 0.021835 | 0.001299 | 3.696667 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 300 | 0.373333 | 0.000187 | 0.021249 | 0.037367 | -0.015757 | 3.690000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 300 | 0.380000 | 0.000190 | -0.002446 | 0.005246 | -0.008007 | 3.650000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 300 | 0.386667 | 0.000193 | -0.004677 | 0.002039 | -0.007199 | 3.690000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.011339 | 1.000000 | 0.000500 | -0.011839 | -0.013386 | 0.002047 | 0.001547 |
| 2021-02-04 | 2021-02-01 | -0.016949 | 0.000000 | 0.000000 | -0.016949 | -0.018752 | 0.001803 | 0.001803 |
| 2021-02-05 | 2021-02-01 | -0.004710 | 0.000000 | 0.000000 | -0.004710 | -0.016112 | 0.011401 | 0.011401 |
| 2021-02-08 | 2021-02-01 | 0.006978 | 0.000000 | 0.000000 | 0.006978 | 0.007470 | -0.000492 | -0.000492 |
| 2021-02-09 | 2021-02-01 | 0.013507 | 0.000000 | 0.000000 | 0.013507 | 0.021414 | -0.007907 | -0.007907 |
| 2021-02-10 | 2021-02-01 | 0.008546 | 0.000000 | 0.000000 | 0.008546 | 0.008609 | -0.000063 | -0.000063 |
| 2021-02-18 | 2021-02-01 | 0.024281 | 0.000000 | 0.000000 | 0.024281 | 0.026714 | -0.002433 | -0.002433 |
| 2021-02-19 | 2021-02-01 | 0.027782 | 0.000000 | 0.000000 | 0.027782 | 0.025629 | 0.002153 | 0.002153 |
| 2021-02-22 | 2021-02-01 | 0.010489 | 0.000000 | 0.000000 | 0.010489 | 0.005639 | 0.004850 | 0.004850 |
| 2021-02-23 | 2021-02-01 | -0.003508 | 0.000000 | 0.000000 | -0.003508 | -0.006207 | 0.002699 | 0.002699 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
