# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_10d_t1`
- IC rows: `7004`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.944100 | -0.055954 | -0.517306 | -0.116914 |  | -0.821989 | 1335743 |
| amount_mean_20 | liquidity | watch | 0.944100 | -0.052127 | -0.460959 | -0.112909 |  | -0.740452 | 1335743 |
| amplitude_20 | risk | negative | 0.944100 | -0.044706 | -0.284496 | -0.093295 | 0.093295 | -0.566367 | 1335743 |
| std_20 | risk | negative | 0.942299 | -0.042651 | -0.302004 | -0.088418 | 0.088418 | -0.595008 | 1333195 |
| ret_20 | momentum | watch | 0.949424 | -0.037489 | -0.291439 | -0.044998 |  | -0.324274 | 1343276 |
| corr_ret_volume_20 | price_volume | watch | 0.942299 | -0.017532 | -0.262474 | -0.034607 |  | -0.431134 | 1333195 |
| ret_10 | momentum | watch | 0.963390 | -0.032562 | -0.293199 | -0.033268 |  | -0.261007 | 1363035 |
| ret_5 | momentum | watch | 0.970729 | -0.028309 | -0.261481 | -0.027245 |  | -0.214463 | 1373419 |
| rev_5 | reversal | positive | 0.970729 | 0.028309 | 0.261481 | 0.027245 | 0.027245 | 0.214463 | 1373419 |
| volume_ratio_5_20 | liquidity | watch | 0.944100 | -0.016300 | -0.210225 | -0.016768 |  | -0.191871 | 1335743 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.012025 |
| amount_mean_20 | 2 | 0.008478 |
| amount_mean_20 | 3 | 0.005272 |
| amount_mean_20 | 4 | 0.000742 |
| amount_mean_20 | 5 | -0.004284 |
| amount_std_20 | 1 | 0.012018 |
| amount_std_20 | 2 | 0.008255 |
| amount_std_20 | 3 | 0.005112 |
| amount_std_20 | 4 | 0.001868 |
| amount_std_20 | 5 | -0.005021 |
| amplitude_20 | 1 | 0.005724 |
| amplitude_20 | 2 | 0.007381 |
| amplitude_20 | 3 | 0.006234 |
| amplitude_20 | 4 | 0.003921 |
| amplitude_20 | 5 | -0.001020 |
| corr_ret_volume_20 | 1 | 0.005952 |
| corr_ret_volume_20 | 2 | 0.005483 |
| corr_ret_volume_20 | 3 | 0.004363 |
| corr_ret_volume_20 | 4 | 0.003643 |
| corr_ret_volume_20 | 5 | 0.002410 |
| ret_10 | 1 | 0.002745 |
| ret_10 | 2 | 0.005197 |
| ret_10 | 3 | 0.005834 |
| ret_10 | 4 | 0.006008 |
| ret_10 | 5 | -0.000666 |
| ret_20 | 1 | 0.004022 |
| ret_20 | 2 | 0.005566 |
| ret_20 | 3 | 0.006473 |
| ret_20 | 4 | 0.006480 |
| ret_20 | 5 | -0.000897 |
| ret_5 | 1 | 0.002926 |
| ret_5 | 2 | 0.005112 |
| ret_5 | 3 | 0.005504 |
| ret_5 | 4 | 0.005463 |
| ret_5 | 5 | -0.000760 |
| rev_5 | 1 | -0.000762 |
| rev_5 | 2 | 0.005465 |
| rev_5 | 3 | 0.005499 |
| rev_5 | 4 | 0.005112 |
| rev_5 | 5 | 0.002921 |
| std_20 | 1 | 0.005792 |
| std_20 | 2 | 0.006930 |
| std_20 | 3 | 0.006391 |
| std_20 | 4 | 0.004106 |
| std_20 | 5 | -0.001365 |
| volume_ratio_5_20 | 1 | 0.004182 |
| volume_ratio_5_20 | 2 | 0.004652 |
| volume_ratio_5_20 | 3 | 0.005388 |
| volume_ratio_5_20 | 4 | 0.005155 |
| volume_ratio_5_20 | 5 | 0.002860 |

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
