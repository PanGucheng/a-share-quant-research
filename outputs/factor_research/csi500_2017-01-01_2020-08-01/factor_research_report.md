# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `csi500`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- IC rows: `8534`

## Factor Summary

| factor | coverage | mean_ic | icir | mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | 0.912285 | 0.003571 | 0.019173 | -0.028375 | -0.146709 | 397165 |
| std_20 | 0.909570 | 0.001192 | 0.006941 | -0.027684 | -0.149338 | 395983 |
| amount_std_20 | 0.912285 | -0.006404 | -0.040019 | -0.027039 | -0.165553 | 397165 |
| ret_20 | 0.919470 | -0.002754 | -0.016393 | -0.024963 | -0.153608 | 400293 |
| rev_5 | 0.951864 | 0.001332 | 0.008738 | 0.022072 | 0.146376 | 414396 |
| ret_5 | 0.951864 | -0.001332 | -0.008738 | -0.022072 | -0.146376 | 414396 |
| ret_10 | 0.940400 | 0.001042 | 0.006420 | -0.021129 | -0.133304 | 409405 |
| amount_mean_20 | 0.912285 | -0.000253 | -0.001541 | -0.017888 | -0.104798 | 397165 |
| volume_ratio_5_20 | 0.912285 | -0.007199 | -0.060296 | -0.017663 | -0.155295 | 397165 |
| corr_ret_volume_20 | 0.909570 | -0.000799 | -0.008314 | -0.016934 | -0.166271 | 395983 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.000156 |
| amount_mean_20 | 2 | 0.000148 |
| amount_mean_20 | 3 | 0.000331 |
| amount_mean_20 | 4 | 0.000209 |
| amount_mean_20 | 5 | 0.000037 |
| amount_std_20 | 1 | 0.000253 |
| amount_std_20 | 2 | 0.000255 |
| amount_std_20 | 3 | 0.000397 |
| amount_std_20 | 4 | 0.000131 |
| amount_std_20 | 5 | -0.000156 |
| amplitude_20 | 1 | -0.000089 |
| amplitude_20 | 2 | 0.000154 |
| amplitude_20 | 3 | 0.000250 |
| amplitude_20 | 4 | 0.000510 |
| amplitude_20 | 5 | 0.000056 |
| corr_ret_volume_20 | 1 | 0.000196 |
| corr_ret_volume_20 | 2 | 0.000170 |
| corr_ret_volume_20 | 3 | 0.000148 |
| corr_ret_volume_20 | 4 | 0.000149 |
| corr_ret_volume_20 | 5 | 0.000186 |
| ret_10 | 1 | 0.000062 |
| ret_10 | 2 | 0.000133 |
| ret_10 | 3 | 0.000261 |
| ret_10 | 4 | 0.000308 |
| ret_10 | 5 | 0.000194 |
| ret_20 | 1 | 0.000173 |
| ret_20 | 2 | 0.000185 |
| ret_20 | 3 | 0.000140 |
| ret_20 | 4 | 0.000203 |
| ret_20 | 5 | 0.000089 |
| ret_5 | 1 | 0.000009 |
| ret_5 | 2 | 0.000122 |
| ret_5 | 3 | 0.000251 |
| ret_5 | 4 | 0.000330 |
| ret_5 | 5 | -0.000042 |
| rev_5 | 1 | -0.000043 |
| rev_5 | 2 | 0.000331 |
| rev_5 | 3 | 0.000245 |
| rev_5 | 4 | 0.000128 |
| rev_5 | 5 | 0.000006 |
| std_20 | 1 | -0.000043 |
| std_20 | 2 | 0.000176 |
| std_20 | 3 | 0.000342 |
| std_20 | 4 | 0.000233 |
| std_20 | 5 | 0.000145 |
| volume_ratio_5_20 | 1 | -0.000050 |
| volume_ratio_5_20 | 2 | 0.000282 |
| volume_ratio_5_20 | 3 | 0.000333 |
| volume_ratio_5_20 | 4 | 0.000446 |
| volume_ratio_5_20 | 5 | -0.000131 |

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
