# Qlib LightGBM + Alpha158 Baseline Report

## Result

Baseline setup succeeded.

- Project root: `E:/qlib_prj/qlib_baseline`
- Qlib source package: editable install from `E:/qlib_prj/qlib_clone`
- Conda environment: `qlib_env`
- Data path: `E:/qlib_prj/qlib_data/cn_data`
- Workflow config: `configs/workflow_lightgbm_alpha158_csi500.yaml`
- Run script: `scripts/run_baseline.ps1`

## Data Validation

The local A-share `cn_data` provider was initialized successfully by qrun:

```text
data_path={'__DEFAULT_FREQ': WindowsPath('E:/qlib_prj/qlib_data/cn_data')}
```

The workflow loaded and processed Alpha158 data successfully:

```text
Loading data Done
DropnaLabel Done
CSZScoreNorm Done
fit & process data Done
Init data Done
```

## Workflow Validation

The official Qlib A-share LightGBM + Alpha158 CSI500 workflow completed successfully.

Confirmed stages:

- Dataset construction and Alpha158 processing
- LightGBM training with validation early stopping
- Prediction generation
- Signal analysis
- Backtest loop over 871 steps
- Portfolio analysis and indicator analysis artifact saving

Successful experiment:

- Experiment ID: `902143453991050438`
- Run ID: `1664d70296414b29ad01866f1f585e15`
- Status: `FINISHED` (`status: 3` in MLflow `meta.yaml`)
- Log: `logs/qrun_lightgbm_alpha158_csi500_20260611_113628.log`

## Output Location

Results are saved under:

```text
E:/qlib_prj/qlib_baseline/outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15
```

Important artifacts:

- `artifacts/pred.pkl`
- `artifacts/label.pkl`
- `artifacts/params.pkl`
- `artifacts/task`
- `artifacts/sig_analysis/ic.pkl`
- `artifacts/sig_analysis/ric.pkl`
- `artifacts/portfolio_analysis/port_analysis_1day.pkl`
- `artifacts/portfolio_analysis/indicator_analysis_1day.pkl`
- `artifacts/portfolio_analysis/report_normal_1day.pkl`
- `artifacts/portfolio_analysis/positions_normal_1day.pkl`
- `metrics/IC`
- `metrics/Rank IC`
- `metrics/ICIR`
- `metrics/Rank ICIR`
- `metrics/1day.excess_return_with_cost.*`
- `metrics/1day.excess_return_without_cost.*`

Key printed metrics:

```text
IC: 0.039390054668819584
ICIR: 0.4036532897768011
Rank IC: 0.04727387420884508
Rank ICIR: 0.5052277849472542

excess return with cost:
annualized_return: 0.111076
information_ratio: 1.325249
max_drawdown: -0.072773
```

## Next Integration Points

For an automatic data cleaning and factor screening system, continue from these baseline outputs:

- Use `pred.pkl` and `label.pkl` to inspect prediction/label alignment and downstream scoring inputs.
- Use `sig_analysis/ic.pkl` and `ric.pkl` as the first factor effectiveness and rank-correlation validation outputs.
- Use `metrics/IC`, `metrics/Rank IC`, `metrics/ICIR`, and `metrics/Rank ICIR` as stable scalar screening signals.
- Use `portfolio_analysis/report_normal_1day.pkl` and `positions_normal_1day.pkl` to connect factor quality to backtest behavior.

This baseline intentionally does not optimize strategy settings, modify the model, or add custom factors.
