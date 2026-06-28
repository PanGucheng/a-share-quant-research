# Alpha360 Strict OOS Extension V1

- Scope: strict OOS diagnostics for 3 reviewed Alpha360 probes.
- Boundary: no model training, no strategy optimization, no evaluator definition changes.
- Expression summary: `outputs/alpha360_expression_frame_v1/strict_oos_recent_2024_2026/expression_frame_summary.csv`
- Metric index: `outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/open_source_metric_index.csv`

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| expected_factor_count | pass | factors=3, missing= |
| expression_coverage | pass | min_coverage=0.996236 |
| batch_passed | pass | passed_batches=1 |
| metric_index_rows | pass | metric_rows=54 |
| metric_factor_coverage | pass | metric_factors=3 |
| evaluator_status_allowed | pass | allowed_partial_rows=3, allowed_failure_rows=6 |
| no_training_side_effect | pass | strict_oos_audit_only |
| batch_summary_metric_rows | pass | summary_metric_rows=54 |

## Expression Coverage

| factor | valid_rows | total_rows | coverage | missing_rate | min | max | mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| alpha360_HIGH36 | 285864 | 286944 | 0.996236 | 0.003764 | 0.258467 | 44.445034 | 1.024657 |
| alpha360_HIGH37 | 285866 | 286944 | 0.996243 | 0.003757 | 0.245989 | 44.735325 | 1.024891 |
| alpha360_HIGH40 | 285866 | 286944 | 0.996243 | 0.003757 | 0.225416 | 48.475834 | 1.025331 |

## Batch Manifest

| batch_id | status | returncode | factor_count | factors | config_path | output_dir | started_at | ended_at | elapsed_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_001 | pass | 0 | 3 | alpha360_HIGH36,alpha360_HIGH37,alpha360_HIGH40 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha360_strict_oos_recent\generated_configs\batch_001.yaml | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha360_strict_oos_recent\runs\batch_001 | 2026-06-28T12:15:53 | 2026-06-28T12:16:48 | 54.170000 |

## Batch Output Summary

| batch_id | status | factor_count | factors | evaluator_status_rows | failure_rows | metric_rows | context_metric_rows | output_dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_001 | pass | 3 | alpha360_HIGH36,alpha360_HIGH37,alpha360_HIGH40 | 9 | 6 | 54 | 0 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha360_strict_oos_recent\runs\batch_001 |

## Evaluator Status

| system | factor | status | output_file_count | failure_count | output_dir |
| --- | --- | --- | --- | --- | --- |
| alphalens_reloaded | alpha360_HIGH36 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/alphalens_reloaded/alpha360_HIGH36 |
| alphalens_reloaded | alpha360_HIGH37 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/alphalens_reloaded/alpha360_HIGH37 |
| alphalens_reloaded | alpha360_HIGH40 | pass | 8 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/alphalens_reloaded/alpha360_HIGH40 |
| jqfactor_analyzer | alpha360_HIGH36 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/jqfactor_analyzer/alpha360_HIGH36 |
| jqfactor_analyzer | alpha360_HIGH37 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/jqfactor_analyzer/alpha360_HIGH37 |
| jqfactor_analyzer | alpha360_HIGH40 | partial_pass | 5 | 2 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/jqfactor_analyzer/alpha360_HIGH40 |
| qlib_eval | alpha360_HIGH36 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/qlib_eval/alpha360_HIGH36 |
| qlib_eval | alpha360_HIGH37 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/qlib_eval/alpha360_HIGH37 |
| qlib_eval | alpha360_HIGH40 | pass | 4 | 0 | E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/qlib_eval/alpha360_HIGH40 |

## Failure Reasons

| system | factor | step | error_type | error | traceback_tail |
| --- | --- | --- | --- | --- | --- |
| jqfactor_analyzer | alpha360_HIGH36 | factor_returns | ValueError | The name date occurs multiple times, use a level number | ValueError: The name date occurs multiple times, use a level number |
| jqfactor_analyzer | alpha360_HIGH36 | factor_alpha_beta | ValueError | The name date occurs multiple times, use a level number | ValueError: The name date occurs multiple times, use a level number |
| jqfactor_analyzer | alpha360_HIGH37 | factor_returns | ValueError | The name date occurs multiple times, use a level number | ValueError: The name date occurs multiple times, use a level number |
| jqfactor_analyzer | alpha360_HIGH37 | factor_alpha_beta | ValueError | The name date occurs multiple times, use a level number | ValueError: The name date occurs multiple times, use a level number |
| jqfactor_analyzer | alpha360_HIGH40 | factor_returns | ValueError | The name date occurs multiple times, use a level number | ValueError: The name date occurs multiple times, use a level number |
| jqfactor_analyzer | alpha360_HIGH40 | factor_alpha_beta | ValueError | The name date occurs multiple times, use a level number | ValueError: The name date occurs multiple times, use a level number |

## Metric Summary

| factor | alphalens_reloaded:mean_information_coefficient:10D | alphalens_reloaded:mean_information_coefficient:20D | jqfactor_analyzer:mean_information_coefficient:period_10 | jqfactor_analyzer:mean_information_coefficient:period_20 | qlib_eval:annualized_return:label_10d_t1 | qlib_eval:annualized_return:label_20d_t1 | qlib_eval:information_ratio:label_10d_t1 | qlib_eval:information_ratio:label_20d_t1 | qlib_eval:mean:label_10d_t1 | qlib_eval:mean:label_20d_t1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alpha360_HIGH36 | 0.063736 | 0.072231 | 0.063736 | 0.072231 | 14.756836 | 17.131914 | 5.025121 | 6.289686 | 0.062004 | 0.071983 |
| alpha360_HIGH37 | 0.065477 | 0.073073 | 0.065477 | 0.073073 | 15.123256 | 17.322861 | 5.153590 | 6.354661 | 0.063543 | 0.072785 |
| alpha360_HIGH40 | 0.065851 | 0.072314 | 0.065851 | 0.072314 | 15.104165 | 17.125857 | 5.157218 | 6.298794 | 0.063463 | 0.071957 |

## Notes

- jqfactor_analyzer partial pass is allowed only for the known factor_returns/factor_alpha_beta index-name issue.
- This stage confirms evaluability and recent-OOS diagnostics; it does not promote factors into training inputs.
