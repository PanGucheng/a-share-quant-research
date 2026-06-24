# Alpha158 Full Screening Input V1

This report builds a screening input layer from existing Alpha158 evaluation outputs.
It does not create a custom combined score and does not train a model.

## Output Rows

- Metric index rows: `33148`
- Factor board rows: `158`
- IC summary rows: `948`
- Quantile return summary rows: `632`
- Turnover summary rows: `624`
- Rank autocorrelation summary rows: `474`
- Context IC summary rows: `1264`
- Context return summary rows: `5056`

## Evaluation Gate

| evaluation_gate | count |
| --- | --- |
| holdout | 3 |
| strict_screening_input | 155 |

## Evaluator Status Combinations

| alphalens_status | jqfactor_status | qlib_status | count |
| --- | --- | --- | --- |
| partial_pass | partial_pass | pass | 3 |
| pass | partial_pass | pass | 155 |

## Holdouts

| factor | category | holdout_reason | failure_steps |
| --- | --- | --- | --- |
| alpha158_CNTN5 | alpha158_price_momentum_balance | alphalens=partial_pass | factor_alpha_beta,factor_returns,quantile_turnover |
| alpha158_IMAX5 | alpha158_rolling_price | alphalens=partial_pass | factor_alpha_beta,factor_returns,quantile_turnover |
| alpha158_RANK5 | alpha158_rolling_price | alphalens=partial_pass | factor_alpha_beta,factor_returns,quantile_turnover |

## Top Absolute Rank IC Snapshot

| factor | category | evaluation_gate | metric | rank_ic |
| --- | --- | --- | --- | --- |
| alpha158_MIN60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | 0.099945 |
| alpha158_MIN60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | 0.099945 |
| alpha158_MIN60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | 0.099681 |
| alpha158_QTLD60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | 0.097826 |
| alpha158_QTLD60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | 0.097826 |
| alpha158_QTLD60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | 0.097581 |
| alpha158_MA60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | 0.086939 |
| alpha158_MA60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | 0.086939 |
| alpha158_MA60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | 0.086714 |
| alpha158_ROC60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | 0.083509 |
| alpha158_ROC60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | 0.083509 |
| alpha158_ROC60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | 0.083354 |
| alpha158_MIN30 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | 0.083258 |
| alpha158_MIN30 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | 0.083258 |
| alpha158_MIN30 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | 0.082977 |
| alpha158_BETA60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | -0.081700 |
| alpha158_BETA60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | -0.081700 |
| alpha158_BETA60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | -0.081528 |
| alpha158_ROC30 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_20d | 0.080597 |
| alpha158_ROC30 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_20d | 0.080597 |
| alpha158_ROC30 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_20d | 0.080334 |
| alpha158_MIN60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_10d | 0.080316 |
| alpha158_MIN60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_10d | 0.080316 |
| alpha158_MIN60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_10d | 0.080016 |
| alpha158_KLEN | alpha158_kbar | strict_screening_input | jqfactor_rank_ic_20d | -0.077333 |
| alpha158_KLEN | alpha158_kbar | strict_screening_input | alphalens_rank_ic_20d | -0.077333 |
| alpha158_KLEN | alpha158_kbar | strict_screening_input | qlib_rank_ic_20d | -0.077244 |
| alpha158_QTLD60 | alpha158_rolling_price | strict_screening_input | alphalens_rank_ic_10d | 0.077101 |
| alpha158_QTLD60 | alpha158_rolling_price | strict_screening_input | jqfactor_rank_ic_10d | 0.077101 |
| alpha158_QTLD60 | alpha158_rolling_price | strict_screening_input | qlib_rank_ic_10d | 0.076647 |

## Top Correlation Pairs

| factor_a | factor_b | mean_daily_spearman_corr | abs_mean_daily_spearman_corr | date_count |
| --- | --- | --- | --- | --- |
| alpha158_VSUMP5 | alpha158_VSUMD5 | 1.000000 | 1.000000 | 120 |
| alpha158_VSUMN5 | alpha158_VSUMD5 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP5 | alpha158_VSUMN5 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP10 | alpha158_VSUMD10 | 1.000000 | 1.000000 | 120 |
| alpha158_VSUMP10 | alpha158_VSUMN10 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMN10 | alpha158_VSUMD10 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP20 | alpha158_VSUMN20 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMN20 | alpha158_VSUMD20 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP20 | alpha158_VSUMD20 | 1.000000 | 1.000000 | 120 |
| alpha158_VSUMN30 | alpha158_VSUMD30 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP30 | alpha158_VSUMN30 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP30 | alpha158_VSUMD30 | 1.000000 | 1.000000 | 120 |
| alpha158_VSUMP60 | alpha158_VSUMN60 | -1.000000 | 1.000000 | 120 |
| alpha158_VSUMP60 | alpha158_VSUMD60 | 1.000000 | 1.000000 | 120 |
| alpha158_VSUMN60 | alpha158_VSUMD60 | -1.000000 | 1.000000 | 120 |
| alpha158_SUMP60 | alpha158_SUMD60 | 1.000000 | 1.000000 | 120 |
| alpha158_SUMP60 | alpha158_SUMN60 | -1.000000 | 1.000000 | 120 |
| alpha158_SUMN60 | alpha158_SUMD60 | -1.000000 | 1.000000 | 120 |
| alpha158_SUMP30 | alpha158_SUMD30 | 1.000000 | 1.000000 | 120 |
| alpha158_SUMN30 | alpha158_SUMD30 | -1.000000 | 1.000000 | 120 |

## Correlation Metadata

| enabled | method | available_factor_count | candidate_date_count | used_date_count | min_instruments |
| --- | --- | --- | --- | --- | --- |
| True | daily_cross_section_spearman_mean | 158 | 120 | 120 | 100 |

## Output Files

- `alpha158_full_metric_index.csv`
- `alpha158_factor_screening_input.csv`
- `alpha158_ic_timeseries_summary.csv`
- `alpha158_quantile_return_summary.csv`
- `alpha158_turnover_summary.csv`
- `alpha158_rank_autocorrelation_summary.csv`
- `alpha158_context_group_ic_summary.csv`
- `alpha158_context_group_return_summary.csv`
- `alpha158_factor_correlation_summary.csv`
- `alpha158_factor_correlation_top_pairs.csv`

## Notes

- Alphalens `factor_information_coefficient` is treated as Rank IC because Alphalens uses Spearman rank correlation for this metric.
- ICIR is derived from the evaluator time series as mean divided by sample standard deviation.
- jqfactor_analyzer partial-pass is preserved as source status instead of being rewritten.
- Context metrics reuse the existing factor context/tradability-aware outputs.
- The factor board is a screening input, not an investment recommendation.
