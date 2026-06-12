# Liquidity Bucket Portfolio Comparison

Scope:

```text
market: all_stock_shsz_liquid2000
label: label_1d_t1
topk: 200
cost: 5 bps per one-way turnover
score: rev_5:1,std_20:-1,amplitude_20:-1
```

## Results

| name | selection_mode | topk | average_liquidity_bucket | average_amount_mean_20 | net_annualized_return | universe_annualized_return | net_annualized_excess | net_excess_ir | net_max_drawdown | average_turnover | average_daily_cost | trading_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| liquid2000_top200_min_liquidity_bucket3 | min_liquidity | 200 | 3.837250 | 243108.912290 | -0.034382 | -0.006336 | -0.039804 | -0.452260 | -0.433789 | 0.159046 | 0.000080 | 849 |
| liquid2000_top200_bucket_balanced | bucket_balanced | 200 | 3.000000 | 181310.994094 | -0.055316 | -0.006336 | -0.063406 | -0.704341 | -0.439095 | 0.189105 | 0.000095 | 849 |
| liquid2000_top200_plain_topk | plain_topk | 200 | 2.509882 | 129574.016047 | -0.060282 | -0.006336 | -0.067818 | -0.784255 | -0.463263 | 0.187962 | 0.000094 | 849 |

## Interpretation

- Liquidity constraints improve the naive long-only score portfolio, but do not make it profitable yet.
- Excluding the lowest two liquidity buckets is better than forcing equal picks across all liquidity buckets.
- This confirms liquidity exposure is part of the problem, but the next long-only version also needs risk or benchmark-relative controls.
