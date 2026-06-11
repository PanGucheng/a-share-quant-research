# Factor Score Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `csi500`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1,std_20:-1,amplitude_20:-1`
- TopK: `50`
- Cost: `5.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-02-07` |
| end_date | `2020-07-29` |
| trading_days | `849` |
| gross_annualized_return | `-0.071150` |
| net_annualized_return | `-0.094056` |
| universe_annualized_return | `0.015649` |
| gross_annualized_excess | `-0.096387` |
| net_annualized_excess | `-0.118672` |
| gross_excess_ir | `-1.210441` |
| net_excess_ir | `-1.518602` |
| net_max_drawdown | `-0.482820` |
| average_turnover | `0.198092` |
| average_daily_cost | `0.000099` |
| topk | `50` |
| cost_bps | `5.000000` |
| score_weights | `rev_5:1,std_20:-1,amplitude_20:-1` |
| score_clip | `3.000000` |
| min_count | `100` |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-02-07 | 50 | 0.004724 | 1.000000 | 0.000500 | 0.004224 | 0.007905 | -0.003181 | -0.003681 |
| 2017-02-08 | 50 | 0.003552 | 0.220000 | 0.000110 | 0.003442 | 0.001769 | 0.001783 | 0.001673 |
| 2017-02-09 | 50 | 0.008075 | 0.220000 | 0.000110 | 0.007965 | 0.005870 | 0.002205 | 0.002095 |
| 2017-02-10 | 50 | -0.001780 | 0.240000 | 0.000120 | -0.001900 | 0.000741 | -0.002521 | -0.002641 |
| 2017-02-13 | 50 | -0.004855 | 0.160000 | 0.000080 | -0.004935 | -0.010567 | 0.005712 | 0.005632 |
| 2017-02-14 | 50 | 0.004760 | 0.160000 | 0.000080 | 0.004680 | 0.008037 | -0.003276 | -0.003356 |
| 2017-02-15 | 50 | -0.005549 | 0.180000 | 0.000090 | -0.005639 | -0.008433 | 0.002885 | 0.002795 |
| 2017-02-16 | 50 | 0.013381 | 0.140000 | 0.000070 | 0.013311 | 0.013717 | -0.000336 | -0.000406 |
| 2017-02-17 | 50 | 0.005453 | 0.240000 | 0.000120 | 0.005333 | 0.008462 | -0.003009 | -0.003129 |
| 2017-02-20 | 50 | 0.004114 | 0.440000 | 0.000220 | 0.003894 | 0.006710 | -0.002596 | -0.002816 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holdings.csv`
