# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `200`
- Cost: `5.0` bps per one-way turnover
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
| gross_annualized_return | `0.176804` |
| net_annualized_return | `0.173324` |
| universe_annualized_return | `0.244434` |
| gross_annualized_excess | `-0.079240` |
| net_annualized_excess | `-0.081936` |
| gross_excess_ir | `-0.522753` |
| net_excess_ir | `-0.544065` |
| net_max_drawdown | `-0.143221` |
| average_turnover | `0.466607` |
| max_turnover | `1.000000` |
| average_eligible_count | `1064.500000` |
| average_selected_count | `200.000000` |
| label | `label_20d_t1` |
| topk | `200` |
| rebalance_every | `20` |
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
| 2024-01-30 | 2024-01-31 | 2024-03-07 | executed | 1101 | 200 | 1.000000 | 0.000500 | 0.084672 | 0.098968 | -0.020412 | 4.200000 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-04-08 | executed | 1120 | 200 | 0.375000 | 0.000188 | 0.020461 | 0.017612 | 0.000035 | 4.265000 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-05-09 | executed | 1116 | 200 | 0.385000 | 0.000193 | 0.048520 | 0.022076 | 0.021487 | 3.855000 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-06-06 | executed | 1100 | 200 | 0.375000 | 0.000188 | -0.033005 | -0.079821 | 0.049935 | 4.010000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-07-05 | executed | 1112 | 200 | 0.405000 | 0.000203 | -0.039290 | -0.038601 | -0.001825 | 3.905000 | 100.000000 |
| 2024-07-04 | 2024-07-05 | 2024-08-02 | executed | 1109 | 200 | 0.460000 | 0.000230 | 0.013338 | 0.011668 | 0.000432 | 4.045000 | 100.000000 |
| 2024-08-01 | 2024-08-02 | 2024-08-30 | executed | 1086 | 200 | 0.440000 | 0.000220 | -0.033864 | -0.030703 | -0.004474 | 3.915000 | 100.000000 |
| 2024-08-29 | 2024-08-30 | 2024-10-08 | executed | 1094 | 200 | 0.405000 | 0.000203 | 0.272691 | 0.331549 | -0.047701 | 3.975000 | 100.000000 |
| 2024-09-30 | 2024-10-08 | 2024-11-05 | executed | 755 | 200 | 0.605000 | 0.000302 | -0.006207 | 0.007102 | -0.016638 | 3.905000 | 100.000000 |
| 2024-11-04 | 2024-11-05 | 2024-12-03 | executed | 1039 | 200 | 0.530000 | 0.000265 | -0.008248 | 0.018639 | -0.029109 | 3.765000 | 100.000000 |

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
