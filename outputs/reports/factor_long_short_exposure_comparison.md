# Factor Long-Short Exposure Comparison

Positive spread means the long leg has a higher average value than the short leg.

## Exposure Spreads

| market | signal | spread_mean_label | spread_mean_score | spread_mean_rev_5 | spread_mean_std_20 | spread_mean_amplitude_20 | spread_mean_ret_20 | spread_mean_amount_mean_20 | spread_mean_volume_ratio_5_20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_stock_shsz_liquid2000 | amplitude_20 | 0.000611 | 5.143877 | 0.007057 | -0.022265 | -0.030678 | -0.067902 | -251199.878340 | -0.005532 |
| all_stock_shsz_liquid2000 | rev_5 | 0.000563 | 2.424723 | 0.127737 | 0.000103 | 0.000358 | -0.114712 | -44156.246853 | -0.333234 |
| all_stock_shsz_liquid2000 | score | 0.000594 | 5.635906 | 0.056737 | -0.022215 | -0.027311 | -0.105161 | -273503.417232 | -0.148294 |
| all_stock_shsz_liquid2000 | std_20 | 0.000605 | 5.193724 | 0.010074 | -0.024905 | -0.027473 | -0.061912 | -288662.777425 | -0.061316 |
| csi500 | amplitude_20 | -0.000158 | 5.141766 | 0.009559 | -0.021031 | -0.029546 | -0.073022 | -380155.347057 | -0.007495 |
| csi500 | rev_5 | 0.000063 | 2.567226 | 0.120296 | -0.000366 | -0.000323 | -0.113557 | 3804.835620 | -0.291433 |
| csi500 | score | -0.000240 | 5.621606 | 0.055475 | -0.021003 | -0.026194 | -0.105096 | -343080.982733 | -0.129022 |
| csi500 | std_20 | -0.000185 | 5.164847 | 0.010800 | -0.023781 | -0.026560 | -0.062839 | -364294.020062 | -0.051162 |

## Interpretation

- `spread_mean_label` is the realized long-minus-short label spread and should align with the long-short return report.
- Large `spread_mean_std_20` or `spread_mean_amplitude_20` gaps show whether the signal is mostly a risk sort.
- Large liquidity gaps mean a long-only version may need liquidity buckets before selecting names.
