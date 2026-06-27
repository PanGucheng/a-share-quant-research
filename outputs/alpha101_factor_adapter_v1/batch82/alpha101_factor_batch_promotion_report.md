# Alpha101 Batch Promotion V1

- Batch root: `E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha101_candidate71_batch1`
- Source factors: `71`
- Batch promoted: `59`
- V4 batch holdout: `12`
- Adapter holdout: `6`
- All holdout: `18`
- Combined promoted: `64`

## Decision Counts

| decision | count |
| --- | --- |
| holdout | 12 |
| promoted | 59 |

## Evaluator Status

| system | status | count |
| --- | --- | --- |
| alphalens_reloaded | not_run | 6 |
| alphalens_reloaded | partial_pass | 6 |
| alphalens_reloaded | pass | 59 |
| jqfactor_analyzer | not_run | 6 |
| jqfactor_analyzer | partial_pass | 65 |
| qlib_eval | pass | 71 |

## Failure Counts

| system | step | error | count |
| --- | --- | --- | --- |
| alphalens_reloaded | quantile_turnover | quantile_turnover produced no numeric values | 6 |
| jqfactor_analyzer | factor_alpha_beta | The name date occurs multiple times, use a level number | 65 |
| jqfactor_analyzer | factor_returns | The name date occurs multiple times, use a level number | 65 |
| jqfactor_analyzer | quantile_turnover | quantile_turnover produced no numeric values | 4 |

## Holdout Factors

| factor | decision | reason | alphalens_status | jqfactor_status | qlib_status |
| --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha001 | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha007 | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha021 | holdout | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha023 | holdout | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha027 | holdout | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha061 | holdout | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha065 | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha068 | holdout | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha075 | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha081 | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
| kunquant_alpha101_alpha086 | holdout | alphalens_reloaded_not_run | not_run | not_run | pass |
| kunquant_alpha101_alpha099 | holdout | alphalens_reloaded_partial:quantile_turnover | partial_pass | partial_pass | pass |
