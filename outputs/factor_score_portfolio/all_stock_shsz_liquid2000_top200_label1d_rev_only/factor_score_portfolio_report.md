# Factor Score Portfolio Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Score weights: `rev_5:1`
- TopK: `200`
- Cost: `5.0` bps per one-way turnover

## Summary

| metric | value |
| --- | ---: |
| start_date | `2017-01-10` |
| end_date | `2020-07-29` |
| trading_days | `864` |
| gross_annualized_return | `-0.116984` |
| net_annualized_return | `-0.162594` |
| universe_annualized_return | `-0.020661` |
| gross_annualized_excess | `-0.093463` |
| net_annualized_excess | `-0.140270` |
| gross_excess_ir | `-1.193498` |
| net_excess_ir | `-1.859341` |
| net_max_drawdown | `-0.569184` |
| average_turnover | `0.420521` |
| average_daily_cost | `0.000210` |
| topk | `200` |
| cost_bps | `5.000000` |
| score_weights | `rev_5:1` |
| score_clip | `3.000000` |
| min_count | `100` |

## First Daily Rows

| datetime | holding_count | gross_return | turnover | cost | net_return | universe_return | excess_return | net_excess_return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017-01-10 | 200 | -0.007736 | 1.000000 | 0.000500 | -0.008236 | -0.009228 | 0.001493 | 0.000993 |
| 2017-01-11 | 200 | -0.024350 | 0.335000 | 0.000167 | -0.024517 | -0.016946 | -0.007404 | -0.007571 |
| 2017-01-12 | 200 | -0.051844 | 0.375000 | 0.000188 | -0.052032 | -0.039001 | -0.012843 | -0.013031 |
| 2017-01-13 | 200 | 0.022400 | 0.460000 | 0.000230 | 0.022170 | 0.011411 | 0.010988 | 0.010758 |
| 2017-01-16 | 200 | -0.010140 | 0.385000 | 0.000193 | -0.010333 | -0.003364 | -0.006776 | -0.006968 |
| 2017-01-17 | 200 | -0.003936 | 0.350000 | 0.000175 | -0.004111 | -0.004064 | 0.000129 | -0.000046 |
| 2017-01-18 | 200 | 0.021757 | 0.335000 | 0.000167 | 0.021590 | 0.016268 | 0.005490 | 0.005322 |
| 2017-01-19 | 200 | 0.013681 | 0.300000 | 0.000150 | 0.013531 | 0.010149 | 0.003532 | 0.003382 |
| 2017-01-20 | 200 | -0.004786 | 0.395000 | 0.000198 | -0.004984 | -0.003251 | -0.001535 | -0.001732 |
| 2017-01-23 | 200 | 0.004046 | 0.660000 | 0.000330 | 0.003716 | 0.003429 | 0.000617 | 0.000287 |

## Output Files

- `daily_returns.csv`
- `summary.csv`
- `holdings.csv`
