# Factor Score Portfolio Scan

Scope:

```text
label: label_1d_t1
cost: 5 bps per one-way turnover
score normalization: daily cross-sectional 1%/99% winsorized z-score, clipped to +/-3
```

## Results

| name | topk | score_weights | net_ann_return | universe_ann_return | net_ann_excess | net_excess_ir | net_max_drawdown | avg_turnover | avg_daily_cost | trading_days |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all_stock_shsz_liquid2000_top200_label1d_low_risk_only | 200 | `std_20:-1,amplitude_20:-1` | -0.027294 | -0.006336 | -0.037848 | -0.362253 | -0.402196 | 0.071484 | 0.000036 | 849 |
| all_stock_shsz_liquid2000_top200_label1d | 200 | `rev_5:1,std_20:-1,amplitude_20:-1` | -0.060282 | -0.006336 | -0.067818 | -0.784255 | -0.463263 | 0.187962 | 0.000094 | 849 |
| all_stock_shsz_liquid2000_top200_label1d_rev_medium_risk | 200 | `rev_5:1,std_20:-0.5,amplitude_20:-0.5` | -0.076632 | -0.006336 | -0.079457 | -1.066563 | -0.512528 | 0.329117 | 0.000165 | 849 |
| all_stock_shsz_liquid2000_top200_label1d_rev_light_risk | 200 | `rev_5:1,std_20:-0.25,amplitude_20:-0.25` | -0.095817 | -0.006336 | -0.092331 | -1.336069 | -0.526926 | 0.437792 | 0.000219 | 849 |
| csi500_top50_label1d | 50 | `rev_5:1,std_20:-1,amplitude_20:-1` | -0.094056 | 0.015649 | -0.118672 | -1.518602 | -0.482820 | 0.198092 | 0.000099 | 849 |
| all_stock_shsz_liquid2000_top200_label1d_rev_only | 200 | `rev_5:1` | -0.162594 | -0.020661 | -0.140270 | -1.859341 | -0.569184 | 0.420521 | 0.000210 | 864 |

## Interpretation

- The naive score portfolios did not beat their universe benchmark in this first pass.
- `rev_5` has positive one-day Rank IC, but direct TopK selection creates high turnover and weak realized portfolio performance.
- The low-risk-only variant is less poor, but still not enough to be treated as a usable strategy.
- The next iteration should add neutralization/exposure checks and compare quantile long-short behavior before promoting any factor score to a Qlib strategy.
