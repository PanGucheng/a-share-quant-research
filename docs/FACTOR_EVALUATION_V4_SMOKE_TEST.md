# Factor Evaluation V4 Smoke Test

This document records the first V3.6 smoke test for open-source factor
evaluation coexistence.

## Command

```powershell
cd E:\qlib_prj\qlib_baseline
$env:PYTHONDONTWRITEBYTECODE='1'
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py
```

## Scope

The runner used the existing Qlib-derived factor pipeline and mandatory
tradability/data-quality filters.

| item | value |
| --- | --- |
| provider | `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived` |
| market | `all_stock_shsz_liquid2000` |
| window | `main_research_2021_2023` |
| raw rows | `1,414,832` |
| tradable rows | `824,291` |
| labels | `label_10d_t1`, `label_20d_t1` |
| factors | `rev_5`, `rev_20_exclude_5`, `std_20`, `amount_mean_20`, `downside_std_20` |

## Optional Dependencies Installed

The first run showed that the reference projects needed additional optional
packages. They were installed into `qlib_env`:

```text
empyrical==0.5.5
fastcache==1.1.0
statsmodels==0.14.6
cached_property==2.0.1
pandas-datareader==0.10.0
lxml==6.1.1
patsy==1.0.2
```

They are also recorded in:

```text
requirements-factor-evaluation.txt
```

## Output Directory

```text
outputs/factor_evaluation_v4/liquid2000_open_source_eval/
```

Main outputs:

```text
adapter_reports/
input_samples/
alphalens_reloaded/<factor>/
jqfactor_analyzer/<factor>/
qlib_eval/<factor>/
project_current/
factor_failure_reasons.csv
factor_evaluation_v4_report.md
```

The output directory currently contains 132 files and is about 1.5 MB.

## Result Summary

| system | status | notes |
| --- | --- | --- |
| Alphalens Reloaded | pass | Core `performance.py` functions produced CSV outputs for all 5 test factors |
| jqfactor_analyzer | partial pass | IC, mean IC, quantile return, and turnover produced outputs; `factor_returns` and `factor_alpha_beta` failed under pandas 2.x MultiIndex behavior |
| Qlib evaluate | pass | Daily Rank IC and Qlib `risk_analysis` outputs were generated for all factors and labels |
| current project | pass | Existing V3 summary/correlation/exposure outputs were copied into the V4 coexistence directory |

## Alphalens Outputs

For each factor, the runner generated:

```text
factor_alpha_beta.csv
factor_returns.csv
information_coefficient.csv
mean_information_coefficient.csv
mean_return_by_quantile.csv
mean_return_by_quantile_std_error.csv
quantile_turnover.csv
rank_autocorrelation.csv
```

This means the first Alphalens-style evaluator path is usable after optional
dependencies are installed.

## jqfactor Outputs

For each factor, the runner generated:

```text
information_coefficient.csv
mean_information_coefficient.csv
mean_return_by_quantile.csv
mean_return_by_quantile_std_error.csv
quantile_turnover.csv
```

Remaining jqfactor failures:

```text
factor_returns    ValueError: The name date occurs multiple times, use a level number
factor_alpha_beta ValueError: The name date occurs multiple times, use a level number
```

This appears to be an old pandas groupby/MultiIndex compatibility issue in the
reference project. The current project should not silently rewrite those
functions. The next step is to either:

1. pin a compatible pandas environment for jqfactor reproduction, or
2. vendor the exact jqfactor function with a clearly documented compatibility
   patch and license header.

## Adapter Findings

- Alphalens requires period columns such as `10D` and `20D`.
- jqfactor requires period columns such as `period_10` and `period_20`.
- Package-level imports are too broad for both reference projects:
  - `alphalens.__init__` imports plotting/tears modules.
  - `jqfactor_analyzer.__init__` imports data API and attribution modules.
- The runner therefore loads each reference `performance.py` file directly,
  together with its local relative dependencies, without executing package
  `__init__.py`. This preserves metric source code while avoiding unrelated UI
  and data API dependencies.

## Next Step

The next engineering step is not to expand the factor pool yet. It is to make
the V4 evaluator runner reproducible and configurable:

- add a small config file for evaluator systems, factors, labels, and windows;
- add explicit dependency checks before a run starts;
- add a compatibility decision for jqfactor `factor_returns` and `factor_alpha_beta`;
- add a compact leaderboard that only summarizes open-source outputs, without
  defining a final project score.

