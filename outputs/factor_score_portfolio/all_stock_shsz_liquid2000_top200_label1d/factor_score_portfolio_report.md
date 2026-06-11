# Factor Score Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-1,amplitude_20:-1`
- TopK: `200`
- Cost: `5.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.037755` |
| net_annualized_return | `-0.060282` |
| universe_annualized_return | `-0.006336` |
| gross_annualized_excess | `-0.045471` |
| net_annualized_excess | `-0.067818` |
| gross_excess_ir | `-0.505512` |
| net_excess_ir | `-0.784255` |
| net_max_drawdown | `-0.463263` |
| average_turnover | `0.187962` |
| average_daily_cost | `0.000094` |
| topk | `200` |
| cost_bps | `5.000000` |
| score_weights | `rev_5:1,std_20:-1,amplitude_20:-1` |
| score_clip | `3.000000` |
| min_count | `100` |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.005387 | 1.000000 | 0.000500 | 0.004887 | 0.008637 | -0.003250 | -0.003750 |
| 2017-02-08 | 200 | 0.005322 | 0.150000 | 0.000075 | 0.005247 | -0.000653 | 0.005975 | 0.005900 |
| 2017-02-09 | 200 | 0.006816 | 0.165000 | 0.000083 | 0.006734 | 0.006801 | 0.000015 | -0.000067 |
| 2017-02-10 | 200 | -0.001716 | 0.185000 | 0.000093 | -0.001808 | -0.000391 | -0.001324 | -0.001417 |
| 2017-02-13 | 200 | -0.003777 | 0.155000 | 0.000078 | -0.003854 | -0.010148 | 0.006371 | 0.006293 |
| 2017-02-14 | 200 | 0.004606 | 0.160000 | 0.000080 | 0.004526 | 0.007367 | -0.002761 | -0.002841 |
| 2017-02-15 | 200 | -0.005206 | 0.150000 | 0.000075 | -0.005281 | -0.009198 | 0.003992 | 0.003917 |
| 2017-02-16 | 200 | 0.011329 | 0.160000 | 0.000080 | 0.011249 | 0.010478 | 0.000851 | 0.000771 |
| 2017-02-17 | 200 | 0.006270 | 0.170000 | 0.000085 | 0.006185 | 0.009666 | -0.003396 | -0.003481 |
| 2017-02-20 | 200 | 0.002776 | 0.335000 | 0.000167 | 0.002608 | 0.004752 | -0.001977 | -0.002144 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holdings.csv`
