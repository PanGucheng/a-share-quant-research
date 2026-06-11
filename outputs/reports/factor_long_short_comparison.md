# Factor Long-Short Comparison

Scope:

```text
label: label_1d_t1
quantile: top 20% long, bottom 20% short
cost: 5 bps per one-way turnover
```

## Results

| market | signal | net_annualized_return | net_ir | net_max_drawdown | average_long_return | average_short_return | average_spread | average_turnover | average_daily_cost | trading_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_stock_shsz_liquid2000 | std_20 | 0.140036 | 0.923612 | -0.184322 | 0.000088 | -0.000518 | 0.000605 | 0.075718 | 0.000038 | 849 |
| all_stock_shsz_liquid2000 | amplitude_20 | 0.143531 | 0.912179 | -0.187354 | 0.000124 | -0.000487 | 0.000611 | 0.054724 | 0.000027 | 850 |
| all_stock_shsz_liquid2000 | score | 0.125890 | 0.859777 | -0.208359 | -0.000131 | -0.000725 | 0.000594 | 0.156382 | 0.000078 | 869 |
| all_stock_shsz_liquid2000 | rev_5 | 0.094322 | 0.763515 | -0.144426 | -0.000066 | -0.000629 | 0.000563 | 0.344575 | 0.000172 | 864 |
| csi500 | rev_5 | -0.037973 | -0.192695 | -0.362543 | 0.000015 | -0.000049 | 0.000063 | 0.349362 | 0.000175 | 864 |
| csi500 | amplitude_20 | -0.061095 | -0.257972 | -0.279331 | -0.000091 | 0.000067 | -0.000158 | 0.054087 | 0.000027 | 850 |
| csi500 | std_20 | -0.068731 | -0.327743 | -0.283350 | -0.000045 | 0.000140 | -0.000185 | 0.078192 | 0.000039 | 849 |
| csi500 | score | -0.090962 | -0.473142 | -0.354192 | -0.000203 | 0.000037 | -0.000240 | 0.160979 | 0.000080 | 869 |

## Interpretation

- Long-short diagnostics are positive while the earlier long-only TopK portfolios are negative.
- This means the factor ranking has signal, but naive long-only construction is absorbing unfavorable exposure.
- Low volatility and low amplitude are the most stable signals in this pass.
- The next step should inspect long-leg and short-leg exposures, then design a long-only portfolio with benchmark or risk controls.
