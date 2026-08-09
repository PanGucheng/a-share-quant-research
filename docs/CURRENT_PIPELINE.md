# Current Pipeline

## 1. 权威状态

本文是当前运行入口索引，不替代研究路线、冻结 artifact 或机器状态文件。

截至 2026-08-09：

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
- 配套说明：[DAILY_DATA_UPDATE_V1.md](DAILY_DATA_UPDATE_V1.md)

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
- 配套说明：[STRATEGY_V1_PAPER_PORTFOLIO_V1.md](STRATEGY_V1_PAPER_PORTFOLIO_V1.md)

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
- 历史 Accuracy Correction、Data Source Audit 和 execution semantics 修正阶段。

CLOSED 阶段只允许修复可证明的数据错误、泄漏、contract failure 或实现 bug；一般
维护不得借机产生新策略结论。

## 6. LEGACY / HISTORICAL

以下内容保留用于复现和历史证据，但不是当前默认入口：

- V1/V2/V3/V3.3/V3.4/V3.5/V4 因子研究 scripts；
- 历史 Alpha158/Alpha101/Alpha360/TA batch 与 promotion runners；
- 旧模型研究、readiness、freeze、audit 和 validation scripts；
- `docs/_archive/` 及对应 tracked outputs。

不要仅因为文件名版本较高就将其视为 active。Phase 0 不移动或重命名这些文件。

## 7. EXPERIMENTAL / DEFERRED

- KunQuant 作为未来 factor computation backend；
- Strategy V2 / Model V2 Research Protocol；
- shadow trading、小资金或 live trading；
- broker gateway、服务化、调度平台和分布式工程。

这些方向没有当前实施授权。

## 8. 修改后的验证入口

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

Phase 0 审计时该集合为 `61 passed`。完整 CI 政策见 [CI_POLICY.md](CI_POLICY.md)。

## 9. Engineering Foundation Status

Phase 1–2 已提供：

- editable `pyproject.toml`；
- `qlib_baseline.settings.ProjectSettings`；
- portable `configs/project.yaml` 与 ignored local override；
- `qlib-doctor`；
- 无 pandas 依赖的 atomic path/text/JSON I/O helper。
- 五个安装式 Forward Track CLI；
- 只转发到 packaged CLI 的旧活动 scripts。

活动 CLI 默认路径现在来自 Project Settings；显式日常业务参数和底层 pipeline
contract 保持不变。旧 scripts 不再包含本机绝对路径或 `sys.path.insert`，但仍可在
editable install 后作为兼容入口使用。

Phase 3A 已完成 Daily Update 内部拆分并通过 Regression Gate A。Community/BaoStock
发布时间、bridge 公式、95% coverage、450 日 warmup、52 因子顺序与 fail-closed
语义保持不变。

Phase 3B 已将 Forward Pipeline 拆为 state、binding、prediction 和 mature-label
四个职责模块，原 `forward_pipeline.py` 只保留兼容 re-export。Strategy V1、模型与
预处理 hash、52 因子顺序、append-only state、commit binding、cutoff、label
maturity 和 paper portfolio contract 均保持不变；Regression Gate B 已通过。
