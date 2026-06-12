# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_1d_t1`
- IC rows: `5694`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.951765 | -0.006754 | -0.055031 | -0.044874 |  | -0.250312 | 1043354 |
| std_20 | risk | negative | 0.949605 | 0.002342 | 0.012599 | -0.039549 | 0.039549 | -0.170010 | 1040986 |
| ret_20 | momentum | watch | 0.956855 | -0.013153 | -0.079355 | -0.038603 |  | -0.208456 | 1048934 |
| amplitude_20 | risk | negative | 0.951765 | 0.006661 | 0.034158 | -0.038382 | 0.038382 | -0.159900 | 1043354 |
| amount_mean_20 | liquidity | watch | 0.951765 | -0.002860 | -0.022980 | -0.035369 |  | -0.182913 | 1043354 |
| ret_10 | momentum | watch | 0.974300 | -0.011614 | -0.073436 | -0.030530 |  | -0.169726 | 1068058 |
| volume_ratio_5_20 | liquidity | watch | 0.951765 | -0.014470 | -0.144960 | -0.029159 |  | -0.264656 | 1043354 |
| ret_5 | momentum | watch | 0.983463 | -0.008630 | -0.054831 | -0.025411 |  | -0.137395 | 1078103 |
| rev_5 | reversal | positive | 0.983463 | 0.008630 | 0.054831 | 0.025411 | 0.025411 | 0.137395 | 1078103 |
| corr_ret_volume_20 | price_volume | watch | 0.949605 | -0.001261 | -0.015068 | -0.020260 |  | -0.201302 | 1040986 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.001249 |
| amount_mean_20 | 2 | 0.001089 |
| amount_mean_20 | 3 | 0.000834 |
| amount_mean_20 | 4 | 0.000756 |
| amount_mean_20 | 5 | 0.000737 |
| amount_std_20 | 1 | 0.001288 |
| amount_std_20 | 2 | 0.001206 |
| amount_std_20 | 3 | 0.001026 |
| amount_std_20 | 4 | 0.000753 |
| amount_std_20 | 5 | 0.000394 |
| amplitude_20 | 1 | 0.000600 |
| amplitude_20 | 2 | 0.000804 |
| amplitude_20 | 3 | 0.001188 |
| amplitude_20 | 4 | 0.001285 |
| amplitude_20 | 5 | 0.000790 |
| corr_ret_volume_20 | 1 | 0.001014 |
| corr_ret_volume_20 | 2 | 0.001105 |
| corr_ret_volume_20 | 3 | 0.001056 |
| corr_ret_volume_20 | 4 | 0.000926 |
| corr_ret_volume_20 | 5 | 0.000961 |
| ret_10 | 1 | 0.000729 |
| ret_10 | 2 | 0.000876 |
| ret_10 | 3 | 0.000997 |
| ret_10 | 4 | 0.000976 |
| ret_10 | 5 | 0.000412 |
| ret_20 | 1 | 0.001021 |
| ret_20 | 2 | 0.001226 |
| ret_20 | 3 | 0.001119 |
| ret_20 | 4 | 0.001198 |
| ret_20 | 5 | 0.000426 |
| ret_5 | 1 | 0.000583 |
| ret_5 | 2 | 0.000853 |
| ret_5 | 3 | 0.000946 |
| ret_5 | 4 | 0.001060 |
| ret_5 | 5 | 0.000341 |
| rev_5 | 1 | 0.000342 |
| rev_5 | 2 | 0.001058 |
| rev_5 | 3 | 0.000942 |
| rev_5 | 4 | 0.000856 |
| rev_5 | 5 | 0.000583 |
| std_20 | 1 | 0.000722 |
| std_20 | 2 | 0.001098 |
| std_20 | 3 | 0.001246 |
| std_20 | 4 | 0.001350 |
| std_20 | 5 | 0.000648 |
| volume_ratio_5_20 | 1 | 0.000977 |
| volume_ratio_5_20 | 2 | 0.001096 |
| volume_ratio_5_20 | 3 | 0.001193 |
| volume_ratio_5_20 | 4 | 0.001015 |
| volume_ratio_5_20 | 5 | 0.000385 |

## Average Top-Quantile Turnover

| factor | turnover |
| --- | --- |
| amount_mean_20 | 0.017693 |
| amount_std_20 | 0.034104 |
| amplitude_20 | 0.048125 |
| corr_ret_volume_20 | 0.185322 |
| ret_10 | 0.223220 |
| ret_20 | 0.159770 |
| ret_5 | 0.317548 |
| rev_5 | 0.358026 |
| std_20 | 0.061121 |
| volume_ratio_5_20 | 0.181524 |

## Output Files

- `factor_summary.csv`
- `ic_series.csv`
- `group_return.csv`
- `turnover.csv`
- `correlation.csv`
