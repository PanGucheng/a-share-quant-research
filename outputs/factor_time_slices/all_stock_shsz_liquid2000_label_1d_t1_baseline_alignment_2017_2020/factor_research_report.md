# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- IC rows: `8534`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.917698 | -0.005131 | -0.032242 | -0.038912 | 0.038912 | -0.221254 | 1595449 |
| std_20 | risk | negative | 0.915476 | -0.006715 | -0.043930 | -0.036701 | 0.036701 | -0.213982 | 1591585 |
| rev_5 | reversal | positive | 0.950865 | 0.010601 | 0.083343 | 0.035087 | 0.035087 | 0.256763 | 1653111 |
| ret_5 | momentum | watch | 0.950865 | -0.010601 | -0.083343 | -0.035087 |  | -0.256763 | 1653111 |
| ret_20 | momentum | watch | 0.928107 | -0.015307 | -0.109212 | -0.034431 |  | -0.236890 | 1613544 |
| ret_10 | momentum | watch | 0.942466 | -0.011186 | -0.083698 | -0.032329 |  | -0.226800 | 1638509 |
| amount_std_20 | liquidity | watch | 0.917698 | -0.006649 | -0.073417 | -0.029473 |  | -0.233094 | 1595449 |
| volume_ratio_5_20 | liquidity | watch | 0.917698 | -0.016702 | -0.173360 | -0.024427 |  | -0.258236 | 1595449 |
| corr_ret_volume_20 | price_volume | watch | 0.915476 | -0.005394 | -0.070468 | -0.020126 |  | -0.231690 | 1591585 |
| amount_mean_20 | liquidity | watch | 0.917698 | -0.001059 | -0.011891 | -0.017891 |  | -0.137948 | 1595449 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.000352 |
| amount_mean_20 | 2 | 0.000202 |
| amount_mean_20 | 3 | 0.000053 |
| amount_mean_20 | 4 | -0.000009 |
| amount_mean_20 | 5 | -0.000121 |
| amount_std_20 | 1 | 0.000485 |
| amount_std_20 | 2 | 0.000318 |
| amount_std_20 | 3 | 0.000143 |
| amount_std_20 | 4 | -0.000050 |
| amount_std_20 | 5 | -0.000419 |
| amplitude_20 | 1 | 0.000125 |
| amplitude_20 | 2 | 0.000275 |
| amplitude_20 | 3 | 0.000307 |
| amplitude_20 | 4 | 0.000256 |
| amplitude_20 | 5 | -0.000485 |
| corr_ret_volume_20 | 1 | 0.000210 |
| corr_ret_volume_20 | 2 | 0.000121 |
| corr_ret_volume_20 | 3 | 0.000153 |
| corr_ret_volume_20 | 4 | 0.000034 |
| corr_ret_volume_20 | 5 | -0.000085 |
| ret_10 | 1 | -0.000021 |
| ret_10 | 2 | 0.000303 |
| ret_10 | 3 | 0.000343 |
| ret_10 | 4 | 0.000315 |
| ret_10 | 5 | -0.000430 |
| ret_20 | 1 | 0.000194 |
| ret_20 | 2 | 0.000246 |
| ret_20 | 3 | 0.000212 |
| ret_20 | 4 | 0.000169 |
| ret_20 | 5 | -0.000534 |
| ret_5 | 1 | -0.000066 |
| ret_5 | 2 | 0.000264 |
| ret_5 | 3 | 0.000366 |
| ret_5 | 4 | 0.000204 |
| ret_5 | 5 | -0.000626 |
| rev_5 | 1 | -0.000625 |
| rev_5 | 2 | 0.000206 |
| rev_5 | 3 | 0.000366 |
| rev_5 | 4 | 0.000265 |
| rev_5 | 5 | -0.000066 |
| std_20 | 1 | 0.000089 |
| std_20 | 2 | 0.000321 |
| std_20 | 3 | 0.000307 |
| std_20 | 4 | 0.000234 |
| std_20 | 5 | -0.000517 |
| volume_ratio_5_20 | 1 | -0.000023 |
| volume_ratio_5_20 | 2 | 0.000293 |
| volume_ratio_5_20 | 3 | 0.000370 |
| volume_ratio_5_20 | 4 | 0.000363 |
| volume_ratio_5_20 | 5 | -0.000526 |

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
