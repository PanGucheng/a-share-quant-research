# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `100`
- Cost: `10.0` bps per one-way turnover
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
| gross_annualized_return | `0.162958` |
| net_annualized_return | `0.155469` |
| universe_annualized_return | `0.244434` |
| gross_annualized_excess | `-0.095617` |
| net_annualized_excess | `-0.101380` |
| gross_excess_ir | `-0.524664` |
| net_excess_ir | `-0.563755` |
| net_max_drawdown | `-0.126877` |
| average_turnover | `0.508571` |
| max_turnover | `1.000000` |
| average_eligible_count | `1064.500000` |
| average_selected_count | `100.000000` |
| label | `label_20d_t1` |
| topk | `100` |
| rebalance_every | `20` |
| cost_bps | `10.000000` |
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
| 2024-01-30 | 2024-01-31 | 2024-03-07 | executed | 1101 | 100 | 1.000000 | 0.001000 | 0.078183 | 0.098968 | -0.027886 | 4.380000 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-04-08 | executed | 1120 | 100 | 0.360000 | 0.000360 | 0.016783 | 0.017612 | -0.003822 | 4.380000 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-05-09 | executed | 1116 | 100 | 0.450000 | 0.000450 | 0.039331 | 0.022076 | 0.011908 | 3.880000 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-06-06 | executed | 1100 | 100 | 0.350000 | 0.000350 | -0.020998 | -0.079821 | 0.062761 | 4.040000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-07-05 | executed | 1112 | 100 | 0.480000 | 0.000480 | -0.040852 | -0.038601 | -0.003768 | 3.960000 | 100.000000 |
| 2024-07-04 | 2024-07-05 | 2024-08-02 | executed | 1109 | 100 | 0.460000 | 0.000460 | 0.029999 | 0.011668 | 0.016203 | 4.180000 | 100.000000 |
| 2024-08-01 | 2024-08-02 | 2024-08-30 | executed | 1086 | 100 | 0.420000 | 0.000420 | -0.038302 | -0.030703 | -0.009427 | 3.990000 | 100.000000 |
| 2024-08-29 | 2024-08-30 | 2024-10-08 | executed | 1094 | 100 | 0.450000 | 0.000450 | 0.274988 | 0.331549 | -0.045973 | 4.020000 | 100.000000 |
| 2024-09-30 | 2024-10-08 | 2024-11-05 | executed | 755 | 100 | 0.740000 | 0.000740 | -0.016773 | 0.007102 | -0.027664 | 3.850000 | 100.000000 |
| 2024-11-04 | 2024-11-05 | 2024-12-03 | executed | 1039 | 100 | 0.590000 | 0.000590 | -0.002166 | 0.018639 | -0.023747 | 3.830000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 | 2024-01-30 | -0.002864 | 1.000000 | 0.001000 | -0.003864 | -0.010364 | 0.007500 | 0.006500 |
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
