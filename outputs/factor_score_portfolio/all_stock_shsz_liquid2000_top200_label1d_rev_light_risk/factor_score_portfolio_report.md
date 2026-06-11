# Factor Score Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-0.25,amplitude_20:-0.25`
- TopK: `200`
- Cost: `5.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.044512` |
| net_annualized_return | `-0.095817` |
| universe_annualized_return | `-0.006336` |
| gross_annualized_excess | `-0.040840` |
| net_annualized_excess | `-0.092331` |
| gross_excess_ir | `-0.555135` |
| net_excess_ir | `-1.336069` |
| net_max_drawdown | `-0.526926` |
| average_turnover | `0.437792` |
| average_daily_cost | `0.000219` |
| topk | `200` |
| cost_bps | `5.000000` |
| score_weights | `rev_5:1,std_20:-0.25,amplitude_20:-0.25` |
| score_clip | `3.000000` |
| min_count | `100` |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 200 | 0.007861 | 1.000000 | 0.000500 | 0.007361 | 0.008637 | -0.000776 | -0.001276 |
| 2017-02-08 | 200 | 0.005072 | 0.365000 | 0.000182 | 0.004890 | -0.000653 | 0.005725 | 0.005543 |
| 2017-02-09 | 200 | 0.006951 | 0.315000 | 0.000157 | 0.006793 | 0.006801 | 0.000150 | -0.000008 |
| 2017-02-10 | 200 | -0.001007 | 0.430000 | 0.000215 | -0.001222 | -0.000391 | -0.000615 | -0.000830 |
| 2017-02-13 | 200 | -0.005712 | 0.380000 | 0.000190 | -0.005902 | -0.010148 | 0.004436 | 0.004246 |
| 2017-02-14 | 200 | 0.003952 | 0.360000 | 0.000180 | 0.003772 | 0.007367 | -0.003415 | -0.003595 |
| 2017-02-15 | 200 | -0.002350 | 0.420000 | 0.000210 | -0.002560 | -0.009198 | 0.006848 | 0.006638 |
| 2017-02-16 | 200 | 0.006677 | 0.385000 | 0.000193 | 0.006484 | 0.010478 | -0.003801 | -0.003994 |
| 2017-02-17 | 200 | 0.012422 | 0.560000 | 0.000280 | 0.012142 | 0.009666 | 0.002756 | 0.002476 |
| 2017-02-20 | 200 | 0.004580 | 0.495000 | 0.000247 | 0.004333 | 0.004752 | -0.000172 | -0.000420 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holdings.csv`
