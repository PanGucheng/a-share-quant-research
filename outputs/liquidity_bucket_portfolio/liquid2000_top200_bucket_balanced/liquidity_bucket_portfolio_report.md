# Liquidity Bucket Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-1,amplitude_20:-1`
- Selection mode: `bucket_balanced`
- TopK: `200`
- Liquidity buckets: `5`

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.032530` |
| net_annualized_return | `-0.055316` |
| universe_annualized_return | `-0.006336` |
| gross_annualized_excess | `-0.040816` |
| net_annualized_excess | `-0.063406` |
| gross_excess_ir | `-0.432242` |
| net_excess_ir | `-0.704341` |
| net_max_drawdown | `-0.439095` |
| average_turnover | `0.189105` |
| average_daily_cost | `0.000095` |
| topk | `200` |
| liquidity_buckets | `5` |
| selection_mode | `bucket_balanced` |
| min_liquidity_bucket | `3` |
| cost_bps | `5.000000` |
| min_count | `100` |
| average_liquidity_bucket | `3.000000` |
| average_amount_mean_20 | `181310.994094` |

## Exposure Summary

| trading_days | holding_count | mean_score | mean_rev_5 | mean_std_20 | mean_amplitude_20 | mean_ret_20 | mean_amount_mean_20 | mean_volume_ratio_5_20 | mean_liquidity_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 849 | 200.000000 | 2.825984 | 0.018639 | 0.013276 | 0.020321 | -0.030001 | 181310.994094 | 0.992266 | 3.000000 |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return | average_liquidity_bucket | average_amount_mean_20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.005600 | 1.000000 | 0.000500 | 0.005100 | 0.008637 | -0.003037 | -0.003537 | 3.000000 | 134595.368498 |
| 2017-02-08 | 200 | 0.003991 | 0.165000 | 0.000083 | 0.003909 | -0.000653 | 0.004644 | 0.004562 | 3.000000 | 137291.598793 |
| 2017-02-09 | 200 | 0.006928 | 0.150000 | 0.000075 | 0.006853 | 0.006801 | 0.000127 | 0.000052 | 3.000000 | 132036.886585 |
| 2017-02-10 | 200 | -0.001538 | 0.175000 | 0.000088 | -0.001625 | -0.000391 | -0.001146 | -0.001234 | 3.000000 | 135104.787661 |
| 2017-02-13 | 200 | -0.003921 | 0.170000 | 0.000085 | -0.004006 | -0.010148 | 0.006226 | 0.006141 | 3.000000 | 135994.565427 |
| 2017-02-14 | 200 | 0.004275 | 0.155000 | 0.000078 | 0.004198 | 0.007367 | -0.003092 | -0.003169 | 3.000000 | 136866.169148 |
| 2017-02-15 | 200 | -0.005139 | 0.180000 | 0.000090 | -0.005229 | -0.009198 | 0.004058 | 0.003968 | 3.000000 | 141351.414485 |
| 2017-02-16 | 200 | 0.011100 | 0.185000 | 0.000093 | 0.011008 | 0.010478 | 0.000622 | 0.000530 | 3.000000 | 149506.317079 |
| 2017-02-17 | 200 | 0.006924 | 0.195000 | 0.000097 | 0.006826 | 0.009666 | -0.002742 | -0.002839 | 3.000000 | 147232.484877 |
| 2017-02-20 | 200 | 0.002596 | 0.290000 | 0.000145 | 0.002451 | 0.004752 | -0.002156 | -0.002301 | 3.000000 | 140595.121979 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holding_exposure_summary.csv`
- `holdings.csv`
