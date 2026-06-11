# Baseline Reproducibility

This document describes how to reproduce the A-share Qlib baseline from the current project state.

## Purpose

The baseline is the official-style `LightGBM + Alpha158 + CSI500` workflow adapted to the local A-share Qlib data directory. It is the reference point for later data upgrades, factor research, model experiments, and portfolio strategy work.

## Directory Boundaries

- `E:/qlib_prj/qlib_baseline`: business project, configs, scripts, diagnostics, and reports.
- `E:/qlib_prj/qlib_clone`: editable qlib source dependency. Do not add business code here.
- `E:/qlib_prj/qlib_data/cn_data`: read-only baseline A-share data for this step.

## Environment

See `docs/ENVIRONMENT.md` for the captured environment.

Important current settings:

- Python executable: `E:/anaconda_envs/qlib_env/python.exe`
- qlib source commit: `d5379c5 docs: replace broken RD-Agent demo links in README (#2150)`
- qlib data end date: `2020-09-25`
- Current data fields: `change`, `close`, `factor`, `high`, `low`, `open`, `volume`
- Known missing field: `amount`

## Baseline Config

Baseline workflow:

```text
configs/workflow_lightgbm_alpha158_csi500.yaml
```

The config uses:

- Market: `csi500`
- Benchmark: `SH000905`
- Model: `qlib.contrib.model.gbdt.LGBModel`
- Data handler: `qlib.contrib.data.handler.Alpha158`
- Strategy: `qlib.contrib.strategy.TopkDropoutStrategy`
- Train segment: `2008-01-01` to `2014-12-31`
- Valid segment: `2015-01-01` to `2016-12-31`
- Test/backtest segment: `2017-01-01` to `2020-08-01`

The default config keeps qlib's normal parallel data loading behavior for local Windows runs outside the restricted Codex sandbox.

Sandbox-only config:

```text
configs/workflow_lightgbm_alpha158_csi500_sandbox.yaml
```

The sandbox config adds:

```yaml
kernels: 1
joblib_backend: threading
```

This is slower, but avoids joblib multiprocessing pipe permission errors inside restricted environments.

## Run Baseline

Preferred command from a normal PowerShell session:

```powershell
cd E:\qlib_prj\qlib_baseline
powershell -ExecutionPolicy Bypass -File .\scripts\run_baseline.ps1
```

When running from Codex or another managed agent, run the full qrun outside the restricted sandbox with escalation. Do not use the restricted sandbox for the full baseline run because Windows multiprocessing and Python temporary artifact writes can fail there.

The runner uses:

- `E:/anaconda_envs/qlib_env/python.exe` by default.
- `QLIB_ENV_PYTHON` if that environment variable is set.
- `tmp/` under the project root as runtime temp space.
- `outputs/mlruns_validated` as the MLflow output root.

Sandbox-safe mode is retained only as a diagnostic fallback. It is much slower and should not be the normal path:

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_baseline.ps1 -SafeMode
```

Preferred unsandboxed rerun on `2026-06-11`:

```text
Experiment ID: 902143453991050438
Run ID: f6a1207624a74d498c00655a218b274c
Status: finished
Log: logs/qrun_lightgbm_alpha158_csi500_20260611_194840.log
Elapsed wall time observed from Codex tool run: about 149 seconds
```

Expected artifacts:

```text
artifacts/pred.pkl
artifacts/label.pkl
artifacts/params.pkl
artifacts/task
artifacts/config
artifacts/dataset
artifacts/sig_analysis/ic.pkl
artifacts/sig_analysis/ric.pkl
artifacts/portfolio_analysis/port_analysis_1day.pkl
artifacts/portfolio_analysis/indicator_analysis_1day.pkl
artifacts/portfolio_analysis/report_normal_1day.pkl
artifacts/portfolio_analysis/positions_normal_1day.pkl
```

## Expected Metrics

The current reproducible run matches the historical validated baseline:

| metric | value |
| --- | --- |
| IC | `0.039390054668819584` |
| ICIR | `0.4036532897768011` |
| Rank IC | `0.04727387420884508` |
| Rank ICIR | `0.5052277849472542` |
| excess return with cost annualized return | `0.11107595634238779` |
| excess return with cost information ratio | `1.3252492154867777` |
| excess return with cost max drawdown | `-0.07277290679859844` |
| excess return without cost annualized return | `0.15345438035909362` |
| excess return without cost information ratio | `1.8311908947024544` |
| excess return without cost max drawdown | `-0.06650820171215371` |

## Run Data Quality Check

Default check:

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_data_quality.ps1 --config data_quality/config.yaml
```

Default output:

```text
outputs/data_quality/csi500_2017-01-01_2020-08-01
```

Smoke test:

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_data_quality.ps1 --market csi300 --start-time 2020-01-01 --end-time 2020-03-31 --output-dir outputs/data_quality_test
```

Smoke test output:

```text
outputs/data_quality_test/csi300_2020-01-01_2020-03-31
```

## Summarize Results

Generate a CSV summary from the MLflow file store:

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_mlruns.py --mlruns outputs\mlruns_validated --output outputs\reports\baseline_summary.csv
```

Current summary output:

```text
outputs/reports/baseline_summary.csv
```

The summary includes both historical and newly generated runs. Failed runs have empty metric columns, while finished runs contain IC, Rank IC, and portfolio metrics.

## Known Data Issues

- `amount` is missing from the current qlib data snapshot.
- Some dates and instruments have low coverage in the data quality report.
- Current data ends on `2020-09-25`, so it is not suitable for recent A-share research.
- The current quality checker still needs better dynamic-stock-pool awareness in later stages.

## Troubleshooting Notes

- If `No module named 'qlib'` appears, make sure `scripts/run_baseline.ps1` is using `E:/anaconda_envs/qlib_env/python.exe` or set `QLIB_ENV_PYTHON`.
- If Windows denies `tempfile.mkdtemp()` directories in a restricted environment, the preferred fix is to rerun outside the sandbox with escalation.
- If unsandboxed execution is unavailable, run `.\scripts\run_baseline.ps1 -SafeMode`. The wrapper then creates temp directories through `Path.mkdir()` and treats qlib uncommitted-code artifact logging as best effort.
- If joblib multiprocessing fails with `PermissionError: [WinError 5]`, first rerun outside the sandbox. Use `-SafeMode` only as a slow fallback, which selects `configs/workflow_lightgbm_alpha158_csi500_sandbox.yaml`.
- Gym warnings and missing optional CatBoost/XGBoost/PyTorch messages are non-blocking for the LightGBM baseline.
