# Factor Screening V3.3 Report

- Input directory: `E:\qlib_prj\qlib_baseline\outputs\factor_research_v3\liquid2000_core`
- Min portfolio directional Rank IC: `0.03`
- Min OOS directional Rank IC: `0.005`
- Min residual retention: `0.25`
- Exposure correlation threshold: `0.8`

## Status Counts

| status | count |
| --- | --- |
| research_candidate | 1 |
| risk_exposure | 2 |
| watch | 2 |

## Candidate Board

| factor | status | reason | main_directional_rank_ic | directional_rank_icir | oos_directional_rank_ic | slice_stability | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rev_5 | research_candidate | partial_signal_needs_more_validation | 0.019598 | 0.147822 | 0.035178 | 0.600000 | 0.937404 | log_amount_mean_20 | 0.171332 |
| amplitude_20 | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.109863 | 0.594628 | 0.075408 | 1.000000 | 0.045095 | volatility_bucket | 0.979796 |
| std_20 | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.094345 | 0.563278 | 0.068258 | 0.800000 | -0.062426 | amplitude_20 | 0.903193 |
| ret_20 | watch | direction_not_defined |  |  |  |  |  | std_20 | 0.253061 |
| amount_mean_20 | watch | direction_not_defined |  |  |  |  |  | log_amount_mean_20 | 1.000000 |

## Risk Exposure Diagnostics

| factor | reason | main_directional_rank_ic | joint_residual_directional_rank_ic | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | strong_raw_signal_but_exposure_dominated | 0.109863 | 0.004954 | 0.045095 | volatility_bucket | 0.979796 |
| std_20 | strong_raw_signal_but_exposure_dominated | 0.094345 | -0.005890 | -0.062426 | amplitude_20 | 0.903193 |

## Output Files

- `factor_candidate_board.csv`
- `factor_screening_report.md`
