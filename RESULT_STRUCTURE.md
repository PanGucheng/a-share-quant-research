# Qlib Workflow Result Structure

This document describes the output structure produced by the validated Qlib A-share LightGBM + Alpha158 baseline run.

It only documents the existing baseline outputs. It does not add strategies, optimize models, or modify factors.

## Baseline Run Identity

- Project root: `E:/qlib_prj/qlib_baseline`
- Workflow config: `E:/qlib_prj/qlib_baseline/configs/workflow_lightgbm_alpha158_csi500.yaml`
- Run script: `E:/qlib_prj/qlib_baseline/scripts/run_baseline.ps1`
- Data provider: `E:/qlib_prj/qlib_data/cn_data`
- MLflow output root: `E:/qlib_prj/qlib_baseline/outputs/mlruns_validated`
- Experiment name: `qlib_baseline_lightgbm_alpha158_csi500`
- Experiment ID: `902143453991050438`
- Successful run ID: `1664d70296414b29ad01866f1f585e15`
- Successful run log: `E:/qlib_prj/qlib_baseline/logs/qrun_lightgbm_alpha158_csi500_20260611_113628.log`

The successful run directory is:

```text
E:/qlib_prj/qlib_baseline/outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15
```

## Top-Level Project Output Layout

```text
E:/qlib_prj/qlib_baseline
+-- configs/
|   +-- workflow_lightgbm_alpha158_csi500.yaml
+-- scripts/
|   +-- run_baseline.ps1
|   +-- qrun_with_project_tmp.py
+-- logs/
|   +-- qrun_lightgbm_alpha158_csi500_20260611_113628.log
+-- outputs/
|   +-- mlruns/
|   +-- mlruns_validated/
+-- tmp/
+-- BASELINE_REPORT.md
+-- RESULT_STRUCTURE.md
```

Notes:

- `outputs/mlruns_validated/` is the clean validated result root.
- `outputs/mlruns/` contains earlier failed/interrupted attempts and should not be used as the validated baseline.
- `tmp/` is only a runtime temporary directory used by the runner.

## MLflow Experiment Structure

The validated experiment directory is:

```text
outputs/mlruns_validated/902143453991050438
```

Important entries:

```text
902143453991050438/
+-- meta.yaml
+-- 1664d70296414b29ad01866f1f585e15/
+-- a1f6b81fdc774125b9b91826cf899a77/
```

- `meta.yaml`: experiment metadata, including experiment name and artifact root.
- `1664d70296414b29ad01866f1f585e15/`: successful completed run.
- `a1f6b81fdc774125b9b91826cf899a77/`: failed sandbox attempt; ignore for baseline validation.

## Successful Run Structure

The successful run directory contains:

```text
1664d70296414b29ad01866f1f585e15/
+-- artifacts/
+-- metrics/
+-- params/
+-- tags/
+-- meta.yaml
```

### Run Metadata

Path:

```text
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15/meta.yaml
```

Purpose:

- Records the run ID, experiment ID, artifact URI, start/end time, user, and run status.
- `status: 3` means the MLflow run finished successfully.

## Experiment Results And Artifacts

Artifacts are stored under:

```text
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15/artifacts
```

Observed artifact layout:

```text
artifacts/
+-- config
+-- dataset
+-- label.pkl
+-- params.pkl
+-- pred.pkl
+-- task
+-- sig_analysis/
|   +-- ic.pkl
|   +-- ric.pkl
+-- portfolio_analysis/
    +-- indicators_normal_1day.pkl
    +-- indicators_normal_1day_obj.pkl
    +-- indicator_analysis_1day.pkl
    +-- port_analysis_1day.pkl
    +-- positions_normal_1day.pkl
    +-- report_normal_1day.pkl
```

Artifact meaning:

- `config`: rendered workflow configuration used by qrun.
- `task`: serialized Qlib task definition, including model, dataset, and record configuration.
- `dataset`: serialized dataset record produced by the workflow.
- `params.pkl`: serialized model parameter/state record saved by Qlib.
- `label.pkl`: labels corresponding to the prediction/evaluation period.
- `pred.pkl`: model prediction output from `SignalRecord`.
- `sig_analysis/ic.pkl`: IC time series/result from `SigAnaRecord`.
- `sig_analysis/ric.pkl`: Rank IC time series/result from `SigAnaRecord`.
- `portfolio_analysis/report_normal_1day.pkl`: backtest return report.
- `portfolio_analysis/positions_normal_1day.pkl`: simulated portfolio positions.
- `portfolio_analysis/port_analysis_1day.pkl`: portfolio risk/return analysis.
- `portfolio_analysis/indicator_analysis_1day.pkl`: trade/execution indicator analysis.
- `portfolio_analysis/indicators_normal_1day.pkl`: raw indicator output.
- `portfolio_analysis/indicators_normal_1day_obj.pkl`: object-form indicator output.

## Prediction Results

Prediction result path:

```text
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15/artifacts/pred.pkl
```

Related label path:

```text
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15/artifacts/label.pkl
```

These are the first files to inspect when connecting later data cleaning and factor screening logic to model output.

## Model And Workflow Records

Qlib stores model/workflow records in both artifacts and params:

Artifact records:

```text
artifacts/params.pkl
artifacts/task
artifacts/config
artifacts/dataset
```

MLflow params directory:

```text
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15/params
```

Observed parameter files include:

```text
model.class
model.module_path
model.kwargs.loss
model.kwargs.learning_rate
model.kwargs.num_leaves
model.kwargs.num_threads
dataset.class
dataset.module_path
dataset.kwargs.handler.class
dataset.kwargs.handler.module_path
dataset.kwargs.handler.kwargs.instruments
dataset.kwargs.segments.train
dataset.kwargs.segments.valid
dataset.kwargs.segments.test
record
cmd-sys.argv
```

Use this directory to confirm which model, dataset handler, segments, and recorders were used for a run.

## Backtest Metrics

Scalar metrics are stored under:

```text
outputs/mlruns_validated/902143453991050438/1664d70296414b29ad01866f1f585e15/metrics
```

Observed metric files:

```text
IC
ICIR
Rank IC
Rank ICIR
l2.train
l2.valid
1day.excess_return_without_cost.annualized_return
1day.excess_return_without_cost.information_ratio
1day.excess_return_without_cost.max_drawdown
1day.excess_return_without_cost.mean
1day.excess_return_without_cost.std
1day.excess_return_with_cost.annualized_return
1day.excess_return_with_cost.information_ratio
1day.excess_return_with_cost.max_drawdown
1day.excess_return_with_cost.mean
1day.excess_return_with_cost.std
1day.ffr
1day.pa
1day.pos
```

Use these files for quick scalar comparison across future experiments. For richer time-series details, use the pickle files under `artifacts/sig_analysis/` and `artifacts/portfolio_analysis/`.

## Log Files

Validated run log:

```text
E:/qlib_prj/qlib_baseline/logs/qrun_lightgbm_alpha158_csi500_20260611_113628.log
```

This log confirms:

- Qlib initialization and data provider path.
- Alpha158 data loading and processing.
- LightGBM training and early stopping.
- Prediction output.
- IC and Rank IC calculation.
- Backtest loop completion.
- Portfolio and indicator analysis artifact saving.

Earlier logs in `logs/` may include failed sandbox attempts. Use the timestamped log above for the successful baseline.

## Recommended Read Order

For future development around automatic data cleaning and factor screening, inspect outputs in this order:

1. `logs/qrun_lightgbm_alpha158_csi500_20260611_113628.log`
2. `artifacts/config` and `artifacts/task`
3. `artifacts/pred.pkl` and `artifacts/label.pkl`
4. `artifacts/sig_analysis/ic.pkl` and `artifacts/sig_analysis/ric.pkl`
5. `metrics/IC`, `metrics/Rank IC`, `metrics/ICIR`, `metrics/Rank ICIR`
6. `artifacts/portfolio_analysis/report_normal_1day.pkl`
7. `artifacts/portfolio_analysis/positions_normal_1day.pkl`

This keeps the next phase grounded in the official baseline workflow before introducing any custom data cleaning or factor screening logic.
