# Factor Time Slice Stability

## Stability Summary

| factor | category | expected_direction | slice_count | positive_directional_slices | mean_directional_rank_ic | min_directional_rank_ic | mean_abs_rank_ic | latest_rank_ic | latest_directional_rank_ic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 4 | 4 | 0.03946913355143182 | 0.0239170868489983 | 0.039469 | -0.038382 | 0.038382 |
| std_20 | risk | negative | 4 | 4 | 0.0370234350651404 | 0.0187753375034852 | 0.037023 | -0.039549 | 0.039549 |
| rev_5 | reversal | positive | 4 | 4 | 0.036709072116455424 | 0.0229545609533246 | 0.036709 | 0.025411 | 0.025411 |
| amount_mean_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.035754 | -0.035369 |  |
| amount_std_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.044144 | -0.044874 |  |
| corr_ret_volume_20 | price_volume | watch | 4 | 0 | <NA> | <NA> | 0.021713 | -0.020260 |  |
| ret_10 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.033185 | -0.030530 |  |
| ret_20 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.035795 | -0.038603 |  |
| ret_5 | momentum | watch | 4 | 0 | <NA> | <NA> | 0.036709 | -0.025411 |  |
| volume_ratio_5_20 | liquidity | watch | 4 | 0 | <NA> | <NA> | 0.024159 | -0.029159 |  |

## Slice Details

| slice | factor | category | expected_direction | coverage | mean_rank_ic | directional_mean_rank_ic | rank_icir |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_alignment_2017_2020 | amplitude_20 | risk | negative | 0.917698 | -0.038912 | 0.038912 | -0.221254 |
| baseline_alignment_2017_2020 | std_20 | risk | negative | 0.915476 | -0.036701 | 0.036701 | -0.213982 |
| baseline_alignment_2017_2020 | rev_5 | reversal | positive | 0.950865 | 0.035087 | 0.035087 | 0.256763 |
| baseline_alignment_2017_2020 | ret_5 | momentum | watch | 0.950865 | -0.035087 |  | -0.256763 |
| baseline_alignment_2017_2020 | ret_20 | momentum | watch | 0.928107 | -0.034431 |  | -0.236890 |
| baseline_alignment_2017_2020 | ret_10 | momentum | watch | 0.942466 | -0.032329 |  | -0.226800 |
| baseline_alignment_2017_2020 | amount_std_20 | liquidity | watch | 0.917698 | -0.029473 |  | -0.233094 |
| baseline_alignment_2017_2020 | volume_ratio_5_20 | liquidity | watch | 0.917698 | -0.024427 |  | -0.258236 |
| baseline_alignment_2017_2020 | corr_ret_volume_20 | price_volume | watch | 0.915476 | -0.020126 |  | -0.231690 |
| baseline_alignment_2017_2020 | amount_mean_20 | liquidity | watch | 0.917698 | -0.017891 |  | -0.137948 |
| historical_reference_2010_2016 | rev_5 | reversal | positive | 0.909128 | 0.063384 | 0.063384 | 0.425490 |
| historical_reference_2010_2016 | amplitude_20 | risk | negative | 0.800714 | -0.023917 | 0.023917 | -0.129179 |
| historical_reference_2010_2016 | std_20 | risk | negative | 0.794730 | -0.018775 | 0.018775 | -0.103556 |
| historical_reference_2010_2016 | ret_5 | momentum | watch | 0.909128 | -0.063384 |  | -0.425490 |
| historical_reference_2010_2016 | amount_std_20 | liquidity | watch | 0.800714 | -0.047308 |  | -0.428959 |
| historical_reference_2010_2016 | ret_10 | momentum | watch | 0.900715 | -0.046156 |  | -0.292991 |
| historical_reference_2010_2016 | ret_20 | momentum | watch | 0.887116 | -0.042950 |  | -0.263776 |
| historical_reference_2010_2016 | amount_mean_20 | liquidity | watch | 0.800714 | -0.039648 |  | -0.352453 |
| historical_reference_2010_2016 | corr_ret_volume_20 | price_volume | watch | 0.794730 | -0.023972 |  | -0.247262 |
| historical_reference_2010_2016 | volume_ratio_5_20 | liquidity | watch | 0.800714 | -0.022863 |  | -0.212887 |
| main_research_2021_2023 | amplitude_20 | risk | negative | 0.957495 | -0.056665 | 0.056665 | -0.330346 |
| main_research_2021_2023 | std_20 | risk | negative | 0.955676 | -0.053068 | 0.053068 | -0.341862 |
| main_research_2021_2023 | rev_5 | reversal | positive | 0.984502 | 0.022955 | 0.022955 | 0.158646 |
| main_research_2021_2023 | amount_std_20 | liquidity | watch | 0.957495 | -0.054920 |  | -0.381521 |
| main_research_2021_2023 | amount_mean_20 | liquidity | watch | 0.957495 | -0.050109 |  | -0.323093 |
| main_research_2021_2023 | ret_20 | momentum | watch | 0.962938 | -0.027197 |  | -0.170708 |
| main_research_2021_2023 | ret_10 | momentum | watch | 0.977009 | -0.023723 |  | -0.161821 |
| main_research_2021_2023 | ret_5 | momentum | watch | 0.984502 | -0.022955 |  | -0.158646 |
| main_research_2021_2023 | corr_ret_volume_20 | price_volume | watch | 0.955676 | -0.022496 |  | -0.268601 |
| main_research_2021_2023 | volume_ratio_5_20 | liquidity | watch | 0.957495 | -0.020185 |  | -0.201369 |
| recent_oos_2024_2026 | std_20 | risk | negative | 0.949605 | -0.039549 | 0.039549 | -0.170010 |
| recent_oos_2024_2026 | amplitude_20 | risk | negative | 0.951765 | -0.038382 | 0.038382 | -0.159900 |
| recent_oos_2024_2026 | rev_5 | reversal | positive | 0.983463 | 0.025411 | 0.025411 | 0.137395 |
| recent_oos_2024_2026 | amount_std_20 | liquidity | watch | 0.951765 | -0.044874 |  | -0.250312 |
| recent_oos_2024_2026 | ret_20 | momentum | watch | 0.956855 | -0.038603 |  | -0.208456 |
| recent_oos_2024_2026 | amount_mean_20 | liquidity | watch | 0.951765 | -0.035369 |  | -0.182913 |
| recent_oos_2024_2026 | ret_10 | momentum | watch | 0.974300 | -0.030530 |  | -0.169726 |
| recent_oos_2024_2026 | volume_ratio_5_20 | liquidity | watch | 0.951765 | -0.029159 |  | -0.264656 |
| recent_oos_2024_2026 | ret_5 | momentum | watch | 0.983463 | -0.025411 |  | -0.137395 |
| recent_oos_2024_2026 | corr_ret_volume_20 | price_volume | watch | 0.949605 | -0.020260 |  | -0.201302 |

## Interpretation Guide

- `2010-2016` is historical reference, not the main training target.
- `2017-2020` is baseline alignment for earlier Qlib-style experiments.
- `2021-2023` should become the main research window.
- `2024-2026` is recent out-of-sample and should be touched lightly to avoid overfitting.
