# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_5d_t1`
- IC rows: `8494`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.910211 | -0.026477 | -0.169682 | -0.061358 | 0.061358 | -0.357343 | 1582431 |
| std_20 | risk | negative | 0.908011 | -0.029040 | -0.194321 | -0.058561 | 0.058561 | -0.352706 | 1578607 |
| ret_20 | momentum | watch | 0.920542 | -0.036085 | -0.265326 | -0.049270 |  | -0.329992 | 1600392 |
| amount_std_20 | liquidity | watch | 0.910211 | -0.014897 | -0.160539 | -0.045518 |  | -0.335830 | 1582431 |
| ret_10 | momentum | watch | 0.934786 | -0.024030 | -0.187248 | -0.033263 |  | -0.233614 | 1625156 |
| ret_5 | momentum | watch | 0.943118 | -0.018682 | -0.158512 | -0.027843 |  | -0.213247 | 1639642 |
| rev_5 | reversal | positive | 0.943118 | 0.018682 | 0.158512 | 0.027843 | 0.027843 | 0.213247 | 1639642 |
| amount_mean_20 | liquidity | watch | 0.910211 | -0.004046 | -0.042998 | -0.027335 |  | -0.193026 | 1582431 |
| corr_ret_volume_20 | price_volume | watch | 0.908011 | -0.010606 | -0.138244 | -0.023853 |  | -0.262228 | 1578607 |
| volume_ratio_5_20 | liquidity | watch | 0.910211 | -0.023224 | -0.258469 | -0.019348 |  | -0.200253 | 1582431 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.001295 |
| amount_mean_20 | 2 | 0.000814 |
| amount_mean_20 | 3 | 0.000158 |
| amount_mean_20 | 4 | 0.000174 |
| amount_mean_20 | 5 | -0.000647 |
| amount_std_20 | 1 | 0.001718 |
| amount_std_20 | 2 | 0.001301 |
| amount_std_20 | 3 | 0.000630 |
| amount_std_20 | 4 | -0.000030 |
| amount_std_20 | 5 | -0.001827 |
| amplitude_20 | 1 | 0.000447 |
| amplitude_20 | 2 | 0.001253 |
| amplitude_20 | 3 | 0.001399 |
| amplitude_20 | 4 | 0.001021 |
| amplitude_20 | 5 | -0.002325 |
| corr_ret_volume_20 | 1 | 0.000728 |
| corr_ret_volume_20 | 2 | 0.000652 |
| corr_ret_volume_20 | 3 | 0.000568 |
| corr_ret_volume_20 | 4 | 0.000193 |
| corr_ret_volume_20 | 5 | -0.000467 |
| ret_10 | 1 | 0.000166 |
| ret_10 | 2 | 0.001296 |
| ret_10 | 3 | 0.001373 |
| ret_10 | 4 | 0.001230 |
| ret_10 | 5 | -0.001704 |
| ret_20 | 1 | 0.001003 |
| ret_20 | 2 | 0.001245 |
| ret_20 | 3 | 0.000949 |
| ret_20 | 4 | 0.000743 |
| ret_20 | 5 | -0.002684 |
| ret_5 | 1 | -0.000154 |
| ret_5 | 2 | 0.001347 |
| ret_5 | 3 | 0.001367 |
| ret_5 | 4 | 0.000966 |
| ret_5 | 5 | -0.001782 |
| rev_5 | 1 | -0.001781 |
| rev_5 | 2 | 0.000975 |
| rev_5 | 3 | 0.001354 |
| rev_5 | 4 | 0.001351 |
| rev_5 | 5 | -0.000154 |
| std_20 | 1 | 0.000153 |
| std_20 | 2 | 0.001257 |
| std_20 | 3 | 0.001575 |
| std_20 | 4 | 0.001258 |
| std_20 | 5 | -0.002567 |
| volume_ratio_5_20 | 1 | -0.000514 |
| volume_ratio_5_20 | 2 | 0.001038 |
| volume_ratio_5_20 | 3 | 0.001437 |
| volume_ratio_5_20 | 4 | 0.001451 |
| volume_ratio_5_20 | 5 | -0.001616 |

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
