# Factor Research Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2010-01-01` to `2016-12-31`
- Label: `label_20d_t1`
- IC rows: `16634`

## Factor Summary

| factor | category | expected_direction | coverage | mean_ic | icir | mean_rank_ic | directional_mean_rank_ic | rank_icir | valid_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amount_std_20 | liquidity | watch | 0.771104 | -0.035506 | -0.428681 | -0.141493 |  | -0.958807 | 2251724 |
| amount_mean_20 | liquidity | watch | 0.771104 | -0.032778 | -0.379875 | -0.134537 |  | -0.864187 | 2251724 |
| ret_20 | momentum | watch | 0.855661 | -0.059495 | -0.421499 | -0.072637 |  | -0.450437 | 2498641 |
| amplitude_20 | risk | negative | 0.771104 | -0.030585 | -0.180817 | -0.060883 | 0.060883 | -0.322193 | 2251724 |
| std_20 | risk | negative | 0.765253 | -0.027465 | -0.167706 | -0.054968 | 0.054968 | -0.297503 | 2234639 |
| corr_ret_volume_20 | price_volume | watch | 0.765253 | -0.028788 | -0.318578 | -0.044167 |  | -0.446077 | 2234639 |
| ret_10 | momentum | watch | 0.868847 | -0.033961 | -0.257613 | -0.043588 |  | -0.293240 | 2537146 |
| ret_5 | momentum | watch | 0.877052 | -0.019224 | -0.153581 | -0.032244 |  | -0.233556 | 2561107 |
| rev_5 | reversal | positive | 0.877052 | 0.019224 | 0.153581 | 0.032244 | 0.032244 | 0.233556 | 2561107 |
| volume_ratio_5_20 | liquidity | watch | 0.771104 | -0.018188 | -0.198003 | -0.008894 |  | -0.083517 | 2251724 |

## Average Group Returns

| factor | quantile | mean_label |
| --- | --- | --- |
| amount_mean_20 | 1 | 0.031927 |
| amount_mean_20 | 2 | 0.023928 |
| amount_mean_20 | 3 | 0.016656 |
| amount_mean_20 | 4 | 0.009813 |
| amount_mean_20 | 5 | 0.000425 |
| amount_std_20 | 1 | 0.032020 |
| amount_std_20 | 2 | 0.023915 |
| amount_std_20 | 3 | 0.017193 |
| amount_std_20 | 4 | 0.010057 |
| amount_std_20 | 5 | -0.000433 |
| amplitude_20 | 1 | 0.014822 |
| amplitude_20 | 2 | 0.019194 |
| amplitude_20 | 3 | 0.019522 |
| amplitude_20 | 4 | 0.017805 |
| amplitude_20 | 5 | 0.011427 |
| corr_ret_volume_20 | 1 | 0.020372 |
| corr_ret_volume_20 | 2 | 0.018580 |
| corr_ret_volume_20 | 3 | 0.016451 |
| corr_ret_volume_20 | 4 | 0.014352 |
| corr_ret_volume_20 | 5 | 0.012799 |
| ret_10 | 1 | 0.017618 |
| ret_10 | 2 | 0.020238 |
| ret_10 | 3 | 0.019942 |
| ret_10 | 4 | 0.017194 |
| ret_10 | 5 | 0.008045 |
| ret_20 | 1 | 0.021740 |
| ret_20 | 2 | 0.020537 |
| ret_20 | 3 | 0.018672 |
| ret_20 | 4 | 0.015192 |
| ret_20 | 5 | 0.005626 |
| ret_5 | 1 | 0.016444 |
| ret_5 | 2 | 0.019210 |
| ret_5 | 3 | 0.019524 |
| ret_5 | 4 | 0.017527 |
| ret_5 | 5 | 0.010191 |
| rev_5 | 1 | 0.010194 |
| rev_5 | 2 | 0.017532 |
| rev_5 | 3 | 0.019516 |
| rev_5 | 4 | 0.019209 |
| rev_5 | 5 | 0.016442 |
| std_20 | 1 | 0.014317 |
| std_20 | 2 | 0.018503 |
| std_20 | 3 | 0.019463 |
| std_20 | 4 | 0.018812 |
| std_20 | 5 | 0.011476 |
| volume_ratio_5_20 | 1 | 0.014677 |
| volume_ratio_5_20 | 2 | 0.017397 |
| volume_ratio_5_20 | 3 | 0.019180 |
| volume_ratio_5_20 | 4 | 0.018687 |
| volume_ratio_5_20 | 5 | 0.012830 |

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
