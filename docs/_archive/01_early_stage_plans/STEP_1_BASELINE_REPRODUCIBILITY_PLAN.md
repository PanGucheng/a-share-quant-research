# 第一步具体计划：基线固化与可复现

本文档是第一阶段的执行清单。目标是把当前已经跑通的 `LightGBM + Alpha158 + CSI500` 实验固化为稳定基线，后续所有数据升级、因子研究、模型优化都从这个基线派生。

## 1. 目标

完成后应达到：

- 任何时候都能知道当前基线使用的 qlib commit、Python 环境和核心包版本。
- 一条命令能复跑基线训练、预测、信号分析和回测。
- 一条命令能复跑数据质量检查。
- 能快速汇总 MLflow 中的核心指标。
- Git 仓库只跟踪代码、配置、文档和必要的小型结果，不误提交大体积实验产物。

## 2. 范围

本步骤只处理 `E:/qlib_prj/qlib_baseline` 工程。

不做：

- 不优化 LightGBM 参数。
- 不新增因子。
- 不升级或覆盖 `E:/qlib_prj/qlib_data/cn_data`。
- 不把业务代码写入 `E:/qlib_prj/qlib_clone`。
- 不接入实盘或模拟交易接口。

## 3. 当前输入

已有文件：

```text
E:/qlib_prj/qlib_baseline/README.md
E:/qlib_prj/qlib_baseline/BASELINE_REPORT.md
E:/qlib_prj/qlib_baseline/RESULT_STRUCTURE.md
E:/qlib_prj/qlib_baseline/configs/workflow_lightgbm_alpha158_csi500.yaml
E:/qlib_prj/qlib_baseline/scripts/run_baseline.ps1
E:/qlib_prj/qlib_baseline/scripts/run_data_quality.ps1
E:/qlib_prj/qlib_baseline/data_quality/config.yaml
```

已有成功基线：

```text
Experiment ID: 902143453991050438
Run ID: 1664d70296414b29ad01866f1f585e15
```

已有核心指标：

```text
IC: 0.039390054668819584
ICIR: 0.4036532897768011
Rank IC: 0.04727387420884508
Rank ICIR: 0.5052277849472542
excess_return_with_cost.annualized_return: 0.111076
excess_return_with_cost.information_ratio: 1.325249
excess_return_with_cost.max_drawdown: -0.072773
```

## 4. 交付物

第一步完成时，建议至少新增或确认以下产物：

```text
docs/ENVIRONMENT.md
docs/BASELINE_REPRODUCIBILITY.md
scripts/summarize_mlruns.py
outputs/reports/baseline_summary.csv
```

其中：

- `ENVIRONMENT.md` 记录运行环境和依赖版本。
- `BASELINE_REPRODUCIBILITY.md` 记录如何复跑基线和如何判断成功。
- `summarize_mlruns.py` 汇总 MLflow 指标。
- `baseline_summary.csv` 保存基线结果摘要。

## 5. 执行计划

### 任务 1：确认目录边界

目的：防止后续把 qlib 源码、数据目录和业务工程混在一起。

执行命令：

```powershell
git -C E:\qlib_prj\qlib_clone log -1 --oneline
git -C E:\qlib_prj\qlib_clone status --short
git -C E:\qlib_prj\qlib_baseline status --short
```

记录内容：

- `qlib_clone` 当前 commit。
- `qlib_clone` 是否有本地修改。
- `qlib_baseline` 当前未提交内容。

验收标准：

- 明确 `qlib_clone` 只作为依赖和参考。
- 明确 `qlib_data/cn_data` 在第一步只读。
- 明确业务代码只进入 `qlib_baseline`。

### 任务 2：生成环境快照

目的：保证基线可复现。

执行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe --version
E:\anaconda_envs\qlib_env\python.exe -m pip show pyqlib lightgbm pandas numpy mlflow pyyaml
git -C E:\qlib_prj\qlib_clone log -1 --oneline
```

写入文件：

```text
docs/ENVIRONMENT.md
```

建议内容：

```text
# Environment

- Project root: E:/qlib_prj/qlib_baseline
- Qlib source: E:/qlib_prj/qlib_clone
- Qlib data: E:/qlib_prj/qlib_data/cn_data
- Conda env: qlib_env
- Python executable: E:/anaconda_envs/qlib_env/python.exe
- Python version: <fill from command>
- Qlib commit: <fill from command>

## Packages

- pyqlib: <version>
- lightgbm: <version>
- pandas: <version>
- numpy: <version>
- mlflow: <version>
- pyyaml: <version>
```

验收标准：

- 文档中包含 Python 版本、包版本、qlib commit。
- 后续复跑无需靠记忆确认环境。

### 任务 3：复跑基线工作流

目的：确认当前代码和数据仍能完整跑通。

执行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_baseline.ps1
```

检查点：

- 控制台没有 qrun fatal error。
- `logs/` 下生成新的 `qrun_lightgbm_alpha158_csi500_*.log`。
- `outputs/mlruns_validated/` 下出现新的 run。
- 新 run 的 `meta.yaml` 中状态为 finished。

建议记录：

```text
docs/BASELINE_REPRODUCIBILITY.md
```

记录内容：

- 运行时间。
- 新 run ID。
- 日志路径。
- 输出路径。
- 是否成功。

验收标准：

- 基线训练、预测、信号分析和组合回测全部完成。
- 新 run 有 `pred.pkl`、`label.pkl`、`sig_analysis` 和 `portfolio_analysis` artifacts。

### 任务 4：复跑数据质量检查

目的：确认数据诊断模块可独立运行。

默认检查：

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_data_quality.ps1 --config data_quality/config.yaml
```

快速 smoke test：

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_data_quality.ps1 --market csi300 --start-time 2020-01-01 --end-time 2020-03-31
```

检查点：

- `outputs/data_quality/` 下生成对应目录。
- 目录中有 `data_quality_report.md`。
- 目录中有 `overview.csv`、`rule_counts.csv`、`field_missing_rate.csv`。

验收标准：

- 默认检查能完整完成。
- smoke test 能快速完成。
- 报告中明确当前数据缺少 `amount` 字段。

### 任务 5：实现 MLflow 指标汇总脚本

目的：不再手动翻 MLflow 目录。

新增文件：

```text
scripts/summarize_mlruns.py
```

最小输入：

```text
outputs/mlruns_validated
```

最小输出：

```text
outputs/reports/baseline_summary.csv
```

第一版需要输出字段：

```text
experiment_id
run_id
status
start_time
end_time
IC
ICIR
Rank IC
Rank ICIR
1day.excess_return_with_cost.annualized_return
1day.excess_return_with_cost.information_ratio
1day.excess_return_with_cost.max_drawdown
1day.excess_return_without_cost.annualized_return
1day.excess_return_without_cost.information_ratio
1day.excess_return_without_cost.max_drawdown
```

建议运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_mlruns.py --mlruns outputs\mlruns_validated --output outputs\reports\baseline_summary.csv
```

验收标准：

- 生成 `outputs/reports/baseline_summary.csv`。
- CSV 至少包含 run `1664d70296414b29ad01866f1f585e15`。
- CSV 中历史成功 run 的核心指标与 `BASELINE_REPORT.md` 一致。

### 任务 6：编写可复现说明

目的：把第一步跑法写成新手也能照做的文档。

新增文件：

```text
docs/BASELINE_REPRODUCIBILITY.md
```

建议结构：

```text
# Baseline Reproducibility

## Purpose
## Directory Boundaries
## Environment
## Run Baseline
## Run Data Quality Check
## Summarize Results
## Expected Metrics
## Known Data Issues
## Troubleshooting
```

验收标准：

- 文档中有完整命令。
- 文档中有预期输出路径。
- 文档中有成功判断标准。
- 文档中说明 `amount` 缺失、数据截至日期等已知问题。

### 任务 7：整理 Git 跟踪范围

目的：只提交该提交的内容，避免把大型输出误提交。

执行命令：

```powershell
git -C E:\qlib_prj\qlib_baseline status --short
```

需要检查：

- `docs/` 应进入 Git。
- `scripts/summarize_mlruns.py` 应进入 Git。
- 大型 `outputs/mlruns_validated` artifacts 原则上不新增进入 Git。
- `tmp/`、缓存目录、临时测试输出不进入 Git。

验收标准：

- 每个新增或修改文件都有明确理由。
- 没有误提交数据集、缓存、临时目录。

## 6. 半天级时间安排

### 第 1 个半天

- 完成任务 1：确认目录边界。
- 完成任务 2：生成环境快照。
- 输出 `docs/ENVIRONMENT.md`。

### 第 2 个半天

- 完成任务 3：复跑基线。
- 完成任务 4：复跑数据质量检查。
- 记录 run ID、日志路径、报告路径。

### 第 3 个半天

- 完成任务 5：实现 MLflow 指标汇总脚本。
- 生成 `outputs/reports/baseline_summary.csv`。
- 和 `BASELINE_REPORT.md` 对齐指标。

### 第 4 个半天

- 完成任务 6：编写可复现说明。
- 完成任务 7：整理 Git 跟踪范围。
- 对照验收清单做最终检查。

## 7. 第一完成标准

当以下事项全部满足，即认为第一步完成：

- `docs/ENVIRONMENT.md` 存在且内容完整。
- `docs/BASELINE_REPRODUCIBILITY.md` 存在且可照文档复跑。
- `.\scripts\run_baseline.ps1` 可完整跑通。
- `.\scripts\run_data_quality.ps1 --config data_quality/config.yaml` 可完整跑通。
- `scripts/summarize_mlruns.py` 可生成 `outputs/reports/baseline_summary.csv`。
- `baseline_summary.csv` 包含至少一个成功 run。
- 已知数据问题被记录，而不是被忽略。
- Git 状态中没有不应提交的大型数据或临时文件。

## 8. 后续衔接

第一步完成后，第二步再开始做数据层升级：

- 保留旧数据目录作为基线。
- 新建近期 A 股数据目录。
- 接入 `chenditc/investment_data` 或 AKShare。
- 升级数据质量检查，让它支持动态股票池和字段完整性校验。
