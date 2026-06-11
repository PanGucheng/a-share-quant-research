# Factor Score Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `std_20:-1,amplitude_20:-1`
- TopK: `200`
- Cost: `5.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.018493` |
| net_annualized_return | `-0.027294` |
| universe_annualized_return | `-0.006336` |
| gross_annualized_excess | `-0.029141` |
| net_annualized_excess | `-0.037848` |
| gross_excess_ir | `-0.266724` |
| net_excess_ir | `-0.362253` |
| net_max_drawdown | `-0.402196` |
| average_turnover | `0.071484` |
| average_daily_cost | `0.000036` |
| topk | `200` |
| cost_bps | `5.000000` |
| score_weights | `std_20:-1,amplitude_20:-1` |
| score_clip | `3.000000` |
| min_count | `100` |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.004598 | 1.000000 | 0.000500 | 0.004098 | 0.008637 | -0.004039 | -0.004539 |
| 2017-02-08 | 200 | 0.003611 | 0.050000 | 0.000025 | 0.003586 | -0.000653 | 0.004264 | 0.004239 |
| 2017-02-09 | 200 | 0.006794 | 0.055000 | 0.000028 | 0.006766 | 0.006801 | -0.000007 | -0.000034 |
| 2017-02-10 | 200 | -0.000968 | 0.055000 | 0.000028 | -0.000996 | -0.000391 | -0.000577 | -0.000604 |
| 2017-02-13 | 200 | -0.003824 | 0.065000 | 0.000032 | -0.003857 | -0.010148 | 0.006324 | 0.006291 |
| 2017-02-14 | 200 | 0.006177 | 0.055000 | 0.000028 | 0.006150 | 0.007367 | -0.001190 | -0.001217 |
| 2017-02-15 | 200 | -0.006721 | 0.040000 | 0.000020 | -0.006741 | -0.009198 | 0.002477 | 0.002457 |
| 2017-02-16 | 200 | 0.014039 | 0.070000 | 0.000035 | 0.014004 | 0.010478 | 0.003561 | 0.003526 |
| 2017-02-17 | 200 | 0.005839 | 0.060000 | 0.000030 | 0.005809 | 0.009666 | -0.003826 | -0.003856 |
| 2017-02-20 | 200 | 0.002867 | 0.240000 | 0.000120 | 0.002747 | 0.004752 | -0.001885 | -0.002005 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holdings.csv`
