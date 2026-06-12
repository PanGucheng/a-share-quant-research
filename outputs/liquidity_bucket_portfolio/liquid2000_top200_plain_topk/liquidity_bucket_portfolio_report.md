# Liquidity Bucket Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-1,amplitude_20:-1`
- Selection mode: `plain_topk`
- TopK: `200`
- Liquidity buckets: `5`

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
| liquidity_buckets | `5` |
| selection_mode | `plain_topk` |
| min_liquidity_bucket | `3` |
| cost_bps | `5.000000` |
| min_count | `100` |
| average_liquidity_bucket | `2.509882` |
| average_amount_mean_20 | `129574.016047` |

## Exposure Summary

| trading_days | holding_count | mean_score | mean_rev_5 | mean_std_20 | mean_amplitude_20 | mean_ret_20 | mean_amount_mean_20 | mean_volume_ratio_5_20 | mean_liquidity_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 849 | 200.000000 | 2.904811 | 0.018676 | 0.012883 | 0.019923 | -0.031074 | 129574.016047 | 0.995014 | 2.509882 |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return | average_liquidity_bucket | average_amount_mean_20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.005387 | 1.000000 | 0.000500 | 0.004887 | 0.008637 | -0.003250 | -0.003750 | 3.490000 | 171340.954701 |
| 2017-02-08 | 200 | 0.005322 | 0.150000 | 0.000075 | 0.005247 | -0.000653 | 0.005975 | 0.005900 | 3.500000 | 182986.362389 |
| 2017-02-09 | 200 | 0.006816 | 0.165000 | 0.000083 | 0.006734 | 0.006801 | 0.000015 | -0.000067 | 3.405000 | 175641.385528 |
| 2017-02-10 | 200 | -0.001716 | 0.185000 | 0.000093 | -0.001808 | -0.000391 | -0.001324 | -0.001417 | 3.325000 | 162837.729132 |
| 2017-02-13 | 200 | -0.003777 | 0.155000 | 0.000078 | -0.003854 | -0.010148 | 0.006371 | 0.006293 | 3.235000 | 158821.879038 |
| 2017-02-14 | 200 | 0.004606 | 0.160000 | 0.000080 | 0.004526 | 0.007367 | -0.002761 | -0.002841 | 3.260000 | 159913.696979 |
| 2017-02-15 | 200 | -0.005206 | 0.150000 | 0.000075 | -0.005281 | -0.009198 | 0.003992 | 0.003917 | 3.250000 | 165497.564071 |
| 2017-02-16 | 200 | 0.011329 | 0.160000 | 0.000080 | 0.011249 | 0.010478 | 0.000851 | 0.000771 | 3.115000 | 159214.721894 |
| 2017-02-17 | 200 | 0.006270 | 0.170000 | 0.000085 | 0.006185 | 0.009666 | -0.003396 | -0.003481 | 3.245000 | 182435.231823 |
| 2017-02-20 | 200 | 0.002776 | 0.335000 | 0.000167 | 0.002608 | 0.004752 | -0.001977 | -0.002144 | 2.690000 | 123457.855267 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holding_exposure_summary.csv`
- `holdings.csv`
