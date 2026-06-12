# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `200`
- Cost: `5.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,ret_20:-0.25`

## Summary

| metric | value |
| --- | ---: |
| start_date | `2024-02-01` |
| end_date | `2026-06-02` |
| trading_days | `560` |
| rebalance_count | `57` |
| executed_rebalances | `56` |
| skipped_rebalances | `1` |
| skipped_rebalance_rate | `0.017544` |
| gross_annualized_return | `0.145834` |
| net_annualized_return | `0.140822` |
| universe_annualized_return | `0.231646` |
| gross_annualized_excess | `-0.095019` |
| net_annualized_excess | `-0.098955` |
| gross_excess_ir | `-0.631388` |
| net_excess_ir | `-0.662179` |
| net_max_drawdown | `-0.141965` |
| average_turnover | `0.346071` |
| max_turnover | `1.000000` |
| average_eligible_count | `1070.589286` |
| average_selected_count | `200.000000` |
| label | `label_10d_t1` |
| topk | `200` |
| rebalance_every | `10` |
| cost_bps | `5.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| window_start | `2024-01-01` |
| window_end | `2026-06-09` |
| weight_preset | `low_risk_momentum_guard` |
| score_weights | `std_20:-1,amplitude_20:-1,ret_20:-0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-01-30 | 2024-01-31 | 2024-02-22 | executed | 1101 | 200 | 1.000000 | 0.000500 | 0.074205 | 0.061360 | 0.007166 | 4.200000 | 100.000000 |
| 2024-02-21 | 2024-02-22 | 2024-03-07 | executed | 1114 | 200 | 0.280000 | 0.000140 | 0.009684 | 0.036383 | -0.028695 | 4.435000 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-03-21 | executed | 1120 | 200 | 0.230000 | 0.000115 | 0.008699 | 0.062384 | -0.051159 | 4.265000 | 100.000000 |
| 2024-03-20 | 2024-03-21 | 2024-04-08 | executed | 1111 | 200 | 0.355000 | 0.000178 | -0.014186 | -0.044535 | 0.029909 | 3.890000 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-04-22 | executed | 1117 | 200 | 0.310000 | 0.000155 | 0.014074 | -0.045381 | 0.058586 | 3.855000 | 100.000000 |
| 2024-04-19 | 2024-04-22 | 2024-05-09 | executed | 1116 | 200 | 0.275000 | 0.000138 | 0.032718 | 0.064582 | -0.030574 | 4.080000 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-05-23 | executed | 1100 | 200 | 0.285000 | 0.000143 | -0.010381 | -0.027807 | 0.017548 | 4.010000 | 100.000000 |
| 2024-05-22 | 2024-05-23 | 2024-06-06 | executed | 1096 | 200 | 0.310000 | 0.000155 | -0.026108 | -0.057492 | 0.032766 | 3.910000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-06-21 | executed | 1114 | 200 | 0.355000 | 0.000178 | -0.022829 | -0.007935 | -0.015276 | 3.900000 | 100.000000 |
| 2024-06-20 | 2024-06-21 | 2024-07-05 | executed | 1111 | 200 | 0.335000 | 0.000167 | -0.021367 | -0.031717 | 0.009719 | 3.965000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 | 2024-01-30 | -0.005129 | 1.000000 | 0.000500 | -0.005629 | -0.010364 | 0.005235 | 0.004735 |
| 2024-02-02 | 2024-01-30 | -0.013895 | 0.000000 | 0.000000 | -0.013895 | -0.030026 | 0.016131 | 0.016131 |
| 2024-02-05 | 2024-01-30 | -0.008423 | 0.000000 | 0.000000 | -0.008423 | -0.055654 | 0.047231 | 0.047231 |
| 2024-02-06 | 2024-01-30 | 0.048443 | 0.000000 | 0.000000 | 0.048443 | 0.045001 | 0.003441 | 0.003441 |
| 2024-02-07 | 2024-01-30 | 0.026642 | 0.000000 | 0.000000 | 0.026642 | 0.017863 | 0.008779 | 0.008779 |
| 2024-02-08 | 2024-01-30 | 0.005695 | 0.000000 | 0.000000 | 0.005695 | 0.039580 | -0.033884 | -0.033884 |
| 2024-02-19 | 2024-01-30 | 0.003873 | 0.000000 | 0.000000 | 0.003873 | 0.021874 | -0.018001 | -0.018001 |
| 2024-02-20 | 2024-01-30 | 0.003526 | 0.000000 | 0.000000 | 0.003526 | 0.008301 | -0.004775 | -0.004775 |
| 2024-02-21 | 2024-01-30 | 0.006003 | 0.000000 | 0.000000 | 0.006003 | 0.009547 | -0.003544 | -0.003544 |
| 2024-02-22 | 2024-01-30 | 0.007051 | 0.000000 | 0.000000 | 0.007051 | 0.017930 | -0.010880 | -0.010880 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
