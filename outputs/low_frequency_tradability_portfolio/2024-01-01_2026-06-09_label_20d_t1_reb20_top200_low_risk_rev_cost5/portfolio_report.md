# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_20d_t1`
- Rebalance every: `20` trading days
- TopK: `200`
- Cost: `5.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,rev_5:0.25`

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
| gross_annualized_return | `0.172593` |
| net_annualized_return | `0.169288` |
| universe_annualized_return | `0.244434` |
| gross_annualized_excess | `-0.083305` |
| net_annualized_excess | `-0.085863` |
| gross_excess_ir | `-0.542272` |
| net_excess_ir | `-0.562234` |
| net_max_drawdown | `-0.139267` |
| average_turnover | `0.444643` |
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
| weight_preset | `low_risk_rev` |
| score_weights | `std_20:-1,amplitude_20:-1,rev_5:0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-01-30 | 2024-01-31 | 2024-03-07 | executed | 1101 | 200 | 1.000000 | 0.000500 | 0.084747 | 0.098968 | -0.020474 | 4.230000 | 100.000000 |
| 2024-03-06 | 2024-03-07 | 2024-04-08 | executed | 1120 | 200 | 0.355000 | 0.000178 | 0.020413 | 0.017612 | 0.000050 | 4.255000 | 100.000000 |
| 2024-04-03 | 2024-04-08 | 2024-05-09 | executed | 1116 | 200 | 0.355000 | 0.000178 | 0.051512 | 0.022076 | 0.024268 | 3.860000 | 100.000000 |
| 2024-05-08 | 2024-05-09 | 2024-06-06 | executed | 1100 | 200 | 0.340000 | 0.000170 | -0.034538 | -0.079821 | 0.048265 | 3.980000 | 100.000000 |
| 2024-06-05 | 2024-06-06 | 2024-07-05 | executed | 1112 | 200 | 0.380000 | 0.000190 | -0.037786 | -0.038601 | -0.000321 | 3.895000 | 100.000000 |
| 2024-07-04 | 2024-07-05 | 2024-08-02 | executed | 1109 | 200 | 0.430000 | 0.000215 | 0.016219 | 0.011668 | 0.003268 | 4.085000 | 100.000000 |
| 2024-08-01 | 2024-08-02 | 2024-08-30 | executed | 1086 | 200 | 0.400000 | 0.000200 | -0.033100 | -0.030703 | -0.003693 | 3.940000 | 100.000000 |
| 2024-08-29 | 2024-08-30 | 2024-10-08 | executed | 1094 | 200 | 0.360000 | 0.000180 | 0.256926 | 0.331549 | -0.060307 | 3.985000 | 100.000000 |
| 2024-09-30 | 2024-10-08 | 2024-11-05 | executed | 755 | 200 | 0.585000 | 0.000293 | -0.006381 | 0.007102 | -0.016887 | 3.905000 | 100.000000 |
| 2024-11-04 | 2024-11-05 | 2024-12-03 | executed | 1039 | 200 | 0.535000 | 0.000267 | -0.007730 | 0.018639 | -0.028575 | 3.745000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-02-01 | 2024-01-30 | -0.005117 | 1.000000 | 0.000500 | -0.005617 | -0.010364 | 0.005247 | 0.004747 |
| 2024-02-02 | 2024-01-30 | -0.013220 | 0.000000 | 0.000000 | -0.013220 | -0.030026 | 0.016806 | 0.016806 |
| 2024-02-05 | 2024-01-30 | -0.007384 | 0.000000 | 0.000000 | -0.007384 | -0.055654 | 0.048270 | 0.048270 |
| 2024-02-06 | 2024-01-30 | 0.048100 | 0.000000 | 0.000000 | 0.048100 | 0.045001 | 0.003099 | 0.003099 |
| 2024-02-07 | 2024-01-30 | 0.026372 | 0.000000 | 0.000000 | 0.026372 | 0.017863 | 0.008509 | 0.008509 |
| 2024-02-08 | 2024-01-30 | 0.005098 | 0.000000 | 0.000000 | 0.005098 | 0.039580 | -0.034482 | -0.034482 |
| 2024-02-19 | 2024-01-30 | 0.003636 | 0.000000 | 0.000000 | 0.003636 | 0.021874 | -0.018238 | -0.018238 |
| 2024-02-20 | 2024-01-30 | 0.003230 | 0.000000 | 0.000000 | 0.003230 | 0.008301 | -0.005072 | -0.005072 |
| 2024-02-21 | 2024-01-30 | 0.006418 | 0.000000 | 0.000000 | 0.006418 | 0.009547 | -0.003128 | -0.003128 |
| 2024-02-22 | 2024-01-30 | 0.006959 | 0.000000 | 0.000000 | 0.006959 | 0.017930 | -0.010972 | -0.010972 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
