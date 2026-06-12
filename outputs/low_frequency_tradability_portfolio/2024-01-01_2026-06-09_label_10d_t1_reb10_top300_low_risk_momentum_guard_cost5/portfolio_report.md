# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `300`
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
| gross_annualized_return | `0.158435` |
| net_annualized_return | `0.153664` |
| universe_annualized_return | `0.231646` |
| gross_annualized_excess | `-0.080863` |
| net_annualized_excess | `-0.084627` |
| gross_excess_ir | `-0.628632` |
| net_excess_ir | `-0.662337` |
| net_max_drawdown | `-0.152633` |
| average_turnover | `0.325774` |
| max_turnover | `1.000000` |
| average_eligible_count | `1070.589286` |
| average_selected_count | `300.000000` |
| label | `label_10d_t1` |
| topk | `300` |
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
| 2024-01-30 | 2024-01-31 | 2024-02-22 | executed | 1101 | 300 | 1.000000 | 0.000500 | 0.076246 | 0.061360 | 0.010393 | 4.073333 | 100.000000 |
| 2024-02-21 | 2024-02-22 | 2024-03-07 | executed | 1114 | 300 | 0.266667 | 0.000133 | 0.012174 | 0.036383 | -0.025995 | 4.360000 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-03-21 | executed | 1120 | 300 | 0.176667 | 0.000088 | 0.010215 | 0.062384 | -0.049696 | 4.183333 | 100.000000 |
| 2024-03-20 | 2024-03-21 | 2024-04-08 | executed | 1111 | 300 | 0.283333 | 0.000142 | -0.010010 | -0.044535 | 0.034487 | 3.850000 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-04-22 | executed | 1117 | 300 | 0.290000 | 0.000145 | 0.010055 | -0.045381 | 0.054771 | 3.830000 | 100.000000 |
| 2024-04-19 | 2024-04-22 | 2024-05-09 | executed | 1116 | 300 | 0.290000 | 0.000145 | 0.039152 | 0.064582 | -0.024467 | 4.020000 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-05-23 | executed | 1100 | 300 | 0.273333 | 0.000137 | -0.015989 | -0.027807 | 0.011815 | 4.010000 | 100.000000 |
| 2024-05-22 | 2024-05-23 | 2024-06-06 | executed | 1096 | 300 | 0.283333 | 0.000142 | -0.025720 | -0.057492 | 0.033210 | 3.880000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-06-21 | executed | 1114 | 300 | 0.370000 | 0.000185 | -0.023707 | -0.007935 | -0.016135 | 3.913333 | 100.000000 |
| 2024-06-20 | 2024-06-21 | 2024-07-05 | executed | 1111 | 300 | 0.296667 | 0.000148 | -0.024148 | -0.031717 | 0.007106 | 3.906667 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 | 2024-01-30 | -0.005674 | 1.000000 | 0.000500 | -0.006174 | -0.010364 | 0.004690 | 0.004190 |
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
