# Factor Candidate Pool V3 Report

- Pool name: `liquid2000_expanded_v3_5`
- Label: `label_20d_t1`
- Source board: `E:\qlib_prj\qlib_baseline\outputs\factor_screening_v3\liquid2000_expanded\factor_candidate_board.csv`

## Role Counts

| role | count |
| --- | --- |
| alpha_candidate | 2 |
| monitor | 5 |
| risk_control | 3 |

## Alpha Candidates

| factor | role | status | reason | main_directional_rank_ic | oos_directional_rank_ic | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rev_20_exclude_5 | alpha_candidate | research_candidate | partial_signal_needs_more_validation | 0.053765 | 0.059016 | 0.178590 | std_20 | 0.267665 |
| rev_5 | alpha_candidate | research_candidate | partial_signal_needs_more_validation | 0.019598 | 0.035178 | 0.937404 | log_amount_mean_20 | 0.171332 |

## Risk Controls

| factor | role | status | reason | main_directional_rank_ic | oos_directional_rank_ic | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | risk_control | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.109863 | 0.075408 | 0.045095 | volatility_bucket | 0.979796 |
| std_20 | risk_control | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.094345 | 0.068258 | -0.062426 | amplitude_20 | 0.903193 |
| downside_std_20 | risk_control | risk_exposure | strong_raw_signal_but_exposure_dominated | 0.065157 | 0.052494 | -0.410751 | std_20 | 0.816805 |

## Monitor List

| factor | role | status | reason | main_directional_rank_ic | oos_directional_rank_ic | residual_retention | dominant_exposure | dominant_exposure_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| max_drawdown_20 | monitor | watch | signal_flips_after_controls | 0.030714 | 0.025261 | -1.131679 | std_20 | 0.559589 |
| amount_cv_20 | monitor | watch | insufficient_evidence | 0.019981 | 0.064393 | 0.286263 | std_20 | 0.389458 |
| ret_20 | monitor | watch | direction_not_defined |  |  |  | std_20 | 0.253061 |
| amount_mean_20 | monitor | watch | direction_not_defined |  |  |  | log_amount_mean_20 | 1.000000 |
| corr_ret_amount_20 | monitor | watch | direction_not_defined |  |  |  | amplitude_20 | 0.121127 |

## Output Files

- `factor_candidate_pool.csv`
- `factor_candidate_pool.json`
- `factor_candidate_pool_report.md`
