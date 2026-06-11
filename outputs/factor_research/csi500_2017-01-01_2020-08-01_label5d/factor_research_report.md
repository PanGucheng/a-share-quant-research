# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `csi500`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_5d_t1`
- IC rows: `8494`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.902608 | -0.022080 | -0.147056 | -0.041860 |  | -0.269749 | 392952 |
| std_20 | risk | negative | 0.900017 | -0.009639 | -0.059393 | -0.035773 | 0.035773 | -0.205372 | 391824 |
| amplitude_20 | risk | negative | 0.902608 | -0.005321 | -0.029981 | -0.035476 | 0.035476 | -0.194681 | 392952 |
| ret_20 | momentum | watch | 0.909848 | -0.010098 | -0.064663 | -0.031727 |  | -0.195317 | 396104 |
| amount_mean_20 | liquidity | watch | 0.902608 | -0.010283 | -0.064700 | -0.027689 |  | -0.169213 | 392952 |
| corr_ret_volume_20 | price_volume | watch | 0.900017 | -0.001621 | -0.018011 | -0.017497 |  | -0.179059 | 391824 |
| ret_10 | momentum | watch | 0.930452 | 0.001785 | 0.011633 | -0.015404 |  | -0.099544 | 405074 |
| volume_ratio_5_20 | liquidity | watch | 0.902608 | -0.010807 | -0.091420 | -0.013121 |  | -0.114663 | 392952 |
| ret_5 | momentum | watch | 0.941861 | 0.002760 | 0.019281 | -0.008134 |  | -0.056280 | 410041 |
| rev_5 | reversal | positive | 0.941861 | -0.002760 | -0.019281 | 0.008134 | 0.008134 | 0.056280 | 410041 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.000497 |
| amount_mean_20 | 2 | 0.000711 |
| amount_mean_20 | 3 | 0.001407 |
| amount_mean_20 | 4 | 0.001205 |
| amount_mean_20 | 5 | -0.000063 |
| amount_std_20 | 1 | 0.000827 |
| amount_std_20 | 2 | 0.001154 |
| amount_std_20 | 3 | 0.001992 |
| amount_std_20 | 4 | 0.000569 |
| amount_std_20 | 5 | -0.000782 |
| amplitude_20 | 1 | -0.000546 |
| amplitude_20 | 2 | 0.000842 |
| amplitude_20 | 3 | 0.001294 |
| amplitude_20 | 4 | 0.002072 |
| amplitude_20 | 5 | 0.000100 |
| corr_ret_volume_20 | 1 | 0.000707 |
| corr_ret_volume_20 | 2 | 0.000709 |
| corr_ret_volume_20 | 3 | 0.000664 |
| corr_ret_volume_20 | 4 | 0.000977 |
| corr_ret_volume_20 | 5 | 0.000571 |
| ret_10 | 1 | 0.000324 |
| ret_10 | 2 | 0.001033 |
| ret_10 | 3 | 0.001207 |
| ret_10 | 4 | 0.001207 |
| ret_10 | 5 | 0.000680 |
| ret_20 | 1 | 0.001110 |
| ret_20 | 2 | 0.000822 |
| ret_20 | 3 | 0.000897 |
| ret_20 | 4 | 0.000672 |
| ret_20 | 5 | 0.000005 |
| ret_5 | 1 | 0.000483 |
| ret_5 | 2 | 0.000910 |
| ret_5 | 3 | 0.000726 |
| ret_5 | 4 | 0.001013 |
| ret_5 | 5 | 0.000807 |
| rev_5 | 1 | 0.000817 |
| rev_5 | 2 | 0.000994 |
| rev_5 | 3 | 0.000738 |
| rev_5 | 4 | 0.000922 |
| rev_5 | 5 | 0.000473 |
| std_20 | 1 | -0.000467 |
| std_20 | 2 | 0.000779 |
| std_20 | 3 | 0.001376 |
| std_20 | 4 | 0.001713 |
| std_20 | 5 | 0.000240 |
| volume_ratio_5_20 | 1 | -0.000171 |
| volume_ratio_5_20 | 2 | 0.000897 |
| volume_ratio_5_20 | 3 | 0.001397 |
| volume_ratio_5_20 | 4 | 0.001776 |
| volume_ratio_5_20 | 5 | -0.000140 |

## Average Top-Quantile Turnover

| factor | turnover |
| --- | --- |
| amount_mean_20 | 0.026085 |
| amount_std_20 | 0.046206 |
| amplitude_20 | 0.055034 |
| corr_ret_volume_20 | 0.181412 |
| ret_10 | 0.228274 |
| ret_20 | 0.161027 |
| ret_5 | 0.328429 |
| rev_5 | 0.367559 |
| std_20 | 0.075168 |
| volume_ratio_5_20 | 0.195718 |

## Output Files

- `factor_summary.csv`
- `ic_series.csv`
- `group_return.csv`
- `turnover.csv`
- `correlation.csv`
