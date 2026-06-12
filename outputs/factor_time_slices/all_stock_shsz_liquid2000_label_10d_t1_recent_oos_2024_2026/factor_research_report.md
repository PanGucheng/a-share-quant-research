# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Label: `label_10d_t1`
- IC rows: `5604`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.935525 | -0.016784 | -0.146872 | -0.080533 |  | -0.461115 | 1025551 |
| ret_20 | momentum | watch | 0.940354 | -0.040526 | -0.294551 | -0.074818 |  | -0.474648 | 1030845 |
| amount_mean_20 | liquidity | watch | 0.935525 | -0.008900 | -0.076607 | -0.067974 |  | -0.355399 | 1025551 |
| std_20 | risk | negative | 0.933433 | -0.008832 | -0.051932 | -0.047369 | 0.047369 | -0.216977 | 1023258 |
| amplitude_20 | risk | negative | 0.935525 | 0.000300 | 0.001637 | -0.045089 | 0.045089 | -0.195627 | 1025551 |
| ret_10 | momentum | watch | 0.957689 | -0.030268 | -0.223598 | -0.043170 |  | -0.274011 | 1049848 |
| volume_ratio_5_20 | liquidity | watch | 0.935525 | -0.031454 | -0.404260 | -0.040647 |  | -0.442011 | 1025551 |
| ret_5 | momentum | watch | 0.966765 | -0.028819 | -0.224630 | -0.034178 |  | -0.223850 | 1059798 |
| rev_5 | reversal | positive | 0.966765 | 0.028819 | 0.224630 | 0.034178 | 0.034178 | 0.223850 | 1059798 |
| corr_ret_volume_20 | price_volume | watch | 0.933433 | -0.000543 | -0.007764 | -0.018876 |  | -0.210971 | 1023258 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.014675 |
| amount_mean_20 | 2 | 0.012601 |
| amount_mean_20 | 3 | 0.010711 |
| amount_mean_20 | 4 | 0.009072 |
| amount_mean_20 | 5 | 0.010025 |
| amount_std_20 | 1 | 0.015137 |
| amount_std_20 | 2 | 0.012812 |
| amount_std_20 | 3 | 0.011921 |
| amount_std_20 | 4 | 0.009154 |
| amount_std_20 | 5 | 0.008062 |
| amplitude_20 | 1 | 0.007041 |
| amplitude_20 | 2 | 0.010160 |
| amplitude_20 | 3 | 0.013817 |
| amplitude_20 | 4 | 0.014475 |
| amplitude_20 | 5 | 0.011606 |
| corr_ret_volume_20 | 1 | 0.011484 |
| corr_ret_volume_20 | 2 | 0.010935 |
| corr_ret_volume_20 | 3 | 0.011802 |
| corr_ret_volume_20 | 4 | 0.012083 |
| corr_ret_volume_20 | 5 | 0.011249 |
| ret_10 | 1 | 0.008822 |
| ret_10 | 2 | 0.010080 |
| ret_10 | 3 | 0.010710 |
| ret_10 | 4 | 0.010904 |
| ret_10 | 5 | 0.005851 |
| ret_20 | 1 | 0.013340 |
| ret_20 | 2 | 0.013626 |
| ret_20 | 3 | 0.012462 |
| ret_20 | 4 | 0.011429 |
| ret_20 | 5 | 0.006276 |
| ret_5 | 1 | 0.008036 |
| ret_5 | 2 | 0.009759 |
| ret_5 | 3 | 0.009729 |
| ret_5 | 4 | 0.010586 |
| ret_5 | 5 | 0.005356 |
| rev_5 | 1 | 0.005359 |
| rev_5 | 2 | 0.010586 |
| rev_5 | 3 | 0.009722 |
| rev_5 | 4 | 0.009751 |
| rev_5 | 5 | 0.008032 |
| std_20 | 1 | 0.006995 |
| std_20 | 2 | 0.011625 |
| std_20 | 3 | 0.014211 |
| std_20 | 4 | 0.014787 |
| std_20 | 5 | 0.009945 |
| volume_ratio_5_20 | 1 | 0.012772 |
| volume_ratio_5_20 | 2 | 0.012374 |
| volume_ratio_5_20 | 3 | 0.012592 |
| volume_ratio_5_20 | 4 | 0.011479 |
| volume_ratio_5_20 | 5 | 0.007874 |

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
