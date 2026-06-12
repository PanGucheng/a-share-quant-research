# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2010-01-01` to `2016-12-31`
- Label: `label_1d_t1`
- IC rows: `16824`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ret_5 | momentum | watch | 0.909128 | -0.026698 | -0.186804 | -0.063384 |  | -0.425490 | 2654773 |
| rev_5 | reversal | positive | 0.909128 | 0.026698 | 0.186804 | 0.063384 | 0.063384 | 0.425490 | 2654773 |
| amount_std_20 | liquidity | watch | 0.800714 | -0.010643 | -0.147910 | -0.047308 |  | -0.428959 | 2338190 |
| ret_10 | momentum | watch | 0.900715 | -0.018232 | -0.122909 | -0.046156 |  | -0.292991 | 2630204 |
| ret_20 | momentum | watch | 0.887116 | -0.021211 | -0.140384 | -0.042950 |  | -0.263776 | 2590493 |
| amount_mean_20 | liquidity | watch | 0.800714 | -0.009398 | -0.130546 | -0.039648 |  | -0.352453 | 2338190 |
| corr_ret_volume_20 | price_volume | watch | 0.794730 | -0.008260 | -0.093302 | -0.023972 |  | -0.247262 | 2320715 |
| amplitude_20 | risk | negative | 0.800714 | 0.005556 | 0.031544 | -0.023917 | 0.023917 | -0.129179 | 2338190 |
| volume_ratio_5_20 | liquidity | watch | 0.800714 | -0.014738 | -0.144270 | -0.022863 |  | -0.212887 | 2338190 |
| std_20 | risk | negative | 0.794730 | 0.007556 | 0.044868 | -0.018775 | 0.018775 | -0.103556 | 2320715 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.001764 |
| amount_mean_20 | 2 | 0.001239 |
| amount_mean_20 | 3 | 0.000765 |
| amount_mean_20 | 4 | 0.000402 |
| amount_mean_20 | 5 | -0.000056 |
| amount_std_20 | 1 | 0.001931 |
| amount_std_20 | 2 | 0.001247 |
| amount_std_20 | 3 | 0.000794 |
| amount_std_20 | 4 | 0.000333 |
| amount_std_20 | 5 | -0.000191 |
| amplitude_20 | 1 | 0.000751 |
| amplitude_20 | 2 | 0.001038 |
| amplitude_20 | 3 | 0.000982 |
| amplitude_20 | 4 | 0.000859 |
| amplitude_20 | 5 | 0.000485 |
| corr_ret_volume_20 | 1 | 0.001051 |
| corr_ret_volume_20 | 2 | 0.001024 |
| corr_ret_volume_20 | 3 | 0.000880 |
| corr_ret_volume_20 | 4 | 0.000702 |
| corr_ret_volume_20 | 5 | 0.000467 |
| ret_10 | 1 | 0.001115 |
| ret_10 | 2 | 0.001070 |
| ret_10 | 3 | 0.001061 |
| ret_10 | 4 | 0.000701 |
| ret_10 | 5 | -0.000114 |
| ret_20 | 1 | 0.001327 |
| ret_20 | 2 | 0.001028 |
| ret_20 | 3 | 0.001017 |
| ret_20 | 4 | 0.000744 |
| ret_20 | 5 | -0.000060 |
| ret_5 | 1 | 0.001579 |
| ret_5 | 2 | 0.001331 |
| ret_5 | 3 | 0.001028 |
| ret_5 | 4 | 0.000490 |
| ret_5 | 5 | -0.000456 |
| rev_5 | 1 | -0.000456 |
| rev_5 | 2 | 0.000492 |
| rev_5 | 3 | 0.001027 |
| rev_5 | 4 | 0.001333 |
| rev_5 | 5 | 0.001579 |
| std_20 | 1 | 0.000681 |
| std_20 | 2 | 0.000935 |
| std_20 | 3 | 0.001003 |
| std_20 | 4 | 0.000931 |
| std_20 | 5 | 0.000576 |
| volume_ratio_5_20 | 1 | 0.000616 |
| volume_ratio_5_20 | 2 | 0.001019 |
| volume_ratio_5_20 | 3 | 0.001165 |
| volume_ratio_5_20 | 4 | 0.001061 |
| volume_ratio_5_20 | 5 | 0.000253 |

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
