# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_10d_t1`
- IC rows: `8444`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.902177 | -0.038580 | -0.263079 | -0.073049 | 0.073049 | -0.452742 | 1568464 |
| std_20 | risk | negative | 0.900015 | -0.040630 | -0.288883 | -0.069266 | 0.069266 | -0.444184 | 1564705 |
| ret_20 | momentum | watch | 0.912413 | -0.044050 | -0.320755 | -0.055492 |  | -0.369746 | 1586260 |
| amount_std_20 | liquidity | watch | 0.902177 | -0.019491 | -0.202158 | -0.052199 |  | -0.369600 | 1568464 |
| ret_10 | momentum | watch | 0.926495 | -0.030690 | -0.245784 | -0.035874 |  | -0.259996 | 1610742 |
| amount_mean_20 | liquidity | watch | 0.902177 | -0.005842 | -0.059850 | -0.031122 |  | -0.208566 | 1568464 |
| corr_ret_volume_20 | price_volume | watch | 0.900015 | -0.015353 | -0.197921 | -0.028245 |  | -0.311589 | 1564705 |
| volume_ratio_5_20 | liquidity | watch | 0.902177 | -0.029443 | -0.341983 | -0.022372 |  | -0.232927 | 1568464 |
| ret_5 | momentum | watch | 0.934759 | -0.019613 | -0.175834 | -0.020448 |  | -0.163526 | 1625109 |
| rev_5 | reversal | positive | 0.934759 | 0.019613 | 0.175834 | 0.020448 | 0.020448 | 0.163526 | 1625109 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.001969 |
| amount_mean_20 | 2 | 0.001400 |
| amount_mean_20 | 3 | 0.000364 |
| amount_mean_20 | 4 | 0.000311 |
| amount_mean_20 | 5 | -0.000934 |
| amount_std_20 | 1 | 0.002737 |
| amount_std_20 | 2 | 0.002144 |
| amount_std_20 | 3 | 0.001261 |
| amount_std_20 | 4 | 0.000086 |
| amount_std_20 | 5 | -0.003115 |
| amplitude_20 | 1 | 0.000856 |
| amplitude_20 | 2 | 0.002151 |
| amplitude_20 | 3 | 0.002740 |
| amplitude_20 | 4 | 0.001534 |
| amplitude_20 | 5 | -0.004164 |
| corr_ret_volume_20 | 1 | 0.001510 |
| corr_ret_volume_20 | 2 | 0.001180 |
| corr_ret_volume_20 | 3 | 0.000764 |
| corr_ret_volume_20 | 4 | 0.000245 |
| corr_ret_volume_20 | 5 | -0.000738 |
| ret_10 | 1 | 0.000464 |
| ret_10 | 2 | 0.002405 |
| ret_10 | 3 | 0.002464 |
| ret_10 | 4 | 0.001914 |
| ret_10 | 5 | -0.003086 |
| ret_20 | 1 | 0.001915 |
| ret_20 | 2 | 0.002342 |
| ret_20 | 3 | 0.001901 |
| ret_20 | 4 | 0.000976 |
| ret_20 | 5 | -0.004723 |
| ret_5 | 1 | -0.000460 |
| ret_5 | 2 | 0.002157 |
| ret_5 | 3 | 0.002334 |
| ret_5 | 4 | 0.002224 |
| ret_5 | 5 | -0.002251 |
| rev_5 | 1 | -0.002245 |
| rev_5 | 2 | 0.002223 |
| rev_5 | 3 | 0.002327 |
| rev_5 | 4 | 0.002162 |
| rev_5 | 5 | -0.000461 |
| std_20 | 1 | 0.000234 |
| std_20 | 2 | 0.002218 |
| std_20 | 3 | 0.002864 |
| std_20 | 4 | 0.002271 |
| std_20 | 5 | -0.004620 |
| volume_ratio_5_20 | 1 | -0.000649 |
| volume_ratio_5_20 | 2 | 0.002095 |
| volume_ratio_5_20 | 3 | 0.002656 |
| volume_ratio_5_20 | 4 | 0.001926 |
| volume_ratio_5_20 | 5 | -0.002913 |

## Average Top-Quantile Turnover

| factor | turnover |
| --- | --- |
| amount_mean_20 | 0.019695 |
| amount_std_20 | 0.038180 |
| amplitude_20 | 0.055860 |
| corr_ret_volume_20 | 0.178548 |
| ret_10 | 0.228238 |
| ret_20 | 0.161842 |
| ret_5 | 0.325443 |
| rev_5 | 0.362150 |
| std_20 | 0.070590 |
| volume_ratio_5_20 | 0.191332 |

## Output Files

- `factor_summary.csv`
- `ic_series.csv`
- `group_return.csv`
- `turnover.csv`
- `correlation.csv`
