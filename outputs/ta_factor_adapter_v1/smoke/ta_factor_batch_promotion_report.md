# TA Batch Promotion V1

- Batch root: `E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/ta_remaining74_batch1`
- Source factors: `74`
- Batch promoted: `72`
- Batch holdout: `2`
- Combined promoted: `77`

## Decision Counts

| decision | count |
| --- | --- |
| holdout | 2 |
| promoted | 72 |

## Evaluator Status

| system | status | count |
| --- | --- | --- |
| alphalens_reloaded | partial_pass | 2 |
| alphalens_reloaded | pass | 72 |
| jqfactor_analyzer | partial_pass | 74 |
| qlib_eval | pass | 74 |

## Failure Counts

| system | step | error | count |
| --- | --- | --- | --- |
| alphalens_reloaded | quantile_turnover | quantile_turnover produced no numeric values | 2 |
| jqfactor_analyzer | factor_alpha_beta | The name date occurs multiple times, use a level number | 74 |
| jqfactor_analyzer | factor_returns | The name date occurs multiple times, use a level number | 74 |

## Holdout Factors

| factor | decision | reason | alphalens_status | jqfactor_status | qlib_status |
| --- | --- | --- | --- | --- | --- |
| ta_volatility_bbli | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| ta_volatility_kchi | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
