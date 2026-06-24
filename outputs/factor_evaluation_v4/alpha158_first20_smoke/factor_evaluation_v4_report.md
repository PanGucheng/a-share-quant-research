# Factor Evaluation V4 Smoke Test Report

This run validates whether open-source evaluation systems can consume the same tradability-filtered factor data.

- Factors: `alpha158_KMID,alpha158_KLEN,alpha158_KMID2,alpha158_KUP,alpha158_KUP2,alpha158_KLOW,alpha158_KLOW2,alpha158_KSFT,alpha158_KSFT2,alpha158_OPEN0,alpha158_HIGH0,alpha158_LOW0,alpha158_VWAP0,alpha158_ROC5,alpha158_ROC10,alpha158_ROC20,alpha158_ROC30,alpha158_ROC60,alpha158_MA5,alpha158_MA10`
- External evaluator results are stored side by side; no project-defined combined score is produced.
- Failures are expected during dependency discovery and are recorded instead of stopping the batch.

## Status

| system | factor | status | output_file_count | failure_count | output_dir |
| --- | --- | --- | --- | --- | --- |
| alphalens_reloaded | alpha158_KMID | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KMID |
| alphalens_reloaded | alpha158_KLEN | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KLEN |
| alphalens_reloaded | alpha158_KMID2 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KMID2 |
| alphalens_reloaded | alpha158_KUP | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KUP |
| alphalens_reloaded | alpha158_KUP2 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KUP2 |
| alphalens_reloaded | alpha158_KLOW | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KLOW |
| alphalens_reloaded | alpha158_KLOW2 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KLOW2 |
| alphalens_reloaded | alpha158_KSFT | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KSFT |
| alphalens_reloaded | alpha158_KSFT2 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_KSFT2 |
| alphalens_reloaded | alpha158_OPEN0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_OPEN0 |
| alphalens_reloaded | alpha158_HIGH0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_HIGH0 |
| alphalens_reloaded | alpha158_LOW0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_LOW0 |
| alphalens_reloaded | alpha158_VWAP0 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_VWAP0 |
| alphalens_reloaded | alpha158_ROC5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_ROC5 |
| alphalens_reloaded | alpha158_ROC10 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_ROC10 |
| alphalens_reloaded | alpha158_ROC20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_ROC20 |
| alphalens_reloaded | alpha158_ROC30 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_ROC30 |
| alphalens_reloaded | alpha158_ROC60 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_ROC60 |
| alphalens_reloaded | alpha158_MA5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_MA5 |
| alphalens_reloaded | alpha158_MA10 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/alphalens_reloaded/alpha158_MA10 |
| jqfactor_analyzer | alpha158_KMID | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KMID |
| jqfactor_analyzer | alpha158_KLEN | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KLEN |
| jqfactor_analyzer | alpha158_KMID2 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KMID2 |
| jqfactor_analyzer | alpha158_KUP | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KUP |
| jqfactor_analyzer | alpha158_KUP2 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KUP2 |
| jqfactor_analyzer | alpha158_KLOW | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KLOW |
| jqfactor_analyzer | alpha158_KLOW2 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KLOW2 |
| jqfactor_analyzer | alpha158_KSFT | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KSFT |
| jqfactor_analyzer | alpha158_KSFT2 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_KSFT2 |
| jqfactor_analyzer | alpha158_OPEN0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_OPEN0 |
| jqfactor_analyzer | alpha158_HIGH0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_HIGH0 |
| jqfactor_analyzer | alpha158_LOW0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_LOW0 |
| jqfactor_analyzer | alpha158_VWAP0 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_VWAP0 |
| jqfactor_analyzer | alpha158_ROC5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_ROC5 |
| jqfactor_analyzer | alpha158_ROC10 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_ROC10 |
| jqfactor_analyzer | alpha158_ROC20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_ROC20 |
| jqfactor_analyzer | alpha158_ROC30 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_ROC30 |
| jqfactor_analyzer | alpha158_ROC60 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_ROC60 |
| jqfactor_analyzer | alpha158_MA5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_MA5 |
| jqfactor_analyzer | alpha158_MA10 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/jqfactor_analyzer/alpha158_MA10 |
| qlib_eval | alpha158_KMID | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KMID |
| qlib_eval | alpha158_KLEN | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KLEN |
| qlib_eval | alpha158_KMID2 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KMID2 |
| qlib_eval | alpha158_KUP | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KUP |
| qlib_eval | alpha158_KUP2 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KUP2 |
| qlib_eval | alpha158_KLOW | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KLOW |
| qlib_eval | alpha158_KLOW2 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KLOW2 |
| qlib_eval | alpha158_KSFT | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KSFT |
| qlib_eval | alpha158_KSFT2 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_KSFT2 |
| qlib_eval | alpha158_OPEN0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_OPEN0 |
| qlib_eval | alpha158_HIGH0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_HIGH0 |
| qlib_eval | alpha158_LOW0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_LOW0 |
| qlib_eval | alpha158_VWAP0 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_VWAP0 |
| qlib_eval | alpha158_ROC5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_ROC5 |
| qlib_eval | alpha158_ROC10 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_ROC10 |
| qlib_eval | alpha158_ROC20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_ROC20 |
| qlib_eval | alpha158_ROC30 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_ROC30 |
| qlib_eval | alpha158_ROC60 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_ROC60 |
| qlib_eval | alpha158_MA5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_MA5 |
| qlib_eval | alpha158_MA10 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke/qlib_eval/alpha158_MA10 |

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
| alphalens_reloaded | benchmark_excess_return | index_segment | pass | 60 |
| alphalens_reloaded | benchmark_excess_return | listing_age_bucket | skipped_non_informative | 20 |
| alphalens_reloaded | raw_return | index_segment | pass | 60 |
| alphalens_reloaded | raw_return | listing_age_bucket | skipped_non_informative | 20 |
| jqfactor_analyzer | benchmark_excess_return | index_segment | pass | 60 |
| jqfactor_analyzer | benchmark_excess_return | listing_age_bucket | skipped_non_informative | 20 |
| jqfactor_analyzer | raw_return | index_segment | pass | 60 |
| jqfactor_analyzer | raw_return | listing_age_bucket | skipped_non_informative | 20 |

## Failures

| system | step | failure_count |
| --- | --- | --- |
| jqfactor_analyzer | factor_alpha_beta | 20 |
| jqfactor_analyzer | factor_returns | 20 |

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
