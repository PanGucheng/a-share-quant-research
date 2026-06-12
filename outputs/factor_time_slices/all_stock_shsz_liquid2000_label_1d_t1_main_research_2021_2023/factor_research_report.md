# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Label: `label_1d_t1`
- IC rows: `7094`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.957495 | -0.013557 | -0.082434 | -0.056665 | 0.056665 | -0.330346 | 1354694 |
| amount_std_20 | liquidity | watch | 0.957495 | -0.018314 | -0.165420 | -0.054920 |  | -0.381521 | 1354694 |
| std_20 | risk | negative | 0.955676 | -0.013312 | -0.089884 | -0.053068 | 0.053068 | -0.341862 | 1352121 |
| amount_mean_20 | liquidity | watch | 0.957495 | -0.016616 | -0.144802 | -0.050109 |  | -0.323093 | 1354694 |
| ret_20 | momentum | watch | 0.962938 | -0.012027 | -0.082495 | -0.027197 |  | -0.170708 | 1362395 |
| ret_10 | momentum | watch | 0.977009 | -0.011275 | -0.084710 | -0.023723 |  | -0.161821 | 1382304 |
| ret_5 | momentum | watch | 0.984502 | -0.010166 | -0.078675 | -0.022955 |  | -0.158646 | 1392905 |
| rev_5 | reversal | positive | 0.984502 | 0.010166 | 0.078675 | 0.022955 | 0.022955 | 0.158646 | 1392905 |
| corr_ret_volume_20 | price_volume | watch | 0.955676 | -0.004564 | -0.065688 | -0.022496 |  | -0.268601 | 1352121 |
| volume_ratio_5_20 | liquidity | watch | 0.957495 | -0.010333 | -0.111664 | -0.020185 |  | -0.201369 | 1354694 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.001193 |
| amount_mean_20 | 2 | 0.000910 |
| amount_mean_20 | 3 | 0.000544 |
| amount_mean_20 | 4 | 0.000091 |
| amount_mean_20 | 5 | -0.000469 |
| amount_std_20 | 1 | 0.001231 |
| amount_std_20 | 2 | 0.000846 |
| amount_std_20 | 3 | 0.000533 |
| amount_std_20 | 4 | 0.000267 |
| amount_std_20 | 5 | -0.000609 |
| amplitude_20 | 1 | 0.000568 |
| amplitude_20 | 2 | 0.000767 |
| amplitude_20 | 3 | 0.000731 |
| amplitude_20 | 4 | 0.000397 |
| amplitude_20 | 5 | -0.000193 |
| corr_ret_volume_20 | 1 | 0.000574 |
| corr_ret_volume_20 | 2 | 0.000552 |
| corr_ret_volume_20 | 3 | 0.000402 |
| corr_ret_volume_20 | 4 | 0.000398 |
| corr_ret_volume_20 | 5 | 0.000316 |
| ret_10 | 1 | 0.000255 |
| ret_10 | 2 | 0.000602 |
| ret_10 | 3 | 0.000661 |
| ret_10 | 4 | 0.000534 |
| ret_10 | 5 | -0.000244 |
| ret_20 | 1 | 0.000350 |
| ret_20 | 2 | 0.000606 |
| ret_20 | 3 | 0.000732 |
| ret_20 | 4 | 0.000704 |
| ret_20 | 5 | -0.000215 |
| ret_5 | 1 | 0.000367 |
| ret_5 | 2 | 0.000680 |
| ret_5 | 3 | 0.000647 |
| ret_5 | 4 | 0.000524 |
| ret_5 | 5 | -0.000327 |
| rev_5 | 1 | -0.000329 |
| rev_5 | 2 | 0.000528 |
| rev_5 | 3 | 0.000643 |
| rev_5 | 4 | 0.000685 |
| rev_5 | 5 | 0.000365 |
| std_20 | 1 | 0.000580 |
| std_20 | 2 | 0.000777 |
| std_20 | 3 | 0.000696 |
| std_20 | 4 | 0.000409 |
| std_20 | 5 | -0.000219 |
| volume_ratio_5_20 | 1 | 0.000480 |
| volume_ratio_5_20 | 2 | 0.000530 |
| volume_ratio_5_20 | 3 | 0.000616 |
| volume_ratio_5_20 | 4 | 0.000526 |
| volume_ratio_5_20 | 5 | 0.000117 |

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
