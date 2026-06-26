# Factor Evaluation V4 Smoke Test Report

This run validates whether open-source evaluation systems can consume the same tradability-filtered factor data.

- Factors: `ta_momentum_rsi,ta_momentum_roc,ta_volatility_bbw,ta_trend_macd_diff,ta_volume_cmf`
- External evaluator results are stored side by side; no project-defined combined score is produced.
- Failures are expected during dependency discovery and are recorded instead of stopping the batch.

## Status

| system | factor | status | output_file_count | failure_count | output_dir |
| --- | --- | --- | --- | --- | --- |
| alphalens_reloaded | ta_momentum_rsi | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/alphalens_reloaded/ta_momentum_rsi |
| alphalens_reloaded | ta_momentum_roc | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/alphalens_reloaded/ta_momentum_roc |
| alphalens_reloaded | ta_volatility_bbw | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/alphalens_reloaded/ta_volatility_bbw |
| alphalens_reloaded | ta_trend_macd_diff | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/alphalens_reloaded/ta_trend_macd_diff |
| alphalens_reloaded | ta_volume_cmf | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/alphalens_reloaded/ta_volume_cmf |
| jqfactor_analyzer | ta_momentum_rsi | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/jqfactor_analyzer/ta_momentum_rsi |
| jqfactor_analyzer | ta_momentum_roc | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/jqfactor_analyzer/ta_momentum_roc |
| jqfactor_analyzer | ta_volatility_bbw | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/jqfactor_analyzer/ta_volatility_bbw |
| jqfactor_analyzer | ta_trend_macd_diff | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/jqfactor_analyzer/ta_trend_macd_diff |
| jqfactor_analyzer | ta_volume_cmf | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/jqfactor_analyzer/ta_volume_cmf |
| qlib_eval | ta_momentum_rsi | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/qlib_eval/ta_momentum_rsi |
| qlib_eval | ta_momentum_roc | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/qlib_eval/ta_momentum_roc |
| qlib_eval | ta_volatility_bbw | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/qlib_eval/ta_volatility_bbw |
| qlib_eval | ta_trend_macd_diff | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/qlib_eval/ta_trend_macd_diff |
| qlib_eval | ta_volume_cmf | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/ta_smoke_v1/qlib_eval/ta_volume_cmf |

## Dependency Status

| kind | name | required_by | status | version_or_path | detail |
| --- | --- | --- | --- | --- | --- |
| python_package | empyrical | alphalens_reloaded | available | 0.5.5 |  |
| python_package | fastcache | jqfactor_analyzer | available | 1.1.0 |  |
| python_package | statsmodels | alphalens_reloaded,jqfactor_analyzer | available | 0.14.6 |  |
| python_package | cached_property | jqfactor_analyzer | available | 2.0.1 |  |
| source_file | alphalens_reloaded | alphalens_reloaded | available | E:/qlib_prj/qlib_baseline/tmp/reference_repos/alphalens-reloaded/src/alphalens/performance.py |  |
| source_file | jqfactor_analyzer | jqfactor_analyzer | available | E:/qlib_prj/qlib_baseline/tmp/reference_repos/jqfactor_analyzer/jqfactor_analyzer/performance.py |  |
| source_file | qlib_evaluate | qlib_evaluate | available | E:/qlib_prj/qlib_clone/qlib/contrib/evaluate.py |  |

## Point-In-Time Context

Context evaluation was not enabled.

## Failures

| system | step | failure_count |
| --- | --- | --- |
| jqfactor_analyzer | factor_alpha_beta | 5 |
| jqfactor_analyzer | factor_returns | 5 |

## Output Layout

- `factor_failure_reasons.csv`
- `dependency_status.csv`
- `evaluator_status.csv`
- `open_source_metric_index.csv`
- `adapter_reports/`
- `input_samples/`
- `alphalens_reloaded/<factor>/`
- `jqfactor_analyzer/<factor>/`
- `qlib_eval/<factor>/`
- `project_current/`
- `context/context_coverage.csv`
- `context/context_evaluator_status.csv`
- `context/context_metric_index.csv`
- `context/<system>/<factor>/<return_mode>/<group_dimension>/`
