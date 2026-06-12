# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_20d_t1`
- IC rows: `5504`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.918917 | -0.018437 | -0.157420 | -0.092683 |  | -0.509807 | 1007345 |
| amount_mean_20 | liquidity | watch | 0.918917 | -0.010806 | -0.091376 | -0.081975 |  | -0.417156 | 1007345 |
| ret_20 | momentum | watch | 0.923007 | -0.045153 | -0.321941 | -0.079541 |  | -0.474521 | 1011829 |
| ret_10 | momentum | watch | 0.940371 | -0.037494 | -0.288477 | -0.056839 |  | -0.372034 | 1030864 |
| std_20 | risk | negative | 0.916840 | -0.015172 | -0.084787 | -0.053787 | 0.053787 | -0.236458 | 1005068 |
| amplitude_20 | risk | negative | 0.918917 | -0.005832 | -0.030278 | -0.051124 | 0.051124 | -0.213414 | 1007345 |
| ret_5 | momentum | watch | 0.949394 | -0.032445 | -0.256620 | -0.040805 |  | -0.267109 | 1040755 |
| rev_5 | reversal | positive | 0.949394 | 0.032445 | 0.256620 | 0.040805 | 0.040805 | 0.267109 | 1040755 |
| volume_ratio_5_20 | liquidity | watch | 0.918917 | -0.024153 | -0.296141 | -0.037255 |  | -0.375094 | 1007345 |
| corr_ret_volume_20 | price_volume | watch | 0.916840 | 0.012526 | 0.171034 | -0.006012 |  | -0.066176 | 1005068 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.028023 |
| amount_mean_20 | 2 | 0.024763 |
| amount_mean_20 | 3 | 0.021296 |
| amount_mean_20 | 4 | 0.018128 |
| amount_mean_20 | 5 | 0.020723 |
| amount_std_20 | 1 | 0.028369 |
| amount_std_20 | 2 | 0.024385 |
| amount_std_20 | 3 | 0.023080 |
| amount_std_20 | 4 | 0.019377 |
| amount_std_20 | 5 | 0.017724 |
| amplitude_20 | 1 | 0.013900 |
| amplitude_20 | 2 | 0.021025 |
| amplitude_20 | 3 | 0.026385 |
| amplitude_20 | 4 | 0.027688 |
| amplitude_20 | 5 | 0.023955 |
| corr_ret_volume_20 | 1 | 0.020196 |
| corr_ret_volume_20 | 2 | 0.020549 |
| corr_ret_volume_20 | 3 | 0.022757 |
| corr_ret_volume_20 | 4 | 0.024545 |
| corr_ret_volume_20 | 5 | 0.024912 |
| ret_10 | 1 | 0.023407 |
| ret_10 | 2 | 0.023487 |
| ret_10 | 3 | 0.023309 |
| ret_10 | 4 | 0.022079 |
| ret_10 | 5 | 0.016325 |
| ret_20 | 1 | 0.025669 |
| ret_20 | 2 | 0.025999 |
| ret_20 | 3 | 0.023885 |
| ret_20 | 4 | 0.021364 |
| ret_20 | 5 | 0.015391 |
| ret_5 | 1 | 0.021084 |
| ret_5 | 2 | 0.022102 |
| ret_5 | 3 | 0.021544 |
| ret_5 | 4 | 0.021086 |
| ret_5 | 5 | 0.015201 |
| rev_5 | 1 | 0.015207 |
| rev_5 | 2 | 0.021074 |
| rev_5 | 3 | 0.021566 |
| rev_5 | 4 | 0.022082 |
| rev_5 | 5 | 0.021073 |
| std_20 | 1 | 0.014193 |
| std_20 | 2 | 0.022613 |
| std_20 | 3 | 0.027154 |
| std_20 | 4 | 0.027895 |
| std_20 | 5 | 0.021115 |
| volume_ratio_5_20 | 1 | 0.024634 |
| volume_ratio_5_20 | 2 | 0.022965 |
| volume_ratio_5_20 | 3 | 0.023448 |
| volume_ratio_5_20 | 4 | 0.022608 |
| volume_ratio_5_20 | 5 | 0.019289 |

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
