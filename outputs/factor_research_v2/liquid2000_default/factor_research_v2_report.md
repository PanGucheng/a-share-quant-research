# Factor Research V2 Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Labels: `label_10d_t1,label_20d_t1`
- Quantiles: `5`
- Min count per daily IC bucket: `50`
- Tradable filter: `can_buy == true`, `liquidity_bucket >= 3`, `tradability_score >= 75.0`

## Windows

- `historical_reference_2010_2016`: `2010-01-01` to `2016-12-31`, raw only
- `baseline_alignment_2017_2020`: `2017-01-01` to `2020-08-01`, raw only
- `main_research_2021_2023`: `2021-01-01` to `2023-12-29`, tradability `outputs\tradability\all_stock_shsz_liquid2000_2021-01-01_2023-12-29`
- `recent_oos_2024_2026`: `2024-01-01` to `2026-06-09`, tradability `outputs\tradability\all_stock_shsz_liquid2000_2024-01-01_2026-06-09`

## Candidate Decisions

| label | factor | category | expected_direction | decision | reason | main_directional_rank_ic | oos_directional_rank_ic | stability_score | monotonicity_score | directional_spread | redundancy_group |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| label_10d_t1 | amplitude_20 | risk | negative | promote | passes_rules | 0.087936 | 0.068054 | 1.000000 | 0.800000 | 0.006657 |  |
| label_10d_t1 | std_20 | risk | negative | reject | passes_rules|redundant_weak | 0.078755 | 0.063243 | 1.000000 | 0.400000 | 0.005526 | amplitude_20 |
| label_10d_t1 | rev_5 | reversal | positive | watch | insufficient_evidence | 0.025876 | 0.034651 | 1.000000 | 0.400000 | 0.004162 |  |
| label_10d_t1 | ret_5 | momentum | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_10d_t1 | ret_10 | momentum | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_10d_t1 | ret_20 | momentum | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_10d_t1 | amount_mean_20 | liquidity | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_10d_t1 | amount_std_20 | liquidity | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_10d_t1 | volume_ratio_5_20 | liquidity | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_10d_t1 | corr_ret_volume_20 | price_volume | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | amplitude_20 | risk | negative | promote | passes_rules | 0.109863 | 0.075408 | 1.000000 | 1.000000 | 0.013217 |  |
| label_20d_t1 | std_20 | risk | negative | reject | passes_rules|redundant_weak | 0.094345 | 0.068258 | 1.000000 | 1.000000 | 0.010865 | amplitude_20 |
| label_20d_t1 | rev_5 | reversal | positive | watch | insufficient_evidence | 0.019598 | 0.035178 | 1.000000 | 0.400000 | 0.004507 |  |
| label_20d_t1 | ret_5 | momentum | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | ret_10 | momentum | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | ret_20 | momentum | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | amount_mean_20 | liquidity | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | amount_std_20 | liquidity | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | volume_ratio_5_20 | liquidity | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |
| label_20d_t1 | corr_ret_volume_20 | price_volume | watch | watch | watch_direction |  |  | 0.000000 |  |  |  |

## Decision Counts

| label | decision | count |
| --- | --- | --- |
| label_10d_t1 | promote | 1 |
| label_10d_t1 | reject | 1 |
| label_10d_t1 | watch | 8 |
| label_20d_t1 | promote | 1 |
| label_20d_t1 | reject | 1 |
| label_20d_t1 | watch | 8 |

## Promoted Factors

| label | factor | category | main_directional_rank_ic | oos_directional_rank_ic | stability_score | monotonicity_score | directional_spread |
| --- | --- | --- | --- | --- | --- | --- | --- |
| label_10d_t1 | amplitude_20 | risk | 0.087936 | 0.068054 | 1.000000 | 0.800000 | 0.006657 |
| label_20d_t1 | amplitude_20 | risk | 0.109863 | 0.075408 | 1.000000 | 1.000000 | 0.013217 |

## Watch Factors

| label | factor | category | reason | main_directional_rank_ic | oos_directional_rank_ic |
| --- | --- | --- | --- | --- | --- |
| label_10d_t1 | rev_5 | reversal | insufficient_evidence | 0.025876 | 0.034651 |
| label_10d_t1 | ret_5 | momentum | watch_direction |  |  |
| label_10d_t1 | ret_10 | momentum | watch_direction |  |  |
| label_10d_t1 | ret_20 | momentum | watch_direction |  |  |
| label_10d_t1 | amount_mean_20 | liquidity | watch_direction |  |  |
| label_10d_t1 | amount_std_20 | liquidity | watch_direction |  |  |
| label_10d_t1 | volume_ratio_5_20 | liquidity | watch_direction |  |  |
| label_10d_t1 | corr_ret_volume_20 | price_volume | watch_direction |  |  |
| label_20d_t1 | rev_5 | reversal | insufficient_evidence | 0.019598 | 0.035178 |
| label_20d_t1 | ret_5 | momentum | watch_direction |  |  |
| label_20d_t1 | ret_10 | momentum | watch_direction |  |  |
| label_20d_t1 | ret_20 | momentum | watch_direction |  |  |
| label_20d_t1 | amount_mean_20 | liquidity | watch_direction |  |  |
| label_20d_t1 | amount_std_20 | liquidity | watch_direction |  |  |
| label_20d_t1 | volume_ratio_5_20 | liquidity | watch_direction |  |  |
| label_20d_t1 | corr_ret_volume_20 | price_volume | watch_direction |  |  |

## Main Research Summary

| factor | category | expected_direction | coverage | mean_rank_ic | directional_mean_rank_ic | rank_icir | ic_dates |
| --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.990451 | -0.109863 | 0.109863 | -0.594628 | 726 |
| std_20 | risk | negative | 0.990084 | -0.094345 | 0.094345 | -0.563278 | 726 |
| rev_5 | reversal | positive | 0.996846 | 0.019598 | 0.019598 | 0.147822 | 726 |
| ret_5 | momentum | watch | 0.996846 | -0.019598 |  | -0.147822 | 726 |
| ret_10 | momentum | watch | 0.996289 | -0.034321 |  | -0.257372 | 726 |
| ret_20 | momentum | watch | 0.996261 | -0.058541 |  | -0.410103 | 726 |
| amount_mean_20 | liquidity | watch | 0.990451 | -0.098629 |  | -0.788295 | 726 |
| amount_std_20 | liquidity | watch | 0.990451 | -0.103426 |  | -0.910269 | 726 |
| volume_ratio_5_20 | liquidity | watch | 0.990451 | -0.005344 |  | -0.056716 | 726 |
| corr_ret_volume_20 | price_volume | watch | 0.990084 | -0.028685 |  | -0.328498 | 726 |

## Main Research Monotonicity

| factor | expected_direction | bottom_mean_label | top_mean_label | directional_spread | monotonicity_score |
| --- | --- | --- | --- | --- | --- |
| amplitude_20 | negative | 0.003591 | -0.009626 | 0.013217 | 1.000000 |
| std_20 | negative | 0.002134 | -0.008731 | 0.010865 | 1.000000 |
| rev_5 | positive | -0.005332 | -0.000825 | 0.004507 | 0.400000 |
| ret_5 | watch | -0.000828 | -0.005337 |  |  |
| ret_10 | watch | -0.000367 | -0.006266 |  |  |
| ret_20 | watch | 0.001293 | -0.007953 |  |  |
| amount_mean_20 | watch | 0.009717 | -0.012804 |  |  |
| amount_std_20 | watch | 0.009627 | -0.012709 |  |  |
| volume_ratio_5_20 | watch | -0.001319 | -0.000620 |  |  |
| corr_ret_volume_20 | watch | 0.001517 | -0.003185 |  |  |

## Output Files

- `factor_registry.csv`
- `factor_summary.csv`
- `factor_time_slice.csv`
- `factor_bucket_ic.csv`
- `factor_group_monotonicity.csv`
- `factor_correlation.csv`
- `factor_candidate_decision.csv`
- `factor_research_v2_report.md`

## Notes

- `promote` means the factor is ready for model feature-pool experiments, not ready for live trading.
- `watch` means the factor needs a clearer direction, richer neutralization, or more out-of-sample evidence.
- `reject` means the current evidence is weak or redundant under these rules.
- Diagnostic rows: summary `120`, monotonicity `40`, bucket IC `300`, correlation `180`.
