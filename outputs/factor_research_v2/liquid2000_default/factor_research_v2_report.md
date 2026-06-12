# Factor Research V2 Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Labels: `label_10d_t1,label_20d_t1`
- Quantiles: `5`
- Min count per daily IC bucket: `50`
- Tradable filter: `can_buy == true`, `liquidity_bucket >= 3`, `tradability_score >= 75.0`
- Data quality filter: exclude `severe` rows and `has_core_missing == true` when fields are available.

## Windows

- `historical_reference_2010_2016`: `2010-01-01` to `2016-12-31`, raw only
- `baseline_alignment_2017_2020`: `2017-01-01` to `2020-08-01`, raw only
- `main_research_2021_2023`: `2021-01-01` to `2023-12-29`, tradability `outputs\tradability\all_stock_shsz_liquid2000_2021-01-01_2023-12-29`
- `recent_oos_2024_2026`: `2024-01-01` to `2026-06-09`, tradability `outputs\tradability\all_stock_shsz_liquid2000_2024-01-01_2026-06-09`

## Candidate Decisions

| label | factor | category | expected_direction | decision | reason | main_directional_rank_ic | main_ic_win_rate | oos_directional_rank_ic | mean_top_quantile_turnover | stability_score | monotonicity_score | directional_spread | redundancy_group |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| label_10d_t1 | amplitude_20 | risk | negative | promote | passes_rules | 0.087936 | 0.668044 | 0.068054 | 0.111788 | 1.000000 | 0.800000 | 0.006657 |  |
| label_10d_t1 | std_20 | risk | negative | reject | passes_rules|redundant_weak | 0.078755 | 0.684573 | 0.063243 | 0.131858 | 1.000000 | 0.400000 | 0.005526 | amplitude_20 |
| label_10d_t1 | rev_5 | reversal | positive | watch | insufficient_evidence | 0.025876 | 0.546832 | 0.034651 | 0.391675 | 1.000000 | 0.400000 | 0.004162 |  |
| label_10d_t1 | ret_5 | momentum | watch | watch | watch_direction |  |  |  | 0.398817 | 0.000000 |  |  |  |
| label_10d_t1 | ret_10 | momentum | watch | watch | watch_direction |  |  |  | 0.302627 | 0.000000 |  |  |  |
| label_10d_t1 | ret_20 | momentum | watch | watch | watch_direction |  |  |  | 0.235862 | 0.000000 |  |  |  |
| label_10d_t1 | amount_mean_20 | liquidity | watch | watch | watch_direction |  |  |  | 0.042930 | 0.000000 |  |  |  |
| label_10d_t1 | amount_std_20 | liquidity | watch | watch | watch_direction |  |  |  | 0.065706 | 0.000000 |  |  |  |
| label_10d_t1 | volume_ratio_5_20 | liquidity | watch | watch | watch_direction |  |  |  | 0.265456 | 0.000000 |  |  |  |
| label_10d_t1 | corr_ret_volume_20 | price_volume | watch | watch | watch_direction |  |  |  | 0.237341 | 0.000000 |  |  |  |
| label_20d_t1 | amplitude_20 | risk | negative | promote | passes_rules | 0.109863 | 0.680441 | 0.075408 | 0.111788 | 1.000000 | 1.000000 | 0.013217 |  |
| label_20d_t1 | std_20 | risk | negative | reject | passes_rules|redundant_weak | 0.094345 | 0.687328 | 0.068258 | 0.131858 | 1.000000 | 1.000000 | 0.010865 | amplitude_20 |
| label_20d_t1 | rev_5 | reversal | positive | watch | insufficient_evidence | 0.019598 | 0.550964 | 0.035178 | 0.391675 | 1.000000 | 0.400000 | 0.004507 |  |
| label_20d_t1 | ret_5 | momentum | watch | watch | watch_direction |  |  |  | 0.398817 | 0.000000 |  |  |  |
| label_20d_t1 | ret_10 | momentum | watch | watch | watch_direction |  |  |  | 0.302627 | 0.000000 |  |  |  |
| label_20d_t1 | ret_20 | momentum | watch | watch | watch_direction |  |  |  | 0.235862 | 0.000000 |  |  |  |
| label_20d_t1 | amount_mean_20 | liquidity | watch | watch | watch_direction |  |  |  | 0.042930 | 0.000000 |  |  |  |
| label_20d_t1 | amount_std_20 | liquidity | watch | watch | watch_direction |  |  |  | 0.065706 | 0.000000 |  |  |  |
| label_20d_t1 | volume_ratio_5_20 | liquidity | watch | watch | watch_direction |  |  |  | 0.265456 | 0.000000 |  |  |  |
| label_20d_t1 | corr_ret_volume_20 | price_volume | watch | watch | watch_direction |  |  |  | 0.237341 | 0.000000 |  |  |  |

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

| label | factor | category | main_directional_rank_ic | main_ic_win_rate | oos_directional_rank_ic | mean_top_quantile_turnover | stability_score | monotonicity_score | directional_spread |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| label_10d_t1 | amplitude_20 | risk | 0.087936 | 0.668044 | 0.068054 | 0.111788 | 1.000000 | 0.800000 | 0.006657 |
| label_20d_t1 | amplitude_20 | risk | 0.109863 | 0.680441 | 0.075408 | 0.111788 | 1.000000 | 1.000000 | 0.013217 |

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

| factor | category | expected_direction | coverage | missing_rate | mean_rank_ic | directional_mean_rank_ic | rank_icir | ic_win_rate | ic_dates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk | negative | 0.990451 | 0.009549 | -0.109863 | 0.109863 | -0.594628 | 0.680441 | 726 |
| std_20 | risk | negative | 0.990084 | 0.009916 | -0.094345 | 0.094345 | -0.563278 | 0.687328 | 726 |
| rev_5 | reversal | positive | 0.996846 | 0.003154 | 0.019598 | 0.019598 | 0.147822 | 0.550964 | 726 |
| ret_5 | momentum | watch | 0.996846 | 0.003154 | -0.019598 |  | -0.147822 |  | 726 |
| ret_10 | momentum | watch | 0.996289 | 0.003711 | -0.034321 |  | -0.257372 |  | 726 |
| ret_20 | momentum | watch | 0.996261 | 0.003739 | -0.058541 |  | -0.410103 |  | 726 |
| amount_mean_20 | liquidity | watch | 0.990451 | 0.009549 | -0.098629 |  | -0.788295 |  | 726 |
| amount_std_20 | liquidity | watch | 0.990451 | 0.009549 | -0.103426 |  | -0.910269 |  | 726 |
| volume_ratio_5_20 | liquidity | watch | 0.990451 | 0.009549 | -0.005344 |  | -0.056716 |  | 726 |
| corr_ret_volume_20 | price_volume | watch | 0.990084 | 0.009916 | -0.028685 |  | -0.328498 |  | 726 |

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

## Main Research Group Returns

| factor | expected_direction | quantile | mean_group_return | std_group_return | group_return_dates |
| --- | --- | --- | --- | --- | --- |
| amount_mean_20 | watch | 1 | 0.009717 | 0.051138 | 726 |
| amount_mean_20 | watch | 2 | 0.004666 | 0.051392 | 726 |
| amount_mean_20 | watch | 3 | -0.000470 | 0.051052 | 726 |
| amount_mean_20 | watch | 4 | -0.005074 | 0.050834 | 726 |
| amount_mean_20 | watch | 5 | -0.012804 | 0.054965 | 726 |
| amount_std_20 | watch | 1 | 0.009627 | 0.051474 | 726 |
| amount_std_20 | watch | 2 | 0.003575 | 0.050156 | 726 |
| amount_std_20 | watch | 3 | 0.000702 | 0.050530 | 726 |
| amount_std_20 | watch | 4 | -0.005157 | 0.051304 | 726 |
| amount_std_20 | watch | 5 | -0.012709 | 0.054124 | 726 |
| amplitude_20 | negative | 1 | 0.003591 | 0.041527 | 726 |
| amplitude_20 | negative | 2 | 0.001607 | 0.048207 | 726 |
| amplitude_20 | negative | 3 | 0.000897 | 0.052768 | 726 |
| amplitude_20 | negative | 4 | -0.000420 | 0.057999 | 726 |
| amplitude_20 | negative | 5 | -0.009626 | 0.065541 | 726 |
| corr_ret_volume_20 | watch | 1 | 0.001517 | 0.047194 | 726 |
| corr_ret_volume_20 | watch | 2 | 0.001230 | 0.051065 | 726 |
| corr_ret_volume_20 | watch | 3 | -0.000336 | 0.053016 | 726 |
| corr_ret_volume_20 | watch | 4 | -0.003196 | 0.051790 | 726 |
| corr_ret_volume_20 | watch | 5 | -0.003185 | 0.051556 | 726 |
| ret_10 | watch | 1 | -0.000367 | 0.053958 | 726 |
| ret_10 | watch | 2 | 0.000520 | 0.050298 | 726 |
| ret_10 | watch | 3 | 0.000927 | 0.048844 | 726 |
| ret_10 | watch | 4 | 0.001029 | 0.050866 | 726 |
| ret_10 | watch | 5 | -0.006266 | 0.056519 | 726 |
| ret_20 | watch | 1 | 0.001293 | 0.054142 | 726 |
| ret_20 | watch | 2 | 0.000545 | 0.049855 | 726 |
| ret_20 | watch | 3 | 0.001222 | 0.049582 | 726 |
| ret_20 | watch | 4 | 0.000626 | 0.051294 | 726 |
| ret_20 | watch | 5 | -0.007953 | 0.057801 | 726 |
| ret_5 | watch | 1 | -0.000828 | 0.055790 | 726 |
| ret_5 | watch | 2 | -0.000333 | 0.050955 | 726 |
| ret_5 | watch | 3 | 0.001211 | 0.048659 | 726 |
| ret_5 | watch | 4 | 0.001131 | 0.050049 | 726 |
| ret_5 | watch | 5 | -0.005337 | 0.054812 | 726 |
| rev_5 | positive | 1 | -0.005332 | 0.054787 | 726 |
| rev_5 | positive | 2 | 0.001137 | 0.050042 | 726 |
| rev_5 | positive | 3 | 0.001220 | 0.048670 | 726 |
| rev_5 | positive | 4 | -0.000360 | 0.050953 | 726 |
| rev_5 | positive | 5 | -0.000825 | 0.055797 | 726 |
| std_20 | negative | 1 | 0.002134 | 0.041704 | 726 |
| std_20 | negative | 2 | 0.001520 | 0.048725 | 726 |
| std_20 | negative | 3 | 0.000811 | 0.052818 | 726 |
| std_20 | negative | 4 | 0.000308 | 0.057670 | 726 |
| std_20 | negative | 5 | -0.008731 | 0.062448 | 726 |
| volume_ratio_5_20 | watch | 1 | -0.001319 | 0.050570 | 726 |
| volume_ratio_5_20 | watch | 2 | -0.001044 | 0.049265 | 726 |
| volume_ratio_5_20 | watch | 3 | -0.000943 | 0.049669 | 726 |
| volume_ratio_5_20 | watch | 4 | -0.000033 | 0.051022 | 726 |
| volume_ratio_5_20 | watch | 5 | -0.000620 | 0.054449 | 726 |

## Main Research Turnover

| factor | category | expected_direction | mean_top_quantile_turnover | median_top_quantile_turnover | turnover_dates |
| --- | --- | --- | --- | --- | --- |
| amount_mean_20 | liquidity | watch | 0.042930 | 0.040179 | 725 |
| amount_std_20 | liquidity | watch | 0.065706 | 0.062222 | 725 |
| amplitude_20 | risk | negative | 0.111788 | 0.110619 | 725 |
| corr_ret_volume_20 | price_volume | watch | 0.237341 | 0.231111 | 725 |
| ret_10 | momentum | watch | 0.302627 | 0.302222 | 725 |
| ret_20 | momentum | watch | 0.235862 | 0.233480 | 725 |
| ret_5 | momentum | watch | 0.398817 | 0.395652 | 725 |
| rev_5 | reversal | positive | 0.391675 | 0.388646 | 725 |
| std_20 | risk | negative | 0.131858 | 0.129464 | 725 |
| volume_ratio_5_20 | liquidity | watch | 0.265456 | 0.264574 | 725 |

## Output Files

- `factor_registry.csv`
- `factor_summary.csv`
- `factor_time_slice.csv`
- `factor_bucket_ic.csv`
- `factor_group_return.csv`
- `factor_group_return_summary.csv`
- `factor_group_monotonicity.csv`
- `factor_correlation.csv`
- `factor_candidate_decision.csv`
- `factor_missing_coverage.csv`
- `factor_turnover.csv`
- `factor_turnover_summary.csv`
- `factor_data_schema.md`
- `factor_research_v2_report.md`

## Notes

- `promote` means the factor is ready for model feature-pool experiments, not ready for live trading.
- `watch` means the factor needs a clearer direction, richer neutralization, or more out-of-sample evidence.
- `reject` means the current evidence is weak or redundant under these rules.
- Diagnostic rows: summary `120`, monotonicity `40`, bucket IC `300`, group returns `200`, correlation `180`, coverage `40`.
