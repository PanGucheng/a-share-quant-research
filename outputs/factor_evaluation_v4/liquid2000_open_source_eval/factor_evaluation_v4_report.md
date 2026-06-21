# Factor Evaluation V4 Smoke Test Report

This run validates whether open-source evaluation systems can consume the same tradability-filtered factor data.

- Factors: `rev_5,rev_20_exclude_5,std_20,amount_mean_20,downside_std_20`
- External evaluator results are stored side by side; no project-defined combined score is produced.
- Failures are expected during dependency discovery and are recorded instead of stopping the batch.

## Status

| system | step | failure_count |
| --- | --- | --- |
| jqfactor_analyzer | factor_alpha_beta | 5 |
| jqfactor_analyzer | factor_returns | 5 |

## Output Layout

- `factor_failure_reasons.csv`
- `adapter_reports/`
- `input_samples/`
- `alphalens_reloaded/<factor>/`
- `jqfactor_analyzer/<factor>/`
- `qlib_eval/<factor>/`
- `project_current/`
