# Factor Screening V3.3 Report

- Input directory: `E:\qlib_prj\qlib_baseline\outputs\factor_research_v3\liquid2000_expanded`
- Min portfolio directional Rank IC: `0.03`
- Min OOS directional Rank IC: `0.005`
- Min residual retention: `0.25`
- Exposure correlation threshold: `0.8`

## Status Counts

| status | count |
| --- | --- |
| research_candidate | 2 |
| risk_exposure | 3 |
| watch | 5 |

## Candidate Board

| factor | status | reason | main_directional_rank_ic | directional_rank_icir | oos_directional_rank_ic | slice_stability | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rev_20_exclude_5 | research_candidate | partial_signal_needs_more_validation | 0.053765 | 0.397930 | 0.059016 | 1.000000 | 0.178590 | std_20 | 0.267665 |
| rev_5 | research_candidate | partial_signal_needs_more_validation | 0.019598 | 0.147822 | 0.035178 | 0.600000 | 0.937404 | log_amount_mean_20 | 0.171332 |
| amplitude_20 | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.109863 | 0.594628 | 0.075408 | 1.000000 | 0.045095 | volatility_bucket | 0.979796 |
| std_20 | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.094345 | 0.563278 | 0.068258 | 0.800000 | -0.062426 | amplitude_20 | 0.903193 |
| downside_std_20 | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.065157 | 0.410552 | 0.052494 | 0.666667 | -0.410751 | std_20 | 0.816805 |
| max_drawdown_20 | watch | signal_flips_after_controls | 0.030714 | 0.221064 | 0.025261 | 0.600000 | -1.131679 | std_20 | 0.559589 |
| amount_cv_20 | watch | insufficient_evidence | 0.019981 | 0.203076 | 0.064393 | 0.733333 | 0.286263 | std_20 | 0.389458 |
| ret_20 | watch | direction_not_defined |  |  |  |  |  | std_20 | 0.253061 |
| amount_mean_20 | watch | direction_not_defined |  |  |  |  |  | log_amount_mean_20 | 1.000000 |
| corr_ret_amount_20 | watch | direction_not_defined |  |  |  |  |  | amplitude_20 | 0.121127 |

## Risk Exposure Diagnostics

| factor | reason | main_directional_rank_ic | joint_residual_directional_rank_ic | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | strong_raw_signal_but_exposure_dominated | 0.109863 | 0.004954 | 0.045095 | volatility_bucket | 0.979796 |
| std_20 | strong_raw_signal_but_exposure_dominated | 0.094345 | -0.005890 | -0.062426 | amplitude_20 | 0.903193 |
| downside_std_20 | strong_raw_signal_but_exposure_dominated | 0.065157 | -0.026763 | -0.410751 | std_20 | 0.816805 |

## Output Files

- `factor_candidate_board.csv`
- `factor_screening_report.md`
