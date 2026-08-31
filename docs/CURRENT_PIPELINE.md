# Current Pipeline

本文是当前状态与运行入口 authority。详细历史结论只在 reports/archive 维护；目录或
artifact 名称中的 `current` 不自动表示 ACTIVE。

## 1. Status At A Glance

| 对象 | 状态 | 允许行为 |
|---|---|---|
| Forward Track | ACTIVE / time-priority | 日常 update、冻结 prediction、paper refresh、成熟标签评价 |
| Strategy V1 | FROZEN | 运行、验证；不得重训或修改定义 |
| Canonical Research Dataset | FROZEN AUTHORITY / READY | 新 Dataset / Protocol research 的唯一推荐输入 |
| Historical Data Engineering | CLOSED | 仅因明确 data bug、leakage 或 provenance failure 重开 |
| Prior Research Protocol V2 | FROZEN HISTORICAL EVIDENCE | 可审计复现；不可直接授权模型竞争 |
| Dataset / Research Protocol Redesign | NEXT / NOT STARTED | 需单独任务授权与预注册 |
| Structured ML | NOT AUTHORIZED | 不得训练或比较候选模型 |
| Strategy V2 | NOT AUTHORIZED | 需要独立 protocol、freeze date 与新 forward evidence |
| Live trading | NOT AUTHORIZED | 不属于当前范围 |

机器实时状态以以下文件为准：

- `outputs/forward/status.json`；
- `outputs/forward/paper_portfolio/status.json`；
- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`。

当前 machine evidence 仍记录 2026-08-07 official prediction 和 paper decision；标签成熟、
execution 状态、production/live flags 必须直接读取上述 JSON，不在文档中复制维护。

## 2. ACTIVE — Forward Track

```text
Daily Data Update
        ↓
Frozen 52-feature snapshot
        ↓
Frozen Strategy V1 LightGBM prediction
        ↓
Git-bound official receipt
        ↓
Top50 equal-weight paper decision / execution refresh
        ↓
Mature-label evaluation (separate, after maturity)
```

Forward evidence 具有时间优先级且不可事后回填。所有 prediction、decision、position、trade
与 NAV 服从 append-only 边界。

### 2.1 Daily Data Update

入口：

- `qlib-daily-update` / `qlib_baseline.cli.daily_update`；
- `scripts/daily_update.py`（兼容 wrapper）；
- `daily_update/`；
- [Daily Data Update contract](operations/DAILY_DATA_UPDATE_V1.md)。

```powershell
qlib-daily-update --target-date YYYY-MM-DD
```

该阶段只生成并验证目标日数据及冻结 52-feature snapshot，不运行 prediction、模型训练、
paper portfolio 或标签评价。

### 2.2 Frozen Forward Prediction

入口：

- `qlib-forward-predict` / `qlib_baseline.cli.forward_predict`；
- `scripts/run_forward_prediction_v1.py`（兼容 wrapper）；
- `daily_update/forward_adapter.py`；
- `model_research/forward_prediction.py`、`forward_binding.py`、`forward_state.py`。

```powershell
qlib-forward-predict `
  --date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt `
  --daily-update-dir outputs/daily_data_update_v1/YYYY-MM-DD

qlib-forward-predict `
  --date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt `
  --finalize-commit <40-char-commit-sha>
```

关键合同：

- prediction 阶段不得读取 label；
- feature order、model 和 preprocessing hash 必须匹配 freeze；
- first-seen、prediction、commit timestamp 和 cutoff 必须合法；
- 同一 official date 不得覆盖；
- `--dry-run` 不能产生 eligible evidence。

Official evidence：

```text
outputs/forward/predictions/<date>/prediction.csv
outputs/forward/predictions/<date>/prediction_receipt.json
outputs/forward/status.json
```

### 2.3 Strategy V1 Paper Portfolio

入口：

- `qlib-paper-portfolio` / `qlib_baseline.cli.paper_portfolio`；
- `scripts/run_paper_portfolio_v1.py`（兼容 wrapper）；
- `model_research/paper_portfolio.py`；
- [Paper Portfolio contract](operations/STRATEGY_V1_PAPER_PORTFOLIO_V1.md)。

```powershell
qlib-paper-portfolio `
  --date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt

qlib-paper-portfolio --refresh-only
```

Portfolio 只消费 committed official prediction。执行日数据未到达时必须保持
`pending_execution`，不得伪造 trade、position 或 NAV。

### 2.4 Mature Label Update And Status

入口：

- `qlib-forward-label-update` / `qlib_baseline.cli.forward_label_update`；
- `qlib-forward-status` / `qlib_baseline.cli.forward_status`；
- `model_research/forward_labels.py`、`forward_state.py`。

```powershell
qlib-forward-label-update `
  --as-of-date YYYY-MM-DD `
  --calendar-file <provider>/calendars/day_future.txt `
  --label-dir data/forward/labels

qlib-forward-status
```

标签未成熟时不得打开 label 文件；评价只消费已完成 Git binding 的 official prediction。

## 3. FROZEN — Strategy V1 And Evidence

Strategy V1：

```text
Model:        LightGBM
Features:     frozen ordered 52-factor input
Portfolio:    P01, Long Only Top50, equal weight
Rebalance:    every 5 trading days
Evidence:     personal research grade
```

权威机器入口：

- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`；
- `artifacts/prospective_forward_candidate_v1/sha256/`；
- `configs/strategy_v1_paper_portfolio_v1.yaml`；
- `outputs/historical_portfolio_backtest_v1/current/selected_portfolio_rule.json`。

未经单独授权，不得改变模型、特征、预处理、TopK、调仓、费用或执行规则。
`split_003` 已观察，只能诊断。Matrix v4、Labels v2、历史 predictions/backtests、manifests、
lineage、receipts 和已生成 Forward evidence 均保持 immutable/append-only。

## 4. FROZEN AUTHORITY — Canonical Research Dataset

新的 Dataset / Research Protocol research 必须绑定：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

- 日期范围：`2010-01-29` 至 `2026-06-09`；
- definitions / research-usable / blocked：774 / 765 / 9；
- 读取 `partition_manifest.csv` 时必须执行 `effective_start` / `effective_end` filters；
- old frozen Matrix、partial extension、lineage-resolved intermediate Matrix 只作 parent
  provenance 和 historical evidence。

机器入口：

- `outputs/canonical_historical_dataset_assembly_v1/current/manifest.json`；
- `outputs/canonical_historical_dataset_assembly_v1/current/partition_manifest.csv`；
- `outputs/canonical_historical_dataset_assembly_v1/current/factor_lineage.csv`。

完整合同见 [Canonical Research Dataset](CANONICAL_RESEARCH_DATASET.md)。不得因文档清理、
协议设计或模型研究覆盖 canonical partitions 或旧 parent evidence。

## 5. CLOSED — Historical Research And Engineering

Historical Data Engineering 已正式 `CLOSED`。其 qualification、frontier admission、authority
resolution、engineering extension、overlap lineage resolution 和 canonical assembly 已被最终
data authority 吸收，不再逐项作为 current todo。

以下类别同样 CLOSED：

- Historical model comparison、portfolio selection 与 Model Diagnostic V1；
- External PIT Style / attribution；
- Economic Multi-Factor、ML Feature Pool、Performance Optimization、Research
  Productivity、Clustering Ablation；
- Factor Universe V2 catalog 与 Matrix readiness；
- Accuracy Correction、Data Source Audit、execution semantics 与 Phase 0–6 refactor。

详细结论从 [DOC_INDEX.md](DOC_INDEX.md) 进入 reports/archive。CLOSED 阶段只能因可证明的
数据错误、泄漏、contract failure 或实现 bug 重开；历史 reports 保持“当时发生了什么”，
不因 current authority 变化而改写。

## 6. NEXT / NOT STARTED — Dataset And Protocol Redesign

Prior Research Protocol V2 在模型 outcomes 前冻结，保留为
[historical protocol evidence](_archive/07_research_program_history/RESEARCH_PROTOCOL_V2.md)。
后续 Dataset & Validation Design Study 已证明其短 development environments 虽满足 leakage
isolation，但 temporal ESS 不足，不能直接作为正式 Structured ML selection authority。

下一研究阶段是单独授权的 Dataset / Research Protocol redesign。它必须以 canonical dataset
identity 为输入，重新预注册 validation/training-history hypotheses 和 evidence roles。当前：

```text
redesign started = false
Structured ML started = false
model outcomes read for redesign = false
Strategy V1 changed = false
Strategy V2 authorized = false
```

本状态只说明“下一步是什么”，不授权设计 windows、运行 ESS study、训练模型或创建 Protocol V3。

## 7. LEGACY / EXPERIMENTAL

- `research_validation/purged_split.py`、`development_split.py`：legacy reproduction；
- prior protocol generator/config/report：frozen historical evidence；
- historical scripts/configs/outputs：按需复现，不是默认入口；
- Fast Research：screening-only，不能选择 winner；
- alternative factor/model adapters：只有 current task 明确授权时使用。

## 8. Quality And Documentation

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

文档变更还应运行全仓 Markdown link audit、repository documentation check 和
`git diff --check`。若 `full` 仅因 immutable historical manifest schema blocker 失败，记录
该 blocker，不得为了绿色而改写旧 frozen artifact。
