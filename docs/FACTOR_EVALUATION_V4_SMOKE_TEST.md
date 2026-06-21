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

After the V3.7 context integration, the output directory contains 240 files and
is about 6.0 MB.

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

## Configured Runner Update

The next V3.6 increment has now been implemented.

Configuration:

```text
configs/factor_evaluation_v4.yaml
```

Run command:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py `
  --config configs\factor_evaluation_v4.yaml
```

New outputs:

```text
dependency_status.csv
evaluator_status.csv
open_source_metric_index.csv
```

Latest status:

| system | pass | partial pass |
| --- | ---: | ---: |
| Alphalens Reloaded | 5 | 0 |
| jqfactor_analyzer | 0 | 5 |
| Qlib evaluate | 5 | 0 |
| current project | 5 | 0 |

`open_source_metric_index.csv` currently contains 90 long-format metric rows.
It is an index of source results only and intentionally contains no combined
score, subjective weight, or automatic factor ranking.

## V3.7 Point-In-Time Context Update

The evaluator now attaches Qlib point-in-time index membership, listing-age
context, and benchmark forward returns after the mandatory data-quality and
tradability filters.

Quick smoke command:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py `
  --config configs\factor_evaluation_v4_context_smoke.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py
```

The grouped metrics call the original `by_group=True` functions from Alphalens
Reloaded and jqfactor_analyzer. Raw forward returns and benchmark-excess forward
returns are stored separately under:

```text
context/<system>/<factor>/<return_mode>/<group_dimension>/
```

Important adapter correction:

- both adapters now remove rows missing any requested forward-return horizon,
  matching the source projects' clean-factor preparation;
- jqfactor weights are normalized by date and factor quantile, matching
  `jqfactor_analyzer.prepare.get_clean_factor`;
- source evaluation functions remain unchanged.

The five-factor full audit used 824,291 tradable rows and 820,580 complete
date/instrument rows per factor after 10D/20D alignment. It completed in 398
seconds.

| context result | count |
| --- | ---: |
| populated index segments | 4 |
| grouped evaluator steps passed | 60 |
| failed context steps | 0 |
| listing-age checks skipped as non-informative | 20 |
| `context_metric_index.csv` rows | 960 |

All current liquid2000 tradable samples are in the `501_plus` listing-age
bucket, so listing-age grouped metrics are explicitly skipped. This is a sample
property, not a silent evaluator success.

The validator also confirms that:

- Alphalens and jqfactor daily grouped Rank IC values are identical;
- subtracting one benchmark return within each date/index segment leaves Rank IC unchanged;
- grouped return outputs contain complete numeric 10D and 20D values;
- the metric index preserves source system, return mode, group, quantile,
  horizon, and source file without producing a combined score.
