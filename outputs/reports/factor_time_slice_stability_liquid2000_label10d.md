# Factor Time Slice Stability

## Stability Summary

| factor | category | expected_direction | slice_count | positive_directional_slices | mean_directional_rank_ic | min_directional_rank_ic | mean_abs_rank_ic | latest_rank_ic | latest_directional_rank_ic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 4 | 4 | 0.06501434266848723 | 0.0450890719677199 | 0.065014 | -0.045089 | 0.045089 |
| std_20 | risk | negative | 4 | 4 | 0.0623951949553938 | 0.0445271235251814 | 0.062395 | -0.047369 | 0.047369 |
| rev_5 | reversal | positive | 4 | 4 | 0.028299021601183777 | 0.0204481240722206 | 0.028299 | 0.034178 | 0.034178 |
| amount_mean_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.079484 | -0.067974 |  |
| amount_std_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.091439 | -0.080533 |  |
| corr_ret_volume_20 | price_volume | watch | 4 | 0 | <NA> | <NA> | 0.029823 | -0.018876 |  |
| ret_10 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.036242 | -0.043170 |  |
| ret_20 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.058240 | -0.074818 |  |
| ret_5 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.028299 | -0.034178 |  |
| volume_ratio_5_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.021191 | -0.040647 |  |

## Slice Details

| slice | factor | category | expected_direction | coverage | mean_rank_ic | directional_mean_rank_ic | rank_icir |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_alignment_2017_2020 | amplitude_20 | risk | negative | 0.902177 | -0.073049 | 0.073049 | -0.452742 |
| baseline_alignment_2017_2020 | std_20 | risk | negative | 0.900015 | -0.069266 | 0.069266 | -0.444184 |
| baseline_alignment_2017_2020 | rev_5 | reversal | positive | 0.934759 | 0.020448 | 0.020448 | 0.163526 |
| baseline_alignment_2017_2020 | ret_20 | momentum | watch | 0.912413 | -0.055492 |  | -0.369746 |
| baseline_alignment_2017_2020 | amount_std_20 | liquidity | watch | 0.902177 | -0.052199 |  | -0.369600 |
| baseline_alignment_2017_2020 | ret_10 | momentum | watch | 0.926495 | -0.035874 |  | -0.259996 |
| baseline_alignment_2017_2020 | amount_mean_20 | liquidity | watch | 0.902177 | -0.031122 |  | -0.208566 |
| baseline_alignment_2017_2020 | corr_ret_volume_20 | price_volume | watch | 0.900015 | -0.028245 |  | -0.311589 |
| baseline_alignment_2017_2020 | volume_ratio_5_20 | liquidity | watch | 0.902177 | -0.022372 |  | -0.232927 |
| baseline_alignment_2017_2020 | ret_5 | momentum | watch | 0.934759 | -0.020448 |  | -0.163526 |
| historical_reference_2010_2016 | amplitude_20 | risk | negative | 0.783678 | -0.048624 | 0.048624 | -0.257997 |
| historical_reference_2010_2016 | std_20 | risk | negative | 0.777777 | -0.044527 | 0.044527 | -0.246495 |
| historical_reference_2010_2016 | rev_5 | reversal | positive | 0.890625 | 0.031325 | 0.031325 | 0.220607 |
| historical_reference_2010_2016 | amount_std_20 | liquidity | watch | 0.783678 | -0.116112 |  | -0.855738 |
| historical_reference_2010_2016 | amount_mean_20 | liquidity | watch | 0.783678 | -0.105932 |  | -0.747328 |
| historical_reference_2010_2016 | ret_20 | momentum | watch | 0.868920 | -0.057652 |  | -0.366862 |
| historical_reference_2010_2016 | corr_ret_volume_20 | price_volume | watch | 0.777777 | -0.037565 |  | -0.379559 |
| historical_reference_2010_2016 | ret_10 | momentum | watch | 0.882293 | -0.032657 |  | -0.218169 |
| historical_reference_2010_2016 | ret_5 | momentum | watch | 0.890625 | -0.031325 |  | -0.220607 |
| historical_reference_2010_2016 | volume_ratio_5_20 | liquidity | watch | 0.783678 | -0.004976 |  | -0.047552 |
| main_research_2021_2023 | amplitude_20 | risk | negative | 0.944100 | -0.093295 | 0.093295 | -0.566367 |
| main_research_2021_2023 | std_20 | risk | negative | 0.942299 | -0.088418 | 0.088418 | -0.595008 |
| main_research_2021_2023 | rev_5 | reversal | positive | 0.970729 | 0.027245 | 0.027245 | 0.214463 |
| main_research_2021_2023 | amount_std_20 | liquidity | watch | 0.944100 | -0.116914 |  | -0.821989 |
| main_research_2021_2023 | amount_mean_20 | liquidity | watch | 0.944100 | -0.112909 |  | -0.740452 |
| main_research_2021_2023 | ret_20 | momentum | watch | 0.949424 | -0.044998 |  | -0.324274 |
| main_research_2021_2023 | corr_ret_volume_20 | price_volume | watch | 0.942299 | -0.034607 |  | -0.431134 |
| main_research_2021_2023 | ret_10 | momentum | watch | 0.963390 | -0.033268 |  | -0.261007 |
| main_research_2021_2023 | ret_5 | momentum | watch | 0.970729 | -0.027245 |  | -0.214463 |
| main_research_2021_2023 | volume_ratio_5_20 | liquidity | watch | 0.944100 | -0.016768 |  | -0.191871 |
| recent_oos_2024_2026 | std_20 | risk | negative | 0.933433 | -0.047369 | 0.047369 | -0.216977 |
| recent_oos_2024_2026 | amplitude_20 | risk | negative | 0.935525 | -0.045089 | 0.045089 | -0.195627 |
| recent_oos_2024_2026 | rev_5 | reversal | positive | 0.966765 | 0.034178 | 0.034178 | 0.223850 |
| recent_oos_2024_2026 | amount_std_20 | liquidity | watch | 0.935525 | -0.080533 |  | -0.461115 |
| recent_oos_2024_2026 | ret_20 | momentum | watch | 0.940354 | -0.074818 |  | -0.474648 |
| recent_oos_2024_2026 | amount_mean_20 | liquidity | watch | 0.935525 | -0.067974 |  | -0.355399 |
| recent_oos_2024_2026 | ret_10 | momentum | watch | 0.957689 | -0.043170 |  | -0.274011 |
| recent_oos_2024_2026 | volume_ratio_5_20 | liquidity | watch | 0.935525 | -0.040647 |  | -0.442011 |
| recent_oos_2024_2026 | ret_5 | momentum | watch | 0.966765 | -0.034178 |  | -0.223850 |
| recent_oos_2024_2026 | corr_ret_volume_20 | price_volume | watch | 0.933433 | -0.018876 |  | -0.210971 |

## Interpretation Guide

- `2010-2016` is historical reference, not the main training target.
- `2017-2020` is baseline alignment for earlier Qlib-style experiments.
- `2021-2023` should become the main research window.
- `2024-2026` is recent out-of-sample and should be touched lightly to avoid overfitting.
