# A 股 Qlib 量化工程开发计划

本文档记录当前工程从 qlib 基线实验升级为可复现 A 股量化研究框架的开发路线。工程目标不是一开始就追求复杂模型，而是先建立可靠的数据、实验、因子、组合回测和报告闭环。

## 路线校准结论

当前方向总体正确，但下一阶段的重点需要更明确：

- 对新手和开源整合路线而言，先把数据、股票池、实验复现和回测解释做扎实，比快速堆模型更重要。
- `LightGBM + Alpha158 + CSI500` 继续作为主基线锚点，不因短期宽股票池实验结果而丢掉。
- 宽股票池路线可以继续，但必须从 `all_stock_shsz_liquid2000` 这类可交易性更好的 universe 开始。
- 下一阶段优先级是“组合约束 + 因子研究”，模型扩展只作为对照实验，不作为主线。
- 深度学习、强化学习、复杂在线交易暂缓，避免在数据和研究评价体系尚未稳固时引入过多不确定性。

## 当前工程状态

当前目录结构中，`qlib_baseline` 是业务工程仓库，`qlib_clone` 是本地 qlib 源码克隆，`qlib_data` 是本地 A 股 qlib 数据目录。

已经具备的能力：

- 已跑通官方风格的 `LightGBM + Alpha158 + CSI500` qrun 工作流。
- 已有可复用运行脚本 `scripts/run_baseline.ps1`。
- 已有 MLflow 输出目录 `outputs/mlruns_validated/`。
- 已有数据质量诊断模块 `data_quality/`。
- 已导入社区 A 股 qlib 数据，并构建派生 provider。
- 已有 `CSI500`、`all_stock_shsz`、`all_stock_shsz_liquid2000` 三条实验线。
- 已有基线结果汇总表 `outputs/reports/baseline_summary.csv`。

已知主要缺口：

- 社区数据的字段口径还需要继续核查，尤其是 `adjclose`、`factor`、`amount`、`volume`。
- 缺失区间需要和停牌/交易状态源对齐。
- 宽股票池已能跑通，但组合收益对流动性和 TopK 参数很敏感。
- 还没有独立的因子研究模块，无法系统判断单因子质量、相关性和入选规则。
- 模型矩阵还未建立，目前只有 LightGBM 主基线。
- 报告生成仍以 CSV/Markdown 为主，尚未形成统一图表化报告。

## 总体目标

构建一个面向 A 股的本地量化研究框架，最小闭环包括：

```text
数据源
  -> 原始数据归档
  -> 数据清洗与质量检查
  -> qlib bin 数据集
  -> 因子与标签
  -> qrun 训练与预测
  -> 信号分析
  -> 组合回测
  -> 结果报告
  -> 每日模拟盘信号
```

## 技术选型

主干框架：

- Qlib：负责数据读取、因子处理、模型训练、预测、信号分析、组合回测和实验记录。
- MLflow：沿用 qlib 的实验记录机制，保存参数、指标和 artifacts。

数据源建议：

- `chenditc/investment_data`：优先作为 qlib A 股数据更新来源之一。
- AKShare：用于补充和交叉校验 A 股日线、指数、换手率、成交额、基础信息等数据。
- 后续可评估 TuShare、BaoStock 或商业数据源，但不要在第一阶段引入太多来源。

回测与执行：

- 第一阶段继续使用 qlib 内置回测和 `TopkDropoutStrategy`。
- 第二阶段再考虑自定义 `WeightStrategyBase` 策略。
- RQAlpha 可作为事件驱动回测候选，但需注意使用许可和数据接入成本。

## 开发阶段

### 阶段 1：基线固化与可复现

目标：把当前一次性跑通的基线变成稳定、可复现、可检查的工程起点。

周期：1 到 2 天。

核心产物：

- 环境与版本记录。
- 一键运行基线脚本。
- 一键运行数据质量检查脚本。
- 基线结果汇总脚本或手工汇总模板。
- 清晰的验收清单。

### 阶段 2：数据层升级

目标：将旧版本地数据升级为可持续更新、可审计的 A 股数据层。

周期：约 1 周。

核心产物：

- 新旧数据目录隔离方案。
- 原始数据归档目录。
- qlib bin 转换流程。
- 数据质量报告升级。
- 字段完整性、覆盖率、复权、成交额、停牌、涨跌停检查。

### 阶段 3：研究流水线

目标：从单一实验扩展为可批量对比、可解释的实验矩阵。

周期：约 1 周。

核心产物：

- 多市场配置：`csi300`、`csi500`、`all_stock_shsz_liquid2000`。
- 多策略配置：不同 `topk`、`n_drop`、benchmark、交易成本。
- 多特征配置：先稳定 `Alpha158`，再评估 `Alpha360` 和自定义因子集合。
- 多模型配置：LightGBM、线性模型、XGBoost/CatBoost；简单神经网络放在后续。
- MLflow 结果汇总表。

### 阶段 4：因子研究模块

目标：建立可解释、可筛选、可复验的因子研究流程。

周期：1 到 2 周。

核心产物：

- 因子库目录。
- 因子覆盖率检查。
- IC、Rank IC、ICIR、分组收益、换手率报告。
- 因子入选和剔除规则。
- 因子相关性和冗余度检查。
- 单因子到多因子模型的接入规则。

### 阶段 5：组合策略与回测升级

目标：从简单 TopK-Drop 升级到更贴近 A 股交易约束的组合构建。

周期：约 1 周。

核心产物：

- TopK 参数扫描和基准组合约束。
- 自定义组合策略。
- 单票权重、换手、行业偏离、停牌、涨跌停约束。
- 成本模型和风控规则。
- 回测报告标准化。

### 阶段 5.5：模型扩展对照

目标：在数据、因子和组合评价体系稳定后，引入模型对照，确认收益来自有效信号而不是单一模型偶然性。

周期：约 3 到 5 天。

核心产物：

- 线性模型/Ridge/Lasso sanity check。
- XGBoost/CatBoost 与 LightGBM 对照。
- 模型间 IC、Rank IC、收益、回撤和稳定性对比。
- 暂不把深度学习作为主线，除非传统模型和因子流程已经稳定。

### 阶段 6：报告与看板

目标：让每次实验自动产出可读报告。

周期：3 到 5 天。

核心产物：

- 实验摘要报告。
- 净值、超额收益、回撤、IC 序列、换手率、持仓集中度图表。
- 横向实验对比表。

### 阶段 7：每日模拟盘信号

目标：在不直接下单的前提下，形成每日候选组合和调仓建议。

周期：1 到 2 周。

核心产物：

- 每日数据更新任务。
- 每日质量检查任务。
- 每日预测和组合生成任务。
- `signals/YYYY-MM-DD.csv` 信号文件。
- 模拟盘运行日志。

## 第一阶段详细计划：基线固化与可复现

### 第一阶段目标

把当前 `qlib_baseline` 固化成一个干净的研究起点。完成后，新实验必须从这个稳定起点派生，而不是直接修改 qlib 源码或覆盖旧数据。

第一阶段不做这些事：

- 不优化模型参数。
- 不新增复杂因子。
- 不接入真实交易。
- 不覆盖现有 `qlib_data/cn_data`。
- 不把业务逻辑写进 `qlib_clone`。

### 工作 1：确认工程边界

目的：避免把 qlib 上游源码、本地数据和业务工程混在一起。

具体任务：

- 确认业务代码只放在 `qlib_baseline`。
- 确认 `qlib_clone` 只作为 qlib 源码依赖和参考，不新增业务模块。
- 确认 `qlib_data/cn_data` 作为只读基线数据，不在第一阶段修改。
- 记录当前 qlib commit。
- 检查 `qlib_clone` 中已有改动，确认是否只是示例配置改动。

建议命令：

```powershell
git -C E:\qlib_prj\qlib_clone log -1 --oneline
git -C E:\qlib_prj\qlib_clone status --short
git -C E:\qlib_prj\qlib_baseline status --short
```

验收标准：

- 文档中明确三类目录职责。
- 没有把业务代码写入 `qlib_clone`。
- 没有修改 `qlib_data/cn_data`。

### 工作 2：记录运行环境

目的：以后复现实验时，知道当时用的 Python、qlib、LightGBM、pandas、mlflow 版本。

具体任务：

- 新增环境快照文档，建议路径：`docs/ENVIRONMENT.md`。
- 记录 conda 环境名：`qlib_env`。
- 记录 Python 解释器路径。
- 记录关键包版本。
- 记录 qlib 源码路径和 commit。

建议命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe --version
E:\anaconda_envs\qlib_env\python.exe -m pip show pyqlib lightgbm pandas numpy mlflow
git -C E:\qlib_prj\qlib_clone log -1 --oneline
```

建议产物：

```text
docs/ENVIRONMENT.md
```

验收标准：

- 任意一天回看文档，可以知道基线是在哪个环境中跑出来的。
- 关键依赖版本不依赖口头记忆。

### 工作 3：固化基线运行入口

目的：让基线运行不依赖手工步骤。

现有入口：

```text
scripts/run_baseline.ps1
scripts/qrun_with_project_tmp.py
configs/workflow_lightgbm_alpha158_csi500.yaml
```

具体任务：

- 确认 `run_baseline.ps1` 从项目根目录和外部目录执行都能正确定位路径。
- 确认临时目录固定在 `qlib_baseline/tmp`，避免 Windows 临时目录权限问题。
- 确认输出统一写入 `outputs/mlruns_validated`。
- 确认日志统一写入 `logs/`。
- 在 README 中保留最短运行命令。

建议命令：

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_baseline.ps1
```

验收标准：

- 命令能跑完整个 qrun 工作流。
- 生成新的 log 文件。
- MLflow run 状态为 finished。
- 关键指标能在 `metrics/` 中找到。

### 工作 4：固化数据质量检查入口

目的：每次实验前先知道数据是否可靠。

现有入口：

```text
scripts/run_data_quality.ps1
data_quality/config.yaml
data_quality/checker.py
```

具体任务：

- 保留默认检查范围：`csi500`、`2017-01-01` 到 `2020-08-01`。
- 增加一个小范围 smoke test 配置或命令，用于快速检查代码是否能跑。
- 明确 `amount` 缺失是当前数据集结构问题，不在第一阶段修复。
- 在报告中标注动态股票池问题，避免把所有历史非成分期都当作真实异常。

建议命令：

```powershell
cd E:\qlib_prj\qlib_baseline
.\scripts\run_data_quality.ps1 --config data_quality/config.yaml
.\scripts\run_data_quality.ps1 --market csi300 --start-time 2020-01-01 --end-time 2020-03-31
```

验收标准：

- 默认检查能生成完整报告。
- smoke test 能在较短时间完成。
- 输出目录结构稳定。
- 数据问题不会阻塞基线训练，但会被记录。

### 工作 5：新增结果汇总能力

目的：不要每次手动翻 MLflow 目录找指标。

建议新增脚本：

```text
scripts/summarize_mlruns.py
```

最小功能：

- 扫描 `outputs/mlruns_validated`。
- 找到 finished runs。
- 读取核心 metrics。
- 输出 CSV 到 `outputs/reports/baseline_summary.csv`。

第一版建议汇总指标：

```text
run_id
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

验收标准：

- 运行脚本后生成一个 CSV。
- CSV 至少包含当前成功基线 run。
- CSV 中核心指标和 `BASELINE_REPORT.md` 一致。

### 工作 6：整理 Git 跟踪范围

目的：让仓库只跟踪代码、配置和小型文档，不跟踪大量实验产物。

具体任务：

- 保留基线报告和必要示例结果。
- 大型 MLflow artifacts 原则上不进 git。
- 数据质量 CSV 如果体积较大，只保留汇总报告或样例。
- `tmp/`、缓存、临时测试输出继续忽略。

需要小心：

- 不要删除已有输出，先只调整 `.gitignore` 和文档说明。
- 如果要清理历史大文件，单独开任务处理。

验收标准：

- `git status --short` 中新增内容可解释。
- 没有把大体积数据、缓存、临时目录加入版本控制。

### 工作 7：第一阶段验收清单

第一阶段完成时，应能回答这些问题：

- 当前基线用的是哪个 qlib commit？
- 当前基线用的是哪个 Python 环境？
- 当前数据集覆盖到哪一天？
- 基线训练命令是什么？
- 数据质量检查命令是什么？
- 成功 run 的 ID 是什么？
- 核心 IC、Rank IC、年化收益、回撤是多少？
- 当前数据质量最大问题是什么？
- 后续实验应该从哪个配置复制修改？

建议最终产物：

```text
docs/ENVIRONMENT.md
docs/_archive/01_early_stage_plans/BASELINE_REPRODUCIBILITY.md
outputs/reports/baseline_summary.csv
scripts/summarize_mlruns.py
```

### 第一阶段时间安排

第 1 个半天：

- 确认目录边界。
- 记录环境。
- 检查 qlib 源码和业务仓库 git 状态。

第 2 个半天：

- 复跑基线。
- 复跑数据质量检查。
- 整理运行日志和结果路径。

第 3 个半天：

- 编写 `summarize_mlruns.py`。
- 生成 `baseline_summary.csv`。
- 对比 `BASELINE_REPORT.md` 指标。

第 4 个半天：

- 完成可复现说明文档。
- 整理 `.gitignore` 和 Git 状态。
- 做第一阶段验收。

## 风险与注意事项

- A 股数据质量比模型选择更重要，字段缺失、复权错误和股票池错误会直接污染回测。
- 初期不要过早追求实时交易，先做好每日模拟盘信号。
- 不要直接覆盖旧数据，所有数据升级都应使用新目录。
- 不要把策略收益当作唯一指标，必须同时看 IC、Rank IC、回撤、换手和成本后收益。
- 不要把 qlib 源码仓库改成业务项目，业务逻辑应留在 `qlib_baseline`。
- 不要因为宽股票池 IC 高就直接扩大交易范围；必须同时看流动性、成交额、停牌、涨跌停和组合集中度。
- 不要过早引入复杂深度模型。对新手阶段，先用简单模型解释清楚信号来源和失败原因。

## 参考资料

- Microsoft Qlib: https://github.com/microsoft/qlib
- Qlib Workflow: https://qlib.readthedocs.io/en/latest/component/workflow.html
- Qlib Data Layer: https://qlib.readthedocs.io/en/latest/component/data.html
- Qlib Portfolio Strategy: https://qlib.readthedocs.io/en/latest/component/strategy.html
- Qlib Online Serving: https://qlib.readthedocs.io/en/latest/component/online.html
- chenditc/investment_data: https://github.com/chenditc/investment_data
- AKShare: https://github.com/akfamily/akshare
- RQAlpha: https://github.com/ricequant/rqalpha
