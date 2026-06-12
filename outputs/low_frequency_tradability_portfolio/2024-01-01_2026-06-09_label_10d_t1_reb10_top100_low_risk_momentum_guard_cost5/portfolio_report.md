# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `100`
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
| gross_annualized_return | `0.118657` |
| net_annualized_return | `0.113314` |
| universe_annualized_return | `0.231646` |
| gross_annualized_excess | `-0.122290` |
| net_annualized_excess | `-0.126456` |
| gross_excess_ir | `-0.688486` |
| net_excess_ir | `-0.716821` |
| net_max_drawdown | `-0.133742` |
| average_turnover | `0.377857` |
| max_turnover | `1.000000` |
| average_eligible_count | `1070.589286` |
| average_selected_count | `100.000000` |
| label | `label_10d_t1` |
| topk | `100` |
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
| 2024-01-30 | 2024-01-31 | 2024-02-22 | executed | 1101 | 100 | 1.000000 | 0.000500 | 0.068890 | 0.061360 | 0.000888 | 4.380000 | 100.000000 |
| 2024-02-21 | 2024-02-22 | 2024-03-07 | executed | 1114 | 100 | 0.300000 | 0.000150 | 0.006519 | 0.036383 | -0.032116 | 4.590000 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-03-21 | executed | 1120 | 100 | 0.220000 | 0.000110 | 0.003599 | 0.062384 | -0.056005 | 4.380000 | 100.000000 |
| 2024-03-20 | 2024-03-21 | 2024-04-08 | executed | 1111 | 100 | 0.380000 | 0.000190 | -0.004189 | -0.044535 | 0.039986 | 3.930000 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-04-22 | executed | 1117 | 100 | 0.330000 | 0.000165 | 0.014223 | -0.045381 | 0.058271 | 3.880000 | 100.000000 |
| 2024-04-19 | 2024-04-22 | 2024-05-09 | executed | 1116 | 100 | 0.240000 | 0.000120 | 0.027722 | 0.064582 | -0.035495 | 4.180000 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-05-23 | executed | 1100 | 100 | 0.280000 | 0.000140 | -0.002982 | -0.027807 | 0.025072 | 4.040000 | 100.000000 |
| 2024-05-22 | 2024-05-23 | 2024-06-06 | executed | 1096 | 100 | 0.350000 | 0.000175 | -0.032672 | -0.057492 | 0.025811 | 3.970000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-06-21 | executed | 1114 | 100 | 0.400000 | 0.000200 | -0.027227 | -0.007935 | -0.019779 | 3.960000 | 100.000000 |
| 2024-06-20 | 2024-06-21 | 2024-07-05 | executed | 1111 | 100 | 0.380000 | 0.000190 | -0.019802 | -0.031717 | 0.011046 | 4.050000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 | 2024-01-30 | -0.002864 | 1.000000 | 0.000500 | -0.003364 | -0.010364 | 0.007500 | 0.007000 |
| 2024-02-02 | 2024-01-30 | -0.008898 | 0.000000 | 0.000000 | -0.008898 | -0.030026 | 0.021128 | 0.021128 |
| 2024-02-05 | 2024-01-30 | -0.000721 | 0.000000 | 0.000000 | -0.000721 | -0.055654 | 0.054933 | 0.054933 |
| 2024-02-06 | 2024-01-30 | 0.037655 | 0.000000 | 0.000000 | 0.037655 | 0.045001 | -0.007347 | -0.007347 |
| 2024-02-07 | 2024-01-30 | 0.018209 | 0.000000 | 0.000000 | 0.018209 | 0.017863 | 0.000346 | 0.000346 |
| 2024-02-08 | 2024-01-30 | 0.003228 | 0.000000 | 0.000000 | 0.003228 | 0.039580 | -0.036352 | -0.036352 |
| 2024-02-19 | 2024-01-30 | 0.004391 | 0.000000 | 0.000000 | 0.004391 | 0.021874 | -0.017483 | -0.017483 |
| 2024-02-20 | 2024-01-30 | 0.004736 | 0.000000 | 0.000000 | 0.004736 | 0.008301 | -0.003566 | -0.003566 |
| 2024-02-21 | 2024-01-30 | 0.006743 | 0.000000 | 0.000000 | 0.006743 | 0.009547 | -0.002804 | -0.002804 |
| 2024-02-22 | 2024-01-30 | 0.005608 | 0.000000 | 0.000000 | 0.005608 | 0.017930 | -0.012322 | -0.012322 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
