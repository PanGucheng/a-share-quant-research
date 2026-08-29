# Current Pipeline

## 1. 权威状态

本文是当前运行入口索引，不替代研究路线、冻结 artifact 或机器状态文件。

当前 tracked machine status 记录：

- 当前时间敏感主线是 Forward Track；
- frozen Strategy V1 为 LightGBM、52 因子、Long Only Top50 等权、每 5 个交易日调仓；
- 2026-08-07 official prediction 已完成并等待标签成熟；
- 2026-08-07 paper decision 已完成，计划执行日为 2026-08-10，当前状态为
  `pending_execution`；
- production model selection 与 live trading 均为 false；
- Model Diagnostic V1 已关闭，不再继续调整历史解释；
- `split_003` 已观察，只能诊断，不能再用于选择。

实时机器状态以以下文件为准：

- `outputs/forward/status.json`
- `outputs/forward/paper_portfolio/status.json`
- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`

## 2. 状态分类

| 状态 | 含义 |
|---|---|
| ACTIVE | 当前允许日常运行或维护的主链 |
| FROZEN | 定义和 evidence 已冻结，只允许验证或修复已证明的 bug |
| CLOSED | 研究阶段已完成，不因一般工程工作重新开启 |
| LEGACY | 为历史复现保留，不是新工作的默认入口 |
| EXPERIMENTAL | 试验能力，不能替代 active/frozen authority |

## 3. ACTIVE — Forward Track

```text
Daily Data Update
        ↓
Frozen 52-feature snapshot
        ↓
Frozen LightGBM prediction
        ↓
Git-bound prediction receipt
        ↓
Strategy V1 paper decision / execution refresh
        ↓
Mature-label evaluation（成熟后独立运行）
```

### 3.1 Daily Data Update

入口：

- `qlib-daily-update` / `qlib_baseline.cli.daily_update`
- `scripts/daily_update.py`（兼容包装器）
- `daily_update/pipeline.py`（orchestration 与兼容 facade）
- `daily_update/sources/`、`provider.py`、`features.py`、`validation.py`
- 配套说明：[DAILY_DATA_UPDATE_V1.md](operations/DAILY_DATA_UPDATE_V1.md)

当前命令：

```powershell
qlib-daily-update --target-date YYYY-MM-DD
```

主要输入：

- Community Qlib release，缺失目标日时使用 BaoStock fallback；
- frozen Strategy V1 universe；
- Qlib/Alpha158/Alpha360、Alpha101、TA 与 project-basic 的既有实现；
- frozen preprocessing 中声明的 52 个 feature names/order。

主要输出：

```text
outputs/daily_data_update_v1/<date>/summary.json
outputs/daily_data_update_v1/<date>/feature_snapshot.csv
outputs/daily_data_update_v1/<date>/<source>_qlib_daily.csv
```

该阶段不运行 prediction、paper portfolio、模型训练或标签评价。

### 3.2 Frozen Forward Prediction

入口：

- `qlib-forward-predict` / `qlib_baseline.cli.forward_predict`
- `scripts/run_forward_prediction_v1.py`（兼容包装器）
- `daily_update/forward_adapter.py`
- `model_research/forward_pipeline.py`（兼容 facade）
- `model_research/forward_prediction.py`
- `model_research/forward_binding.py`
- `model_research/forward_state.py`

从 Daily Update 消费一天数据：

```powershell
qlib-forward-predict `
  --date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt `
  --daily-update-dir outputs/daily_data_update_v1/YYYY-MM-DD
```

第一步生成 pending prediction 后，必须在 cutoff 前提交 prediction payload；随后用
真实 40 位 commit SHA 完成 receipt：

```powershell
qlib-forward-predict `
  --date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt `
  --finalize-commit <40-char-commit-sha>
```

关键限制：

- prediction 阶段不接受 label 路径；
- feature order、model 和 preprocessing hash 必须匹配 freeze；
- official 日期、raw first-seen、prediction 和 commit timestamp 必须满足冻结及
  t+1 09:25 Asia/Shanghai cutoff；
- 同一 official 日期不得覆盖；
- `--dry-run` 只能写独立 dry-run 目录，不能产生 eligible evidence。

主要 evidence：

```text
outputs/forward/predictions/<date>/prediction.csv
outputs/forward/predictions/<date>/prediction_receipt.json
outputs/forward/status.json
```

### 3.3 Strategy V1 Paper Portfolio

入口：

- `qlib-paper-portfolio` / `qlib_baseline.cli.paper_portfolio`
- `scripts/run_paper_portfolio_v1.py`（兼容包装器）
- `model_research/paper_portfolio.py`
- `configs/strategy_v1_paper_portfolio_v1.yaml`
- 配套说明：[STRATEGY_V1_PAPER_PORTFOLIO_V1.md](operations/STRATEGY_V1_PAPER_PORTFOLIO_V1.md)

创建 decision：

```powershell
qlib-paper-portfolio `
  --date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt
```

仅推进已存在 decision 的执行状态：

```powershell
qlib-paper-portfolio --refresh-only
```

Paper Portfolio 只消费 committed official prediction。执行日数据尚未到达时必须保持
`pending_execution`，不得伪造 trade、position 或 NAV。

### 3.4 Mature Label Update

入口：

- `qlib-forward-label-update` / `qlib_baseline.cli.forward_label_update`
- `qlib-forward-status` / `qlib_baseline.cli.forward_status`
- `scripts/update_forward_labels_v1.py`、`scripts/show_forward_status_v1.py`
  （兼容包装器）
- `model_research/forward_labels.py`
- `model_research/forward_state.py`

```powershell
qlib-forward-label-update `
  --as-of-date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt `
  --label-dir data/forward/labels

qlib-forward-status
```

标签未成熟时不得打开 label 文件；评价只消费已完成 Git binding 的 prediction。

## 4. FROZEN — 不得一般性修改

### Strategy V1 Candidate

```text
Model:        LightGBM
Features:     frozen ordered 52-factor input
Portfolio:    P01, Long Only Top50, equal weight
Rebalance:    every 5 trading days
Evidence:     personal research grade
```

权威入口：

- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`
- `artifacts/prospective_forward_candidate_v1/sha256/`
- `configs/strategy_v1_paper_portfolio_v1.yaml`
- `outputs/historical_portfolio_backtest_v1/current/selected_portfolio_rule.json`

未经单独研究授权，不得改变模型、特征、预处理、TopK、调仓、费用或执行规则。

### Historical Research Evidence

- Matrix v4、Labels v2 与 corrected selection chain；
- frozen LightGBM historical predictions；
- Historical Portfolio Backtest V1；
- Strategy V1 已生成的 forward/paper evidence。

工程等价验证只能读取或复制到临时目录，不能覆盖这些对象。

## 5. CLOSED

- Historical Model Comparison V1；
- Historical Portfolio Backtest V1 的选择阶段；
- Model Diagnostic V1；
- External PIT Style Data V1 与 Style Attribution Extension；
- ML Feature Pool MVP V1（A/B/C historical diagnostic）；
- Performance Optimization V1；
- Research Productivity V1（Fast Research 仅 screening-only）；
- Clustering Ablation V1（mixed historical diagnostic，representative gate 不变）；
- 历史 Accuracy Correction、Data Source Audit 和 execution semantics 修正阶段。

CLOSED 阶段只允许修复可证明的数据错误、泄漏、contract failure 或实现 bug；一般
维护不得借机产生新策略结论。

近期四个阶段的详细结论只在相应 final reports 中维护，入口见
[DOC_INDEX.md](DOC_INDEX.md)。它们不产生 production winner、Strategy V2 authorization
或新的 unbiased holdout estimate。

## 6. LEGACY / HISTORICAL

以下内容保留用于复现和历史证据，但不是当前默认入口：

- V1/V2/V3/V3.3/V3.4/V3.5/V4 因子研究 scripts；
- 历史 Alpha158/Alpha101/Alpha360/TA batch 与 promotion runners；
- 旧模型研究、readiness、freeze、audit 和 validation scripts；
- `docs/_archive/` 及对应 tracked outputs。

不要仅因为文件名版本较高就将其视为 active。历史代码和对应 evidence 保持原位；
只有 CLOSED/HISTORICAL Markdown 已按文档生命周期归档。

## 7. EXPERIMENTAL / DEFERRED

- Factor Universe V2 已完成 [774 因子 research-only 目录](../reports/factor_universe_v2/REPORT.md)
  与 [Historical Data & Matrix Readiness](../reports/factor_universe_v2_matrix_readiness/REPORT.md)：
  2021-02-01 至 2026-06-09 的 2,587,671 个 PIT keys 中，770 个定义可物化、765 个
  research-usable、9 个明确 blocked；669 个 V1 因子分区保持字节级不变，Matrix
  Readiness 阶段现为 CLOSED。该结果只允许
  qualified list 进入后续独立的 Economic Multi-Factor Research，不修改 Strategy V1、
  Forward Track，也不授权 Strategy V2；
- 这里的 765 个 research-usable 因子是全局物理数据合格候选集，不是所有 outer split
  固定使用的 feature whitelist；任何带时间依赖的 eligibility、选择、IC 或模型输入仍须
  development-only、split-local，不能利用后期 coverage/availability 决定早期 membership；
- KunQuant 作为未来 factor computation backend；
- Strategy V2 / Model V2 Research Protocol；
- shadow trading、小资金或 live trading；
- broker gateway、服务化、调度平台和分布式工程。

这些方向没有当前实施授权。

## 8. 当前验证入口

本地与 CI 使用统一入口：

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

`fast` 是有限 Ruff scope 与 settings/cache/active-entry tests；`full` 是完整 pytest 与
既有 compact/synthetic validators；`qlib` 是临时 synthetic provider 上的 Qlib
Exchange runtime tests。完整分层与路径触发政策见 [CI_POLICY.md](CI_POLICY.md)。

Forward Track 的当前针对性基线：

```powershell
E:\anaconda_envs\qlib_env\python.exe -m pytest -q `
  tests/test_daily_update.py `
  tests/test_daily_forward_adapter.py `
  tests/test_forward_pipeline.py `
  tests/test_forward_prediction_contract.py `
  tests/test_paper_portfolio.py `
  tests/test_ci_policy.py `
  tests/test_config_parsing.py `
  tests/test_imports.py
```

该 targeted 列表用于 Forward 局部调试；交付仍以适用的统一 quality tier 为准。

## 9. CLOSED — Engineering Refactor

Phase 0–6 工程重构已在
`b46b4f614f3be5388bf7a26ebf2b035d14906f5f` 形成最终绿色基线并关闭。不存在隐式
Phase 7；历史 closeout 与旧计划保存在
[`_archive/08_engineering_refactor/`](_archive/08_engineering_refactor/)，不再是当前执行入口。

当前工程基础包括：

- editable `pyproject.toml`；
- `qlib_baseline.settings.ProjectSettings`；
- portable `configs/project.yaml` 与 ignored local override；
- `qlib-doctor`；
- 无 pandas 依赖的 atomic path/text/JSON I/O helper；
- 弱缓存使用的分层 fingerprint、规范化 AST hash、Parquet 与 sidecar helper；
- 五个安装式 Forward Track CLI；
- 只转发到 packaged CLI 的旧活动 scripts；
- Daily Update 与 Forward Pipeline 的职责拆分及兼容 facade；
- 目录级 output policy 和 official Forward evidence allowlist；
- 三个批准弱缓存的分层 fingerprint、Parquet 与 sidecar；
- 统一 `fast`、`full`、`qlib` quality runner 与路径感知 CI。

活动 CLI 默认路径现在来自 Project Settings；显式日常业务参数和底层 pipeline
contract 保持不变。旧 scripts 不再包含本机绝对路径或 `sys.path.insert`，但仍可在
editable install 后作为兼容入口使用。

Strategy V1、模型/预处理 hash、52 因子顺序、append-only evidence、Matrix v4、raw
snapshot、lineage 和历史 outputs/artifacts 均未因该重构改变。
