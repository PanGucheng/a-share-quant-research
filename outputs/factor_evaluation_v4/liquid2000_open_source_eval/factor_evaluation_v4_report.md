# Factor Evaluation V4 Smoke Test Report

This run validates whether open-source evaluation systems can consume the same tradability-filtered factor data.

- Factors: `rev_5,rev_20_exclude_5,std_20,amount_mean_20,downside_std_20`
- External evaluator results are stored side by side; no project-defined combined score is produced.
- Failures are expected during dependency discovery and are recorded instead of stopping the batch.

## Status

| system | factor | status | output_file_count | failure_count | output_dir |
| --- | --- | --- | --- | --- | --- |
| alphalens_reloaded | rev_5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/alphalens_reloaded/rev_5 |
| alphalens_reloaded | rev_20_exclude_5 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/alphalens_reloaded/rev_20_exclude_5 |
| alphalens_reloaded | std_20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/alphalens_reloaded/std_20 |
| alphalens_reloaded | amount_mean_20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/alphalens_reloaded/amount_mean_20 |
| alphalens_reloaded | downside_std_20 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/alphalens_reloaded/downside_std_20 |
| jqfactor_analyzer | rev_5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/jqfactor_analyzer/rev_5 |
| jqfactor_analyzer | rev_20_exclude_5 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/jqfactor_analyzer/rev_20_exclude_5 |
| jqfactor_analyzer | std_20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/jqfactor_analyzer/std_20 |
| jqfactor_analyzer | amount_mean_20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/jqfactor_analyzer/amount_mean_20 |
| jqfactor_analyzer | downside_std_20 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/jqfactor_analyzer/downside_std_20 |
| qlib_eval | rev_5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/qlib_eval/rev_5 |
| qlib_eval | rev_20_exclude_5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/qlib_eval/rev_20_exclude_5 |
| qlib_eval | std_20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/qlib_eval/std_20 |
| qlib_eval | amount_mean_20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/qlib_eval/amount_mean_20 |
| qlib_eval | downside_std_20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/qlib_eval/downside_std_20 |
| project_current | rev_5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/project_current |
| project_current | rev_20_exclude_5 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/project_current |
| project_current | std_20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/project_current |
| project_current | amount_mean_20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/project_current |
| project_current | downside_std_20 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/liquid2000_open_source_eval/project_current |

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
