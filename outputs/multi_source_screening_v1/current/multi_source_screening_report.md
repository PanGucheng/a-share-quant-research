# Multi-Source Screening V1

- Pool name: `multi_source_v1`
- Scope: screening contract only; no model training, no strategy optimization, no evaluator redefinition.
- Sources: Alpha158 validated reference plus promoted TA and Alpha101 catalogs.

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| source_count | pass | sources=3 |
| total_screening_rows | pass | rows=242 |
| new_source_screening_rows | pass | new_source_rows=82 |
| standard_columns | pass | columns=41 |
| alpha_candidates_not_holdout | pass | alpha_candidates=14 |
| holdout_visible | pass | holdouts=5 |
| board_pool_alignment | pass | board=242, pool=242 |

## Source Counts

| source_family | screening_gate | count |
| --- | --- | --- |
| alpha101 | strict_screening_input | 5 |
| alpha158 | holdout | 3 |
| alpha158 | strict_screening_input | 155 |
| ta | holdout | 2 |
| ta | strict_screening_input | 77 |

## Role Counts

| source_family | role | count |
| --- | --- | --- |
| alpha101 | monitor | 5 |
| alpha158 | alpha_candidate | 14 |
| alpha158 | excluded_high_turnover | 33 |
| alpha158 | excluded_redundant | 55 |
| alpha158 | excluded_unstable_context | 16 |
| alpha158 | holdout | 3 |
| alpha158 | monitor | 37 |
| ta | holdout | 2 |
| ta | monitor | 77 |

## Alpha Candidates

| factor | source_family | role | pool_reason | primary_rank_ic |
| --- | --- | --- | --- | --- |
| alpha158_IMIN20 | alpha158 | alpha_candidate | consistent_signal_accepted | 0.040908 |
| alpha158_IMIN30 | alpha158 | alpha_candidate | strong_signal_accepted | 0.057858 |
| alpha158_IMIN60 | alpha158 | alpha_candidate | strong_signal_accepted | 0.068445 |
| alpha158_MIN10 | alpha158 | alpha_candidate | strong_signal_accepted | 0.061041 |
| alpha158_MIN30 | alpha158 | alpha_candidate | strong_signal_accepted | 0.083258 |
| alpha158_MIN5 | alpha158 | alpha_candidate | strong_signal_accepted | 0.055802 |
| alpha158_MIN60 | alpha158 | alpha_candidate | strong_signal_accepted | 0.099945 |
| alpha158_QTLD10 | alpha158 | alpha_candidate | consistent_signal_accepted | 0.038871 |
| alpha158_QTLD30 | alpha158 | alpha_candidate | strong_signal_accepted | 0.072863 |
| alpha158_QTLD60 | alpha158 | alpha_candidate | strong_signal_accepted | 0.097826 |
| alpha158_ROC10 | alpha158 | alpha_candidate | consistent_signal_accepted | 0.034488 |
| alpha158_ROC30 | alpha158 | alpha_candidate | strong_signal_accepted | 0.080597 |
| alpha158_ROC60 | alpha158 | alpha_candidate | strong_signal_accepted | 0.083509 |
| alpha158_VSUMN60 | alpha158 | alpha_candidate | consistent_signal_accepted | 0.035648 |

## Holdouts

| factor | source_family | promotion_reason | alphalens_status | jqfactor_status | qlib_status |
| --- | --- | --- | --- | --- | --- |
| alpha158_CNTN5 | alpha158 | alphalens=partial_pass | partial_pass | partial_pass | pass |
| alpha158_IMAX5 | alpha158 | alphalens=partial_pass | partial_pass | partial_pass | pass |
| alpha158_RANK5 | alpha158 | alphalens=partial_pass | partial_pass | partial_pass | pass |
| ta_volatility_bbli | ta | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| ta_volatility_kchi | ta | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |

## Output Files

- `multi_source_screening_input.csv`
- `multi_source_candidate_board.csv`
- `multi_source_candidate_pool.csv`
- `multi_source_alpha_candidates.csv`
- `multi_source_holdouts.csv`
- `multi_source_contract_status.csv`
- `multi_source_candidate_pool.json`
