# Low Frequency Tradability Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- Rebalance every: `10` trading days
- TopK: `300`
- Cost: `20.0` bps per one-way turnover
- Score weights: `std_20:-1,amplitude_20:-1,rev_5:0.25`

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
| gross_annualized_return | `0.039819` |
| net_annualized_return | `0.020361` |
| universe_annualized_return | `0.003471` |
| gross_annualized_excess | `0.026909` |
| net_annualized_excess | `0.007705` |
| gross_excess_ir | `0.359576` |
| net_excess_ir | `0.133548` |
| net_max_drawdown | `-0.258093` |
| average_turnover | `0.374571` |
| max_turnover | `1.000000` |
| average_eligible_count | `1124.685714` |
| average_selected_count | `300.000000` |
| label | `label_10d_t1` |
| topk | `300` |
| rebalance_every | `10` |
| cost_bps | `20.000000` |
| min_liquidity_bucket | `3` |
| min_tradability_score | `75.000000` |
| min_capacity_multiple | `2.000000` |
| window_start | `2021-01-01` |
| window_end | `2023-12-29` |
| weight_preset | `low_risk_rev` |
| score_weights | `std_20:-1,amplitude_20:-1,rev_5:0.25` |

## First Rebalances

| signal_date | execution_date | period_end_date | status | eligible_count | selected_count | turnover | cost | period_net_return | period_universe_return | period_net_excess_return | avg_selected_liquidity_bucket | avg_selected_tradability_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-01 | 2021-02-02 | 2021-02-23 | executed | 1117 | 300 | 1.000000 | 0.002000 | 0.055102 | 0.040415 | 0.013724 | 3.750000 | 100.000000 |
| 2021-02-22 | 2021-02-23 | 2021-03-09 | executed | 1117 | 300 | 0.390000 | 0.000780 | -0.005908 | -0.042360 | 0.037065 | 3.723333 | 100.000000 |
| 2021-03-08 | 2021-03-09 | 2021-03-23 | executed | 1122 | 300 | 0.353333 | 0.000707 | 0.016954 | 0.023996 | -0.007191 | 3.680000 | 100.000000 |
| 2021-03-22 | 2021-03-23 | 2021-04-07 | executed | 1136 | 300 | 0.380000 | 0.000760 | 0.009190 | 0.019674 | -0.010563 | 3.580000 | 100.000000 |
| 2021-04-06 | 2021-04-07 | 2021-04-21 | executed | 1128 | 300 | 0.363333 | 0.000727 | 0.001789 | 0.004745 | -0.003178 | 3.713333 | 100.000000 |
| 2021-04-20 | 2021-04-21 | 2021-05-10 | executed | 1142 | 300 | 0.356667 | 0.000713 | -0.026726 | -0.004462 | -0.022482 | 3.680000 | 100.000000 |
| 2021-05-07 | 2021-05-10 | 2021-05-24 | executed | 1119 | 300 | 0.370000 | 0.000740 | 0.022555 | 0.021835 | 0.000611 | 3.713333 | 100.000000 |
| 2021-05-21 | 2021-05-24 | 2021-06-07 | executed | 1113 | 300 | 0.370000 | 0.000740 | 0.017184 | 0.037367 | -0.019693 | 3.666667 | 100.000000 |
| 2021-06-04 | 2021-06-07 | 2021-06-22 | executed | 1123 | 300 | 0.366667 | 0.000733 | -0.003940 | 0.005246 | -0.009487 | 3.670000 | 100.000000 |
| 2021-06-21 | 2021-06-22 | 2021-07-06 | executed | 1133 | 300 | 0.393333 | 0.000787 | -0.003604 | 0.002039 | -0.006119 | 3.673333 | 100.000000 |

## First Daily Rows

| datetime | signal_date | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-02-03 | 2021-02-01 | -0.011549 | 1.000000 | 0.002000 | -0.013549 | -0.013386 | 0.001837 | -0.000163 |
| 2021-02-04 | 2021-02-01 | -0.016761 | 0.000000 | 0.000000 | -0.016761 | -0.018752 | 0.001991 | 0.001991 |
| 2021-02-05 | 2021-02-01 | -0.004768 | 0.000000 | 0.000000 | -0.004768 | -0.016112 | 0.011344 | 0.011344 |
| 2021-02-08 | 2021-02-01 | 0.007552 | 0.000000 | 0.000000 | 0.007552 | 0.007470 | 0.000082 | 0.000082 |
| 2021-02-09 | 2021-02-01 | 0.014847 | 0.000000 | 0.000000 | 0.014847 | 0.021414 | -0.006567 | -0.006567 |
| 2021-02-10 | 2021-02-01 | 0.008453 | 0.000000 | 0.000000 | 0.008453 | 0.008609 | -0.000156 | -0.000156 |
| 2021-02-18 | 2021-02-01 | 0.024325 | 0.000000 | 0.000000 | 0.024325 | 0.026714 | -0.002389 | -0.002389 |
| 2021-02-19 | 2021-02-01 | 0.026907 | 0.000000 | 0.000000 | 0.026907 | 0.025629 | 0.001278 | 0.001278 |
| 2021-02-22 | 2021-02-01 | 0.010157 | 0.000000 | 0.000000 | 0.010157 | 0.005639 | 0.004518 | 0.004518 |
| 2021-02-23 | 2021-02-01 | -0.002405 | 0.000000 | 0.000000 | -0.002405 | -0.006207 | 0.003802 | 0.003802 |

## Output Files

- `daily_returns.csv`
- `rebalance_summary.csv`
- `summary.csv`
- `positions.csv`
