# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2010-01-01` to `2016-12-31`
- Label: `label_10d_t1`
- IC rows: `16734`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.783678 | -0.029445 | -0.374026 | -0.116112 |  | -0.855738 | 2288442 |
| amount_mean_20 | liquidity | watch | 0.783678 | -0.027098 | -0.333168 | -0.105932 |  | -0.747328 | 2288442 |
| ret_20 | momentum | watch | 0.868920 | -0.042875 | -0.309436 | -0.057652 |  | -0.366862 | 2537359 |
| amplitude_20 | risk | negative | 0.783678 | -0.019018 | -0.111309 | -0.048624 | 0.048624 | -0.257997 | 2288442 |
| std_20 | risk | negative | 0.777777 | -0.017690 | -0.109477 | -0.044527 | 0.044527 | -0.246495 | 2271211 |
| corr_ret_volume_20 | price_volume | watch | 0.777777 | -0.020953 | -0.237160 | -0.037565 |  | -0.379559 | 2271211 |
| ret_10 | momentum | watch | 0.882293 | -0.017763 | -0.130592 | -0.032657 |  | -0.218169 | 2576409 |
| ret_5 | momentum | watch | 0.890625 | -0.010604 | -0.079503 | -0.031325 |  | -0.220607 | 2600741 |
| rev_5 | reversal | positive | 0.890625 | 0.010604 | 0.079503 | 0.031325 | 0.031325 | 0.220607 | 2600741 |
| volume_ratio_5_20 | liquidity | watch | 0.783678 | -0.011237 | -0.122932 | -0.004976 |  | -0.047552 | 2288442 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.016695 |
| amount_mean_20 | 2 | 0.012265 |
| amount_mean_20 | 3 | 0.008256 |
| amount_mean_20 | 4 | 0.004972 |
| amount_mean_20 | 5 | -0.000244 |
| amount_std_20 | 1 | 0.017189 |
| amount_std_20 | 2 | 0.012413 |
| amount_std_20 | 3 | 0.008632 |
| amount_std_20 | 4 | 0.004613 |
| amount_std_20 | 5 | -0.000901 |
| amplitude_20 | 1 | 0.007275 |
| amplitude_20 | 2 | 0.010116 |
| amplitude_20 | 3 | 0.010049 |
| amplitude_20 | 4 | 0.008842 |
| amplitude_20 | 5 | 0.005673 |
| corr_ret_volume_20 | 1 | 0.010162 |
| corr_ret_volume_20 | 2 | 0.009776 |
| corr_ret_volume_20 | 3 | 0.008415 |
| corr_ret_volume_20 | 4 | 0.007380 |
| corr_ret_volume_20 | 5 | 0.006137 |
| ret_10 | 1 | 0.008096 |
| ret_10 | 2 | 0.010221 |
| ret_10 | 3 | 0.010437 |
| ret_10 | 4 | 0.008465 |
| ret_10 | 5 | 0.003732 |
| ret_20 | 1 | 0.010766 |
| ret_20 | 2 | 0.010674 |
| ret_20 | 3 | 0.009873 |
| ret_20 | 4 | 0.007729 |
| ret_20 | 5 | 0.002044 |
| ret_5 | 1 | 0.007943 |
| ret_5 | 2 | 0.009977 |
| ret_5 | 3 | 0.010021 |
| ret_5 | 4 | 0.008382 |
| ret_5 | 5 | 0.004179 |
| rev_5 | 1 | 0.004174 |
| rev_5 | 2 | 0.008391 |
| rev_5 | 3 | 0.010022 |
| rev_5 | 4 | 0.009976 |
| rev_5 | 5 | 0.007938 |
| std_20 | 1 | 0.007045 |
| std_20 | 2 | 0.009531 |
| std_20 | 3 | 0.010287 |
| std_20 | 4 | 0.009456 |
| std_20 | 5 | 0.005558 |
| volume_ratio_5_20 | 1 | 0.006009 |
| volume_ratio_5_20 | 2 | 0.008920 |
| volume_ratio_5_20 | 3 | 0.010560 |
| volume_ratio_5_20 | 4 | 0.010166 |
| volume_ratio_5_20 | 5 | 0.006303 |

## Average Top-Quantile Turnover

| factor | turnover |
| --- | --- |
| amount_mean_20 | 0.030080 |
| amount_std_20 | 0.051079 |
| amplitude_20 | 0.071307 |
| corr_ret_volume_20 | 0.186306 |
| ret_10 | 0.238427 |
| ret_20 | 0.175001 |
| ret_5 | 0.330641 |
| rev_5 | 0.384070 |
| std_20 | 0.091629 |
| volume_ratio_5_20 | 0.199476 |

## Output Files

- `factor_summary.csv`
- `ic_series.csv`
- `group_return.csv`
- `turnover.csv`
- `correlation.csv`
