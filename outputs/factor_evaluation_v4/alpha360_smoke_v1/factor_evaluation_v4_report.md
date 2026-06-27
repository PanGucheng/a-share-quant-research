# Factor Evaluation V4 Smoke Test Report

This run validates whether open-source evaluation systems can consume the same tradability-filtered factor data.

- Factors: `alpha360_CLOSE5,alpha360_CLOSE20,alpha360_CLOSE59,alpha360_OPEN0,alpha360_OPEN5,alpha360_OPEN20,alpha360_OPEN59,alpha360_HIGH0,alpha360_HIGH5,alpha360_HIGH20,alpha360_HIGH59,alpha360_LOW0,alpha360_LOW5,alpha360_LOW20,alpha360_LOW59,alpha360_VWAP0,alpha360_VWAP5,alpha360_VWAP20,alpha360_VWAP59,alpha360_VOLUME5,alpha360_VOLUME20,alpha360_VOLUME59`
- External evaluator results are stored side by side; no project-defined combined score is produced.
- Failures are expected during dependency discovery and are recorded instead of stopping the batch.

## Status

| system | factor | status | output_file_count | failure_count | output_dir |
| --- | --- | --- | --- | --- | --- |
| alphalens_reloaded | alpha360_CLOSE5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_CLOSE5 |
| alphalens_reloaded | alpha360_CLOSE20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_CLOSE20 |
| alphalens_reloaded | alpha360_CLOSE59 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_CLOSE59 |
| alphalens_reloaded | alpha360_OPEN0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_OPEN0 |
| alphalens_reloaded | alpha360_OPEN5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_OPEN5 |
| alphalens_reloaded | alpha360_OPEN20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_OPEN20 |
| alphalens_reloaded | alpha360_OPEN59 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_OPEN59 |
| alphalens_reloaded | alpha360_HIGH0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_HIGH0 |
| alphalens_reloaded | alpha360_HIGH5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_HIGH5 |
| alphalens_reloaded | alpha360_HIGH20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_HIGH20 |
| alphalens_reloaded | alpha360_HIGH59 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_HIGH59 |
| alphalens_reloaded | alpha360_LOW0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_LOW0 |
| alphalens_reloaded | alpha360_LOW5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_LOW5 |
| alphalens_reloaded | alpha360_LOW20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_LOW20 |
| alphalens_reloaded | alpha360_LOW59 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_LOW59 |
| alphalens_reloaded | alpha360_VWAP0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VWAP0 |
| alphalens_reloaded | alpha360_VWAP5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VWAP5 |
| alphalens_reloaded | alpha360_VWAP20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VWAP20 |
| alphalens_reloaded | alpha360_VWAP59 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VWAP59 |
| alphalens_reloaded | alpha360_VOLUME5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VOLUME5 |
| alphalens_reloaded | alpha360_VOLUME20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VOLUME20 |
| alphalens_reloaded | alpha360_VOLUME59 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/alphalens_reloaded/alpha360_VOLUME59 |
| jqfactor_analyzer | alpha360_CLOSE5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_CLOSE5 |
| jqfactor_analyzer | alpha360_CLOSE20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_CLOSE20 |
| jqfactor_analyzer | alpha360_CLOSE59 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_CLOSE59 |
| jqfactor_analyzer | alpha360_OPEN0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_OPEN0 |
| jqfactor_analyzer | alpha360_OPEN5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_OPEN5 |
| jqfactor_analyzer | alpha360_OPEN20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_OPEN20 |
| jqfactor_analyzer | alpha360_OPEN59 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_OPEN59 |
| jqfactor_analyzer | alpha360_HIGH0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_HIGH0 |
| jqfactor_analyzer | alpha360_HIGH5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_HIGH5 |
| jqfactor_analyzer | alpha360_HIGH20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_HIGH20 |
| jqfactor_analyzer | alpha360_HIGH59 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_HIGH59 |
| jqfactor_analyzer | alpha360_LOW0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_LOW0 |
| jqfactor_analyzer | alpha360_LOW5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_LOW5 |
| jqfactor_analyzer | alpha360_LOW20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_LOW20 |
| jqfactor_analyzer | alpha360_LOW59 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_LOW59 |
| jqfactor_analyzer | alpha360_VWAP0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VWAP0 |
| jqfactor_analyzer | alpha360_VWAP5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VWAP5 |
| jqfactor_analyzer | alpha360_VWAP20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VWAP20 |
| jqfactor_analyzer | alpha360_VWAP59 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VWAP59 |
| jqfactor_analyzer | alpha360_VOLUME5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VOLUME5 |
| jqfactor_analyzer | alpha360_VOLUME20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VOLUME20 |
| jqfactor_analyzer | alpha360_VOLUME59 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/jqfactor_analyzer/alpha360_VOLUME59 |
| qlib_eval | alpha360_CLOSE5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_CLOSE5 |
| qlib_eval | alpha360_CLOSE20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_CLOSE20 |
| qlib_eval | alpha360_CLOSE59 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_CLOSE59 |
| qlib_eval | alpha360_OPEN0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_OPEN0 |
| qlib_eval | alpha360_OPEN5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_OPEN5 |
| qlib_eval | alpha360_OPEN20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_OPEN20 |
| qlib_eval | alpha360_OPEN59 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_OPEN59 |
| qlib_eval | alpha360_HIGH0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_HIGH0 |
| qlib_eval | alpha360_HIGH5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_HIGH5 |
| qlib_eval | alpha360_HIGH20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_HIGH20 |
| qlib_eval | alpha360_HIGH59 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_HIGH59 |
| qlib_eval | alpha360_LOW0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_LOW0 |
| qlib_eval | alpha360_LOW5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_LOW5 |
| qlib_eval | alpha360_LOW20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_LOW20 |
| qlib_eval | alpha360_LOW59 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_LOW59 |
| qlib_eval | alpha360_VWAP0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VWAP0 |
| qlib_eval | alpha360_VWAP5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VWAP5 |
| qlib_eval | alpha360_VWAP20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VWAP20 |
| qlib_eval | alpha360_VWAP59 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VWAP59 |
| qlib_eval | alpha360_VOLUME5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VOLUME5 |
| qlib_eval | alpha360_VOLUME20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VOLUME20 |
| qlib_eval | alpha360_VOLUME59 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha360_smoke_v1/qlib_eval/alpha360_VOLUME59 |

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

| system | return_mode | group_dimension | status | step_count |
| --- | --- | --- | --- | --- |
| alphalens_reloaded | benchmark_excess_return | index_segment | pass | 66 |
| alphalens_reloaded | benchmark_excess_return | listing_age_bucket | skipped_non_informative | 22 |
| alphalens_reloaded | raw_return | index_segment | pass | 66 |
| alphalens_reloaded | raw_return | listing_age_bucket | skipped_non_informative | 22 |
| jqfactor_analyzer | benchmark_excess_return | index_segment | pass | 66 |
| jqfactor_analyzer | benchmark_excess_return | listing_age_bucket | skipped_non_informative | 22 |
| jqfactor_analyzer | raw_return | index_segment | pass | 66 |
| jqfactor_analyzer | raw_return | listing_age_bucket | skipped_non_informative | 22 |

## Failures

| system | step | failure_count |
| --- | --- | --- |
| jqfactor_analyzer | factor_alpha_beta | 22 |
| jqfactor_analyzer | factor_returns | 22 |

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
