# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_20d_t1`
- IC rows: `6904`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.930317 | -0.072067 | -0.662541 | -0.149689 |  | -1.093560 | 1316242 |
| amount_mean_20 | liquidity | watch | 0.930317 | -0.069467 | -0.635901 | -0.148783 |  | -1.021089 | 1316242 |
| amplitude_20 | risk | negative | 0.930317 | -0.058651 | -0.375815 | -0.110202 | 0.110202 | -0.652737 | 1316242 |
| std_20 | risk | negative | 0.928519 | -0.052578 | -0.373839 | -0.102066 | 0.102066 | -0.666263 | 1313698 |
| ret_20 | momentum | watch | 0.935487 | -0.048478 | -0.389123 | -0.061054 |  | -0.435218 | 1323557 |
| corr_ret_volume_20 | price_volume | watch | 0.928519 | -0.025578 | -0.347038 | -0.045155 |  | -0.517990 | 1313698 |
| ret_10 | momentum | watch | 0.949410 | -0.039349 | -0.345087 | -0.038644 |  | -0.300472 | 1343256 |
| ret_5 | momentum | watch | 0.956737 | -0.029815 | -0.278380 | -0.023893 |  | -0.190979 | 1353622 |
| rev_5 | reversal | positive | 0.956737 | 0.029815 | 0.278380 | 0.023893 | 0.023893 | 0.190979 | 1353622 |
| volume_ratio_5_20 | liquidity | watch | 0.930317 | -0.018386 | -0.231826 | -0.022859 |  | -0.267264 | 1316242 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.022957 |
| amount_mean_20 | 2 | 0.015559 |
| amount_mean_20 | 3 | 0.009259 |
| amount_mean_20 | 4 | 0.001446 |
| amount_mean_20 | 5 | -0.007604 |
| amount_std_20 | 1 | 0.022606 |
| amount_std_20 | 2 | 0.015583 |
| amount_std_20 | 3 | 0.008697 |
| amount_std_20 | 4 | 0.002999 |
| amount_std_20 | 5 | -0.008265 |
| amplitude_20 | 1 | 0.010801 |
| amplitude_20 | 2 | 0.013745 |
| amplitude_20 | 3 | 0.010964 |
| amplitude_20 | 4 | 0.007811 |
| amplitude_20 | 5 | -0.001689 |
| corr_ret_volume_20 | 1 | 0.011446 |
| corr_ret_volume_20 | 2 | 0.010684 |
| corr_ret_volume_20 | 3 | 0.008807 |
| corr_ret_volume_20 | 4 | 0.006540 |
| corr_ret_volume_20 | 5 | 0.003795 |
| ret_10 | 1 | 0.007661 |
| ret_10 | 2 | 0.010814 |
| ret_10 | 3 | 0.011965 |
| ret_10 | 4 | 0.011048 |
| ret_10 | 5 | 0.000672 |
| ret_20 | 1 | 0.009192 |
| ret_20 | 2 | 0.010850 |
| ret_20 | 3 | 0.011519 |
| ret_20 | 4 | 0.010168 |
| ret_20 | 5 | -0.000565 |
| ret_5 | 1 | 0.006346 |
| ret_5 | 2 | 0.010359 |
| ret_5 | 3 | 0.011670 |
| ret_5 | 4 | 0.011388 |
| ret_5 | 5 | 0.001612 |
| rev_5 | 1 | 0.001611 |
| rev_5 | 2 | 0.011384 |
| rev_5 | 3 | 0.011669 |
| rev_5 | 4 | 0.010329 |
| rev_5 | 5 | 0.006339 |
| std_20 | 1 | 0.011024 |
| std_20 | 2 | 0.012463 |
| std_20 | 3 | 0.011332 |
| std_20 | 4 | 0.007795 |
| std_20 | 5 | -0.001336 |
| volume_ratio_5_20 | 1 | 0.009062 |
| volume_ratio_5_20 | 2 | 0.009167 |
| volume_ratio_5_20 | 3 | 0.009296 |
| volume_ratio_5_20 | 4 | 0.008715 |
| volume_ratio_5_20 | 5 | 0.005387 |

## Average Top-Quantile Turnover

| factor | turnover |
| --- | --- |
| amount_mean_20 | 0.017394 |
| amount_std_20 | 0.033584 |
| amplitude_20 | 0.047566 |
| corr_ret_volume_20 | 0.175225 |
| ret_10 | 0.231912 |
| ret_20 | 0.166970 |
| ret_5 | 0.324347 |
| rev_5 | 0.353128 |
| std_20 | 0.061837 |
| volume_ratio_5_20 | 0.184081 |

## Output Files

- `factor_summary.csv`
- `ic_series.csv`
- `group_return.csv`
- `turnover.csv`
- `correlation.csv`
