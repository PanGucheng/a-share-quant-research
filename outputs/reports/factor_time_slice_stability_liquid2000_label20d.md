# Factor Time Slice Stability

## Stability Summary

| factor | category | expected_direction | slice_count | positive_directional_slices | mean_directional_rank_ic | min_directional_rank_ic | mean_abs_rank_ic | latest_rank_ic | latest_directional_rank_ic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 4 | 4 | 0.0758637997854395 | 0.0511235305671605 | 0.075864 | -0.051124 | 0.051124 |
| std_20 | risk | negative | 4 | 4 | 0.07161850846337275 | 0.0537867812788723 | 0.071619 | -0.053787 | 0.053787 |
| rev_5 | reversal | positive | 4 | 4 | 0.030789487118944 | 0.0238927901940687 | 0.030789 | 0.040805 | 0.040805 |
| amount_mean_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.097908 | -0.081975 |  |
| amount_std_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.108366 | -0.092683 |  |
| corr_ret_volume_20 | price_volume | watch | 4 | 0 | <NA> | <NA> | 0.031941 | -0.006012 |  |
| ret_10 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.045914 | -0.056839 |  |
| ret_20 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.067265 | -0.079541 |  |
| ret_5 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.030789 | -0.040805 |  |
| volume_ratio_5_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.024060 | -0.037255 |  |

## Slice Details

| slice | factor | category | expected_direction | coverage | mean_rank_ic | directional_mean_rank_ic | rank_icir |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_alignment_2017_2020 | amplitude_20 | risk | negative | 0.888484 | -0.081247 | 0.081247 | -0.525696 |
| baseline_alignment_2017_2020 | std_20 | risk | negative | 0.886342 | -0.075653 | 0.075653 | -0.498810 |
| baseline_alignment_2017_2020 | rev_5 | reversal | positive | 0.920484 | 0.026217 | 0.026217 | 0.206832 |
| baseline_alignment_2017_2020 | ret_20 | momentum | watch | 0.898444 | -0.055827 |  | -0.375476 |
| baseline_alignment_2017_2020 | amount_std_20 | liquidity | watch | 0.888484 | -0.049600 |  | -0.337376 |
| baseline_alignment_2017_2020 | ret_10 | momentum | watch | 0.912362 | -0.044585 |  | -0.315021 |
| baseline_alignment_2017_2020 | corr_ret_volume_20 | price_volume | watch | 0.886342 | -0.032429 |  | -0.367129 |
| baseline_alignment_2017_2020 | volume_ratio_5_20 | liquidity | watch | 0.888484 | -0.027232 |  | -0.292759 |
| baseline_alignment_2017_2020 | amount_mean_20 | liquidity | watch | 0.888484 | -0.026338 |  | -0.168464 |
| baseline_alignment_2017_2020 | ret_5 | momentum | watch | 0.920484 | -0.026217 |  | -0.206832 |
| historical_reference_2010_2016 | amplitude_20 | risk | negative | 0.771104 | -0.060883 | 0.060883 | -0.322193 |
| historical_reference_2010_2016 | std_20 | risk | negative | 0.765253 | -0.054968 | 0.054968 | -0.297503 |
| historical_reference_2010_2016 | rev_5 | reversal | positive | 0.877052 | 0.032244 | 0.032244 | 0.233556 |
| historical_reference_2010_2016 | amount_std_20 | liquidity | watch | 0.771104 | -0.141493 |  | -0.958807 |
| historical_reference_2010_2016 | amount_mean_20 | liquidity | watch | 0.771104 | -0.134537 |  | -0.864187 |
| historical_reference_2010_2016 | ret_20 | momentum | watch | 0.855661 | -0.072637 |  | -0.450437 |
| historical_reference_2010_2016 | corr_ret_volume_20 | price_volume | watch | 0.765253 | -0.044167 |  | -0.446077 |
| historical_reference_2010_2016 | ret_10 | momentum | watch | 0.868847 | -0.043588 |  | -0.293240 |
| historical_reference_2010_2016 | ret_5 | momentum | watch | 0.877052 | -0.032244 |  | -0.233556 |
| historical_reference_2010_2016 | volume_ratio_5_20 | liquidity | watch | 0.771104 | -0.008894 |  | -0.083517 |
| main_research_2021_2023 | amplitude_20 | risk | negative | 0.930317 | -0.110202 | 0.110202 | -0.652737 |
| main_research_2021_2023 | std_20 | risk | negative | 0.928519 | -0.102066 | 0.102066 | -0.666263 |
| main_research_2021_2023 | rev_5 | reversal | positive | 0.956737 | 0.023893 | 0.023893 | 0.190979 |
| main_research_2021_2023 | amount_std_20 | liquidity | watch | 0.930317 | -0.149689 |  | -1.093560 |
| main_research_2021_2023 | amount_mean_20 | liquidity | watch | 0.930317 | -0.148783 |  | -1.021089 |
| main_research_2021_2023 | ret_20 | momentum | watch | 0.935487 | -0.061054 |  | -0.435218 |
| main_research_2021_2023 | corr_ret_volume_20 | price_volume | watch | 0.928519 | -0.045155 |  | -0.517990 |
| main_research_2021_2023 | ret_10 | momentum | watch | 0.949410 | -0.038644 |  | -0.300472 |
| main_research_2021_2023 | ret_5 | momentum | watch | 0.956737 | -0.023893 |  | -0.190979 |
| main_research_2021_2023 | volume_ratio_5_20 | liquidity | watch | 0.930317 | -0.022859 |  | -0.267264 |
| recent_oos_2024_2026 | std_20 | risk | negative | 0.916840 | -0.053787 | 0.053787 | -0.236458 |
| recent_oos_2024_2026 | amplitude_20 | risk | negative | 0.918917 | -0.051124 | 0.051124 | -0.213414 |
| recent_oos_2024_2026 | rev_5 | reversal | positive | 0.949394 | 0.040805 | 0.040805 | 0.267109 |
| recent_oos_2024_2026 | amount_std_20 | liquidity | watch | 0.918917 | -0.092683 |  | -0.509807 |
| recent_oos_2024_2026 | amount_mean_20 | liquidity | watch | 0.918917 | -0.081975 |  | -0.417156 |
| recent_oos_2024_2026 | ret_20 | momentum | watch | 0.923007 | -0.079541 |  | -0.474521 |
| recent_oos_2024_2026 | ret_10 | momentum | watch | 0.940371 | -0.056839 |  | -0.372034 |
| recent_oos_2024_2026 | ret_5 | momentum | watch | 0.949394 | -0.040805 |  | -0.267109 |
| recent_oos_2024_2026 | volume_ratio_5_20 | liquidity | watch | 0.918917 | -0.037255 |  | -0.375094 |
| recent_oos_2024_2026 | corr_ret_volume_20 | price_volume | watch | 0.916840 | -0.006012 |  | -0.066176 |

## Interpretation Guide

- `2010-2016` is historical reference, not the main training target.
- `2017-2020` is baseline alignment for earlier Qlib-style experiments.
- `2021-2023` should become the main research window.
- `2024-2026` is recent out-of-sample and should be touched lightly to avoid overfitting.
