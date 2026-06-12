# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `100`
- Cost: `5.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1`

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
| gross_annualized_return | `0.055185` |
| net_annualized_return | `0.049738` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.035597` |
| net_annualized_excess | `0.030255` |
| gross_excess_ir | `0.357183` |
| net_excess_ir | `0.313058` |
| net_max_drawdown | `-0.195216` |
| average_turnover | `0.410857` |
| max_turnover | `1.000000` |
| average_eligible_count | `1124.685714` |
| average_selected_count | `100.000000` |
| label | `label_10d_t1` |
| topk | `100` |
| rebalance_every | `10` |
| cost_bps | `5.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| window_start | `2021-01-01` |
| window_end | `2023-12-29` |
| weight_preset | `low_risk` |
| score_weights | `std_20:-1,amplitude_20:-1` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 100 | 1.000000 | 0.000500 | 0.061786 | 0.040415 | 0.019393 | 3.850000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 100 | 0.390000 | 0.000195 | 0.007055 | -0.042360 | 0.050147 | 3.790000 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 100 | 0.350000 | 0.000175 | 0.019720 | 0.023996 | -0.004602 | 3.660000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 100 | 0.410000 | 0.000205 | 0.005920 | 0.019674 | -0.013876 | 3.700000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 100 | 0.410000 | 0.000205 | -0.006210 | 0.004745 | -0.011277 | 3.750000 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 100 | 0.350000 | 0.000175 | -0.017921 | -0.004462 | -0.013661 | 3.740000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 100 | 0.450000 | 0.000225 | 0.013070 | 0.021835 | -0.008697 | 3.740000 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 100 | 0.420000 | 0.000210 | 0.007307 | 0.037367 | -0.029356 | 3.590000 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 100 | 0.440000 | 0.000220 | -0.009834 | 0.005246 | -0.015493 | 3.560000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 100 | 0.460000 | 0.000230 | -0.000922 | 0.002039 | -0.003647 | 3.560000 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.004576 | 1.000000 | 0.000500 | -0.005076 | -0.013386 | 0.008810 | 0.008310 |
| 2021-02-04 | 2021-02-01 | -0.012957 | 0.000000 | 0.000000 | -0.012957 | -0.018752 | 0.005795 | 0.005795 |
| 2021-02-05 | 2021-02-01 | 0.006216 | 0.000000 | 0.000000 | 0.006216 | -0.016112 | 0.022328 | 0.022328 |
| 2021-02-08 | 2021-02-01 | 0.005775 | 0.000000 | 0.000000 | 0.005775 | 0.007470 | -0.001696 | -0.001696 |
| 2021-02-09 | 2021-02-01 | 0.008028 | 0.000000 | 0.000000 | 0.008028 | 0.021414 | -0.013386 | -0.013386 |
| 2021-02-10 | 2021-02-01 | 0.005843 | 0.000000 | 0.000000 | 0.005843 | 0.008609 | -0.002765 | -0.002765 |
| 2021-02-18 | 2021-02-01 | 0.020038 | 0.000000 | 0.000000 | 0.020038 | 0.026714 | -0.006676 | -0.006676 |
| 2021-02-19 | 2021-02-01 | 0.023058 | 0.000000 | 0.000000 | 0.023058 | 0.025629 | -0.002571 | -0.002571 |
| 2021-02-22 | 2021-02-01 | 0.012246 | 0.000000 | 0.000000 | 0.012246 | 0.005639 | 0.006606 | 0.006606 |
| 2021-02-23 | 2021-02-01 | -0.002499 | 0.000000 | 0.000000 | -0.002499 | -0.006207 | 0.003708 | 0.003708 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
