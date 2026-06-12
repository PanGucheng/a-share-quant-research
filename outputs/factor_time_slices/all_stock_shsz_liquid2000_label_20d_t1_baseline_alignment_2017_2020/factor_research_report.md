# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2017-01-01` to `2020-08-01`
- Label: `label_20d_t1`
- IC rows: `8344`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.888484 | -0.048756 | -0.360950 | -0.081247 | 0.081247 | -0.525696 | 1544658 |
| std_20 | risk | negative | 0.886342 | -0.049577 | -0.377892 | -0.075653 | 0.075653 | -0.498810 | 1540934 |
| ret_20 | momentum | watch | 0.898444 | -0.043839 | -0.334550 | -0.055827 |  | -0.375476 | 1561975 |
| amount_std_20 | liquidity | watch | 0.888484 | -0.019556 | -0.205571 | -0.049600 |  | -0.337376 | 1544658 |
| ret_10 | momentum | watch | 0.912362 | -0.040674 | -0.324389 | -0.044585 |  | -0.315021 | 1586171 |
| corr_ret_volume_20 | price_volume | watch | 0.886342 | -0.020334 | -0.265480 | -0.032429 |  | -0.367129 | 1540934 |
| volume_ratio_5_20 | liquidity | watch | 0.888484 | -0.035544 | -0.422866 | -0.027232 |  | -0.292759 | 1544658 |
| amount_mean_20 | liquidity | watch | 0.888484 | -0.003558 | -0.036968 | -0.026338 |  | -0.168464 | 1544658 |
| ret_5 | momentum | watch | 0.920484 | -0.028746 | -0.257835 | -0.026217 |  | -0.206832 | 1600292 |
| rev_5 | reversal | positive | 0.920484 | 0.028746 | 0.257835 | 0.026217 | 0.026217 | 0.206832 | 1600292 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.002372 |
| amount_mean_20 | 2 | 0.001532 |
| amount_mean_20 | 3 | 0.000627 |
| amount_mean_20 | 4 | 0.000549 |
| amount_mean_20 | 5 | -0.000337 |
| amount_std_20 | 1 | 0.003502 |
| amount_std_20 | 2 | 0.002889 |
| amount_std_20 | 3 | 0.002352 |
| amount_std_20 | 4 | -0.000019 |
| amount_std_20 | 5 | -0.003977 |
| amplitude_20 | 1 | 0.001399 |
| amplitude_20 | 2 | 0.003208 |
| amplitude_20 | 3 | 0.004749 |
| amplitude_20 | 4 | 0.002172 |
| amplitude_20 | 5 | -0.006776 |
| corr_ret_volume_20 | 1 | 0.002954 |
| corr_ret_volume_20 | 2 | 0.002280 |
| corr_ret_volume_20 | 3 | 0.001052 |
| corr_ret_volume_20 | 4 | -0.000188 |
| corr_ret_volume_20 | 5 | -0.001561 |
| ret_10 | 1 | 0.002564 |
| ret_10 | 2 | 0.004023 |
| ret_10 | 3 | 0.003647 |
| ret_10 | 4 | 0.002067 |
| ret_10 | 5 | -0.005899 |
| ret_20 | 1 | 0.003561 |
| ret_20 | 2 | 0.003341 |
| ret_20 | 3 | 0.002462 |
| ret_20 | 4 | 0.001010 |
| ret_20 | 5 | -0.006642 |
| ret_5 | 1 | 0.000633 |
| ret_5 | 2 | 0.003679 |
| ret_5 | 3 | 0.003766 |
| ret_5 | 4 | 0.003157 |
| ret_5 | 5 | -0.004344 |
| rev_5 | 1 | -0.004341 |
| rev_5 | 2 | 0.003153 |
| rev_5 | 3 | 0.003764 |
| rev_5 | 4 | 0.003689 |
| rev_5 | 5 | 0.000630 |
| std_20 | 1 | 0.000076 |
| std_20 | 2 | 0.003467 |
| std_20 | 3 | 0.004860 |
| std_20 | 4 | 0.003867 |
| std_20 | 5 | -0.007721 |
| volume_ratio_5_20 | 1 | -0.000218 |
| volume_ratio_5_20 | 2 | 0.003337 |
| volume_ratio_5_20 | 3 | 0.003924 |
| volume_ratio_5_20 | 4 | 0.002834 |
| volume_ratio_5_20 | 5 | -0.005125 |

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
