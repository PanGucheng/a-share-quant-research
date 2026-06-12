# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `300`
- Cost: `20.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,ret_20:-0.25`

## Summary

| metric | value |
| --- | ---: |
| start_date | `2024-02-01` |
| end_date | `2026-06-02` |
| trading_days | `560` |
| rebalance_count | `29` |
| executed_rebalances | `28` |
| skipped_rebalances | `1` |
| skipped_rebalance_rate | `0.034483` |
| gross_annualized_return | `0.178674` |
| net_annualized_return | `0.165929` |
| universe_annualized_return | `0.244434` |
| gross_annualized_excess | `-0.073861` |
| net_annualized_excess | `-0.083781` |
| gross_excess_ir | `-0.579297` |
| net_excess_ir | `-0.670234` |
| net_max_drawdown | `-0.150227` |
| average_turnover | `0.428095` |
| max_turnover | `1.000000` |
| average_eligible_count | `1064.500000` |
| average_selected_count | `300.000000` |
| label | `label_20d_t1` |
| topk | `300` |
| rebalance_every | `20` |
| cost_bps | `20.000000` |
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
| 2024-01-30 | 2024-01-31 | 2024-03-07 | executed | 1101 | 300 | 1.000000 | 0.002000 | 0.089716 | 0.098968 | -0.014107 | 4.073333 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-04-08 | executed | 1120 | 300 | 0.340000 | 0.000680 | 0.013668 | 0.017612 | -0.006383 | 4.183333 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-05-09 | executed | 1116 | 300 | 0.343333 | 0.000687 | 0.048236 | 0.022076 | 0.021714 | 3.826667 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-06-06 | executed | 1100 | 300 | 0.366667 | 0.000733 | -0.037905 | -0.079821 | 0.044677 | 4.010000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-07-05 | executed | 1112 | 300 | 0.403333 | 0.000807 | -0.044211 | -0.038601 | -0.006738 | 3.913333 | 100.000000 |
| 2024-07-04 | 2024-07-05 | 2024-08-02 | executed | 1109 | 300 | 0.376667 | 0.000753 | 0.009667 | 0.011668 | -0.002890 | 4.046667 | 100.000000 |
| 2024-08-01 | 2024-08-02 | 2024-08-30 | executed | 1086 | 300 | 0.396667 | 0.000793 | -0.033007 | -0.030703 | -0.003331 | 3.900000 | 100.000000 |
| 2024-08-29 | 2024-08-30 | 2024-10-08 | executed | 1094 | 300 | 0.360000 | 0.000720 | 0.267983 | 0.331549 | -0.051132 | 3.956667 | 100.000000 |
| 2024-09-30 | 2024-10-08 | 2024-11-05 | executed | 755 | 300 | 0.500000 | 0.001000 | -0.006531 | 0.007102 | -0.016704 | 3.930000 | 100.000000 |
| 2024-11-04 | 2024-11-05 | 2024-12-03 | executed | 1039 | 300 | 0.446667 | 0.000893 | -0.008729 | 0.018639 | -0.029266 | 3.836667 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 | 2024-01-30 | -0.005674 | 1.000000 | 0.002000 | -0.007674 | -0.010364 | 0.004690 | 0.002690 |
| 2024-02-02 | 2024-01-30 | -0.018633 | 0.000000 | 0.000000 | -0.018633 | -0.030026 | 0.011393 | 0.011393 |
| 2024-02-05 | 2024-01-30 | -0.018505 | 0.000000 | 0.000000 | -0.018505 | -0.055654 | 0.037149 | 0.037149 |
| 2024-02-06 | 2024-01-30 | 0.053672 | 0.000000 | 0.000000 | 0.053672 | 0.045001 | 0.008671 | 0.008671 |
| 2024-02-07 | 2024-01-30 | 0.031749 | 0.000000 | 0.000000 | 0.031749 | 0.017863 | 0.013886 | 0.013886 |
| 2024-02-08 | 2024-01-30 | 0.011949 | 0.000000 | 0.000000 | 0.011949 | 0.039580 | -0.027630 | -0.027630 |
| 2024-02-19 | 2024-01-30 | 0.005298 | 0.000000 | 0.000000 | 0.005298 | 0.021874 | -0.016576 | -0.016576 |
| 2024-02-20 | 2024-01-30 | 0.002492 | 0.000000 | 0.000000 | 0.002492 | 0.008301 | -0.005809 | -0.005809 |
| 2024-02-21 | 2024-01-30 | 0.005789 | 0.000000 | 0.000000 | 0.005789 | 0.009547 | -0.003758 | -0.003758 |
| 2024-02-22 | 2024-01-30 | 0.008233 | 0.000000 | 0.000000 | 0.008233 | 0.017930 | -0.009698 | -0.009698 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
