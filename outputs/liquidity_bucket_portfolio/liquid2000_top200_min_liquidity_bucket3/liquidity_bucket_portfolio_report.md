# Liquidity Bucket Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-1,amplitude_20:-1`
- Selection mode: `min_liquidity`
- TopK: `200`
- Liquidity buckets: `5`

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.014833` |
| net_annualized_return | `-0.034382` |
| universe_annualized_return | `-0.006336` |
| gross_annualized_excess | `-0.020363` |
| net_annualized_excess | `-0.039804` |
| gross_excess_ir | `-0.208904` |
| net_excess_ir | `-0.452260` |
| net_max_drawdown | `-0.433789` |
| average_turnover | `0.159046` |
| average_daily_cost | `0.000080` |
| topk | `200` |
| liquidity_buckets | `5` |
| selection_mode | `min_liquidity` |
| min_liquidity_bucket | `3` |
| cost_bps | `5.000000` |
| min_count | `100` |
| average_liquidity_bucket | `3.837250` |
| average_amount_mean_20 | `243108.912290` |

## Exposure Summary

| trading_days | holding_count | mean_score | mean_rev_5 | mean_std_20 | mean_amplitude_20 | mean_ret_20 | mean_amount_mean_20 | mean_volume_ratio_5_20 | mean_liquidity_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 849 | 200.000000 | 2.386394 | 0.018636 | 0.015225 | 0.022859 | -0.028094 | 243108.912290 | 0.975089 | 3.837250 |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return | average_liquidity_bucket | average_amount_mean_20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.006800 | 1.000000 | 0.000500 | 0.006300 | 0.008637 | -0.001837 | -0.002337 | 4.120000 | 212157.367109 |
| 2017-02-08 | 200 | 0.006030 | 0.140000 | 0.000070 | 0.005960 | -0.000653 | 0.006683 | 0.006613 | 4.145000 | 211489.018053 |
| 2017-02-09 | 200 | 0.006715 | 0.110000 | 0.000055 | 0.006660 | 0.006801 | -0.000086 | -0.000141 | 4.170000 | 214891.591461 |
| 2017-02-10 | 200 | -0.001022 | 0.130000 | 0.000065 | -0.001087 | -0.000391 | -0.000630 | -0.000695 | 4.120000 | 203947.201188 |
| 2017-02-13 | 200 | -0.004247 | 0.100000 | 0.000050 | -0.004297 | -0.010148 | 0.005901 | 0.005851 | 4.150000 | 210251.488511 |
| 2017-02-14 | 200 | 0.005721 | 0.115000 | 0.000057 | 0.005664 | 0.007367 | -0.001646 | -0.001703 | 4.115000 | 208731.921761 |
| 2017-02-15 | 200 | -0.005917 | 0.155000 | 0.000078 | -0.005994 | -0.009198 | 0.003281 | 0.003204 | 4.130000 | 219648.953849 |
| 2017-02-16 | 200 | 0.012986 | 0.135000 | 0.000068 | 0.012919 | 0.010478 | 0.002508 | 0.002441 | 4.090000 | 221470.288769 |
| 2017-02-17 | 200 | 0.006612 | 0.160000 | 0.000080 | 0.006532 | 0.009666 | -0.003053 | -0.003133 | 4.100000 | 240427.399302 |
| 2017-02-20 | 200 | 0.003716 | 0.315000 | 0.000157 | 0.003558 | 0.004752 | -0.001037 | -0.001194 | 3.825000 | 175386.315570 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holding_exposure_summary.csv`
- `holdings.csv`
