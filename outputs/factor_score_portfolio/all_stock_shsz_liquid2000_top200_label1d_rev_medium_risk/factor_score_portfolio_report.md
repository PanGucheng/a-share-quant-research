# Factor Score Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-0.5,amplitude_20:-0.5`
- TopK: `200`
- Cost: `5.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.037524` |
| net_annualized_return | `-0.076632` |
| universe_annualized_return | `-0.006336` |
| gross_annualized_excess | `-0.040471` |
| net_annualized_excess | `-0.079457` |
| gross_excess_ir | `-0.513598` |
| net_excess_ir | `-1.066563` |
| net_max_drawdown | `-0.512528` |
| average_turnover | `0.329117` |
| average_daily_cost | `0.000165` |
| topk | `200` |
| cost_bps | `5.000000` |
| score_weights | `rev_5:1,std_20:-0.5,amplitude_20:-0.5` |
| score_clip | `3.000000` |
| min_count | `100` |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.007098 | 1.000000 | 0.000500 | 0.006598 | 0.008637 | -0.001539 | -0.002039 |
| 2017-02-08 | 200 | 0.005795 | 0.250000 | 0.000125 | 0.005670 | -0.000653 | 0.006448 | 0.006323 |
| 2017-02-09 | 200 | 0.007067 | 0.210000 | 0.000105 | 0.006962 | 0.006801 | 0.000266 | 0.000161 |
| 2017-02-10 | 200 | -0.001395 | 0.245000 | 0.000122 | -0.001518 | -0.000391 | -0.001004 | -0.001126 |
| 2017-02-13 | 200 | -0.004593 | 0.260000 | 0.000130 | -0.004723 | -0.010148 | 0.005555 | 0.005425 |
| 2017-02-14 | 200 | 0.003999 | 0.255000 | 0.000128 | 0.003872 | 0.007367 | -0.003368 | -0.003495 |
| 2017-02-15 | 200 | -0.003100 | 0.310000 | 0.000155 | -0.003255 | -0.009198 | 0.006098 | 0.005943 |
| 2017-02-16 | 200 | 0.010576 | 0.305000 | 0.000153 | 0.010423 | 0.010478 | 0.000098 | -0.000054 |
| 2017-02-17 | 200 | 0.009398 | 0.345000 | 0.000172 | 0.009225 | 0.009666 | -0.000268 | -0.000440 |
| 2017-02-20 | 200 | 0.004274 | 0.420000 | 0.000210 | 0.004064 | 0.004752 | -0.000479 | -0.000689 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holdings.csv`
