# Environment

This document records the environment used by the reproducible A-share Qlib baseline.

## Project Paths

- Project root: `E:/qlib_prj/qlib_baseline`
- Qlib source: `E:/qlib_prj/qlib_clone`
- Qlib data: `E:/qlib_prj/qlib_data/cn_data`
- Conda environment: `qlib_env`
- Python executable: `E:/anaconda_envs/qlib_env/python.exe`

## Project Settings And Doctor

Committed machine-independent defaults are stored in `configs/project.yaml`. Qlib
source, provider, and daily cache paths remain `null` there. Copy the example for a
new workstation:

```powershell
Copy-Item configs/project.local.example.yaml configs/project.local.yaml
```

`configs/project.local.yaml` is ignored by Git. It may contain machine-specific
paths, while repository paths such as `outputs`, `artifacts`, `reports`, and `tmp`
continue to come from the committed base config. Environment variables or later CLI
arguments may override individual fields.

After editable installation, inspect the current interpreter, dependencies, and
resolved paths without selecting another Python executable:

```powershell
python -m pip install -e . --no-deps
python -m qlib_baseline.cli.doctor --strict
```

With the environment's Scripts directory on `PATH`, the equivalent command is:

```powershell
qlib-doctor --strict
```

Phase 2 exposes the active Forward Track through installed commands:

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

Run `qlib-doctor --strict` before these commands on a new workstation. Their default
Qlib source, provider, daily cache, repository root, and output paths are resolved
from Project Settings. The legacy active scripts remain wrappers and require the
editable project installation; they no longer modify `sys.path` themselves.

## Python

- Python version: `3.10.19`

## Qlib Source

- Editable install location: `E:/qlib_prj/qlib_clone`
- Current commit: `d5379c5 docs: replace broken RD-Agent demo links in README (#2150)`
- Current local source status:

```text
 M examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158_csi500.yaml
```

The `qlib_clone` directory is treated as an upstream source dependency and reference copy. Business code should stay in `qlib_baseline`.

## Key Packages

| package | version | note |
| --- | --- | --- |
| pyqlib | `0.1.dev6` | Editable install from `E:/qlib_prj/qlib_clone` |
| lightgbm | `4.6.0` | Baseline model backend |
| pandas | `2.3.3` | Data processing |
| numpy | `2.2.6` | Numeric backend |
| mlflow | `3.10.0` | Experiment record storage |
| PyYAML | `6.0.3` | YAML config parsing |

## Optional Factor Evaluation Packages

These packages are only required for V3.6 open-source factor evaluation smoke
tests. They are not required for the Qlib baseline workflow.

| package | version | note |
| --- | --- | --- |
| empyrical | `0.5.5` | Required by Alphalens Reloaded `performance.py` |
| fastcache | `1.1.0` | Required by jqfactor_analyzer package components |
| statsmodels | `0.14.6` | Required by Alphalens/jqfactor alpha-beta calculations |
| cached_property | `2.0.1` | Required by jqfactor_analyzer package components |
| pandas-datareader | `0.10.0` | Installed as empyrical dependency |
| lxml | `6.1.1` | Installed as pandas-datareader dependency |
| patsy | `1.0.2` | Installed as statsmodels dependency |

The install record is mirrored in:

```text
requirements-factor-evaluation.txt
```

## Baseline Data Snapshot

- Provider URI: `E:/qlib_prj/qlib_data/cn_data`
- Region: `cn`
- Frequency: `day`
- Calendar count: `4943`
- Calendar start: `1999-11-10`
- Calendar end: `2020-09-25`
- `all.txt` lines: `3875`
- `csi300.txt` lines: `820`
- `csi500.txt` lines: `2017`
- Feature instrument directories: `3875`

Observed fields for `sh600000`:

```text
change.day.bin
close.day.bin
factor.day.bin
high.day.bin
low.day.bin
open.day.bin
volume.day.bin
```

Known limitation: this data snapshot does not contain `amount.day.bin`, so amount-related diagnostics are expected to report 100% missing for the current baseline data.

## Directory Boundaries

- `qlib_baseline`: business project, scripts, configs, reports, and custom diagnostics.
- `qlib_clone`: upstream qlib source dependency and reference. Do not add business modules here.
- `qlib_data/cn_data`: read-only baseline data for step 1. Do not overwrite this data while solidifying the baseline.

## Captured On

- Date: `2026-06-11`
- Timezone from workspace context: `Asia/Shanghai`
