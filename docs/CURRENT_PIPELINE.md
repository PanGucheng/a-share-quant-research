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

### Canonical Research Dataset Authority

后续 Dataset / Research Protocol research 必须显式绑定
`canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`，
覆盖 `2010-01-29` 至 `2026-06-09`。机器入口为
`outputs/canonical_historical_dataset_assembly_v1/current/manifest.json` 与
`partition_manifest.csv`；读取时必须执行 manifest 的 effective date filters。

该 dataset 统一使用 PIT-rank Alpha101、causal KAMA、practical reconstructed PIT 和 practical
historical universe。774 个 definitions 中只有 765 个是 global physical-data-qualified candidates，
9 个仍 blocked。旧 frozen、partial-extension 和 lineage-resolved historical Matrix 只保留为
immutable evidence，不是新研究默认输入。完整合同见
[Canonical Research Dataset Authority](CANONICAL_RESEARCH_DATASET.md)。

## 5. CLOSED

- Historical Model Comparison V1；
- Historical Portfolio Backtest V1 的选择阶段；
- Model Diagnostic V1；
- External PIT Style Data V1 与 Style Attribution Extension；
- ML Feature Pool MVP V1（A/B/C historical diagnostic）；
- Performance Optimization V1；
- Research Productivity V1（Fast Research 仅 screening-only）；
- Clustering Ablation V1（mixed historical diagnostic，representative gate 不变）；
- Economic Multi-Factor Research V1（765 因子经济映射、11 sleeves、7 archetypes、
  split-local eligibility 与固定 P01 历史诊断；无稳定三段增量链，不选择 winner）；
- Historical Dataset & Validation Design Study V1（2021 起点 lineage、历史数据能力、
  validation dependence/ESS 与 regime coverage；只形成设计候选，未选择新 split）；
- Maximum Historical Extension & Qualification V1（多源最大历史探测与 frontier qualification；
  技术 price history 可至 2000，但共同 full-feature frontier 尚未获准，未生成 extended Matrix）；
- Historical Frontier Admission V1（市场级 canary：28 个分层 issuer、48 个季度代表日、
  daily_basic/moneyflow 覆盖、PIT row-cap、lifecycle 交集与 adjustment continuity；
  稳定尾部候选 2016-07-01，但 PIT/lifecycle gates 阻断 Full V2，未生成 extended Matrix）；
- Historical Data Authority Resolution V1（对 Qlib interval、Tushare stock_basic/namechange、
  Tushare/BaoStock dated presence 做 authority reconciliation；以 exact `period=YYYYMMDD`
  加 offset pagination 证明 2010–2017 statement endpoint retrieval 可穷尽，但 provider
  vintage 与 historical lifecycle 仍未证明；daily_basic/moneyflow 只保留 candidate，未生成
  extended Matrix）；
- Historical Data Engineering Extension V1（采用 practical reconstructed PIT / practical
  historical universe 实际构建独立 Extended Matrix；2000-11-01 至 2021-01-29 共
  8,014,460 PIT keys，733/774 分层历史；分区、连续累计状态、PIT 与 universe overlap
  通过，但 frozen-parent value overlap 仍有 36 因子差异，故状态为 `partial_extension`，
  不进入 Structured ML）；
- Extended Matrix Overlap Lineage Resolution V1（对 36 个 residual 完成逐因子 root-cause
  决策；15 个 Alpha101 采用 dated PIT rank scope，KAMA 改为因果连续状态，KCP 修复
  infinity comparator，19 个 Fundamental residual 记录 source-window provenance；新
  versioned Matrix 为 `lineage_resolved`，739 exact / 35 explained / 0 quarantined）；
- Canonical Historical Dataset Assembly & Data Engineering Closure V1（组装
  2010-01-29 至 2026-06-09 的语义连续 canonical dataset；2021+ 重算 15 个 Alpha101、
  causal KAMA 与 19 个 Fundamental，其余只引用已证明一致的 frozen partitions；PIT、universe、
  state、boundary、partition 和 old-artifact immutability 全通过；Historical Data Engineering
  正式 CLOSED）；
- 历史 Accuracy Correction、Data Source Audit 和 execution semantics 修正阶段。

CLOSED 阶段只允许修复可证明的数据错误、泄漏、contract failure 或实现 bug；一般
维护不得借机产生新策略结论。

## 5.1 FROZEN — Research Protocol V2

[Research Protocol V2](RESEARCH_PROTOCOL_V2.md) 已在任何 Structured ML V1 正式模型
竞争前单独冻结。它提供 5 个 development selection environments、7 个
`historical_diagnostic_only` environments、两个训练历史假设（expanding / 504 日
sliding）和 exact `[t+1,t+21]` interval purge。

当前只允许后续任务按该协议注册并运行 development candidate；本阶段的所有 task
模板保持 `execution_authorized=false`。旧三个 historical tests 继续是 legacy
diagnostic anchors，Forward Track 和 Strategy V1 均未改变。

[Historical Dataset & Validation Design Study V1](../reports/historical_dataset_validation_design_v1/REPORT.md)
在不读取 Structured ML outcomes 的前提下发现：当前 35–43 个可用日期的 development
folds 虽满足 leakage isolation，但 temporal ESS 不足，不能直接作为正式模型竞争的选择
authority。Research Protocol V2 artifact 保持冻结；正式 Structured ML 继续 deferred，
后续须先完成 bounded 历史扩展，并另行预注册 120–252 日、4–6 个较长顺序环境的候选研究。

[Maximum Historical Extension & Qualification V1](../reports/maximum_historical_extension_qualification_v1/REPORT.md)
已实际探测 Community Qlib、Tushare、BaoStock 与 AkShare：price-volume 技术历史从
2000-01-04 可获得，Tushare/BaoStock/Qlib 在代表性长期上市样本的 raw close/volume/amount
轴已完成数量级对齐；但 statement responses 存在 row cap、早期 PIT vintage 完整性和
corporate-action/lifecycle 语义仍未充分证明。因此只保留 frontier map，extended Matrix
继续不生成，Protocol/model stages 继续 deferred。

[Historical Data Engineering Extension V1](../reports/historical_data_engineering_extension_v1/REPORT.md)
已将资格化证据落实为独立、可追溯的分区 Matrix：长期 price-volume 层从 2000-11-01
开始，774 因子共同层从 2010-01-29 开始，历史端点为 frozen parent 前一交易月的
2021-01-29。Extended Matrix 已生成且连续状态验证通过；2021-02-01 至 2021-03-31
overlap key set 完全一致，但 Alpha101 为主的 36 个因子仍有值差异，保留为显式 blocker，
不修改 frozen parent 或 Protocol V2，也不启动模型竞争。

[Extended Matrix Overlap Lineage Resolution V1](../reports/extended_matrix_overlap_lineage_resolution_v1/REPORT.md)
已关闭该 blocker：所有 36 个 residual 均完成可审计归因，未通过复制旧实现 bug 或放宽
tolerance 强求完全一致。新 identity 为
`extended-matrix:22fbf692d22e97a90d3b63ad1258f4867be38f5476494e27fbf68d5825cc38f0`；
762 个分区完整性、PIT、universe 与连续状态门禁继续通过。该 artifact 已具备作为后续
Dataset / Research Protocol redesign 输入的 lineage 条件，但 redesign 和 Structured ML
仍须单独授权，当前均未启动。

[Canonical Historical Dataset Assembly & Data Engineering Closure V1](../reports/canonical_historical_dataset_assembly_v1/REPORT.md)
已将上述 lineage-resolved history 与 corrected 2021–2026 continuation 组装为新的数据 authority：
`canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`。
它是后续 Dataset / Protocol research 的唯一推荐 Matrix 输入；旧 artifacts 继续 immutable。
Historical Data Engineering 已 CLOSED，只能因明确 data bug、leakage 或 provenance failure 重开。
Dataset / Research Protocol redesign 与 Structured ML 仍未启动。

近期阶段的详细结论只在相应 final reports 中维护，入口见
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
  Readiness 阶段现为 CLOSED。qualified list 已由独立的
  [Economic Multi-Factor Research V1](../reports/economic_multi_factor_research_v1/REPORT.md)
  完成经济映射与历史诊断；该阶段同样 CLOSED，不修改 Strategy V1、Forward Track，
  也不授权 Strategy V2；
- 这里的 765 个 research-usable 因子是全局物理数据合格候选集，不是所有 outer split
  固定使用的 feature whitelist；任何带时间依赖的 eligibility、选择、IC 或模型输入仍须
  development-only、split-local，不能利用后期 coverage/availability 决定早期 membership；
- KunQuant 作为未来 factor computation backend；
- Strategy V2；
- Structured ML V1 正式模型竞争（Research Protocol V2 已冻结；Dataset & Validation
  Design、historical extension 和 canonical assembly 已完成数据准备，但 Dataset / Research
  Protocol redesign 尚未单独启动，竞争仍未开始）；
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
