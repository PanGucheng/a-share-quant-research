# Project Context Summary

本文件用于在新会话中快速恢复当前上下文。详细历史不在此重复，统一从
[DOC_INDEX.md](DOC_INDEX.md) 进入 archive 或冻结 outputs。

## Project Positioning

- 展示名称：`A-Share Quant Research` / `A 股量化研究框架`。
- 当前 repository：
  [PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)。
- personal、research-first 的中国 A 股量化研究项目；Microsoft Qlib 是主要底层框架，
  不是整个项目身份。
- 用于 Qlib 因子、模型、组合与 genuine forward research。
- 不是机构平台、合规系统、生产交易基础设施或实盘服务。
- 优先级是研究逻辑正确、无未来数据、train/validation/test 隔离、可解释、易维护、
  有用自动化；额外工程治理必须证明成本收益。

权威研究路线为
[PERSONAL_QUANT_RESEARCH_ROADMAP.md](PERSONAL_QUANT_RESEARCH_ROADMAP.md)。

## Current Authority

按顺序阅读：

1. [CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) — ACTIVE/FROZEN/CLOSED 状态与命令；
2. [CANONICAL_RESEARCH_DATASET.md](CANONICAL_RESEARCH_DATASET.md) — 后续 Dataset / Protocol
   research 的唯一推荐 Matrix identity 与读取合同；
3. [RESEARCH_PROTOCOL_V2.md](RESEARCH_PROTOCOL_V2.md) — 下一阶段模型研究的冻结时间与证据边界；
4. [ARCHITECTURE.md](ARCHITECTURE.md) — 当前模块和依赖边界；
5. [OUTPUT_POLICY.md](OUTPUT_POLICY.md) — 输出、artifact、report、cache 和 Forward evidence；
6. [CI_POLICY.md](CI_POLICY.md) — 本地/CI quality tiers。

`docs/_archive/` 中的计划和回执是 CLOSED/HISTORICAL/SUPERSEDED 证据，不是当前授权。

## Current Data, Factor, And Model Stack

- 数据：community Qlib-format A-share provider、PIT universe/Matrix v4、Labels v2、
  tradability layer；本机路径由 ignored local config 绑定。
- 因子：冻结 669-factor research catalog；rolling stability 与 clustering artifacts 保留
  研究 provenance，Strategy V1 仍只消费冻结的有序 52-feature snapshot。
- 模型：Strategy V1 为冻结 LightGBM；历史 research model protocol、candidate table、
  preprocessing、holdout/freeze/lineage contracts 不因后续诊断而改变。
- 组合：P01，Long Only Top50、等权、每 5 个交易日调仓；forward evidence append-only。

## Active Forward Track

当前时间敏感主线：

```text
Daily Data Update
        ↓
frozen 52-feature snapshot
        ↓
frozen Strategy V1 LightGBM prediction
        ↓
Git-bound official receipt
        ↓
Top50 equal-weight paper decision / execution refresh
        ↓
mature-label evaluation
```

当前 tracked machine status 记录：

- 2026-08-07 official prediction 已完成并等待标签成熟；
- 2026-08-07 paper decision 已完成，计划执行日为 2026-08-10；
- production model selection 与 live trading 均为 false；
- 实时状态以 `outputs/forward/status.json` 和
  `outputs/forward/paper_portfolio/status.json` 为准。

## Frozen And Closed Boundaries

- Strategy V1：LightGBM、固定 52 因子顺序、Long Only Top50 等权、每 5 个交易日调仓。
- `split_003` 已观察，只能诊断，不能重新用于选因子、调参或组合搜索后声称新 OOS。
- 历史 prediction、paper decision、position、trade 和 NAV 不得覆盖。
- Model Diagnostic V1 已 CLOSED；其历史 closeout 位于
  [`_archive/07_research_program_history/MODEL_DIAGNOSTIC_V1_CLOSEOUT.md`](_archive/07_research_program_history/MODEL_DIAGNOSTIC_V1_CLOSEOUT.md)。
- Phase 0–6 工程重构已 CLOSED，最终绿色基线为
  `b46b4f614f3be5388bf7a26ebf2b035d14906f5f`；不存在隐式 Phase 7。历史 closeout
  位于 [`_archive/08_engineering_refactor/`](_archive/08_engineering_refactor/)。
- Matrix v4、raw snapshot manifest、lineage 和全部历史研究结果保持冻结。
- Research Protocol V2 已在模型 outcomes 前冻结；5 个 development environments 可用于
  后续受限诊断，7 个细粒度历史环境及旧三个 test 只能诊断。后续独立的 Dataset &
  Validation Design Study 发现 35–43 日 folds 的 temporal ESS 不足，不能直接作为正式
  Structured ML selection authority；正式竞争尚未开始。

## Recent Research Conclusions

- **Economic Multi-Factor Research V1 — CLOSED / diagnostic-only**：765 个物理合格
  因子完成经济机制映射；11 个 sleeves 与 7 个有限 archetypes 使用 split-local
  eligibility 和固定 P01 诊断。投机/反转历史排序较强但成本高，流动性带显著小盘暴露，
  6 个预注册增量链均未在三个 split 同时通过两项互补检验。详见
  [final report](../reports/economic_multi_factor_research_v1/REPORT.md)。
- **ML Feature Pool MVP V1 — CLOSED / diagnostic-only**：strict pool 可能偏窄，较宽
  输入有部分历史增量，但 broad pool 稳定性下降。详细数字见
  [final report](../reports/ml_feature_pool_mvp_v1/REPORT.md)。
- **Performance Optimization V1 — CLOSED**：保留 authoritative-compatible 的
  single-thread/float64 语义；不满足数值 parity 的线程加速未被采用。详见
  [final report](../reports/performance_optimization_v1/REPORT.md)。
- **Research Productivity V1 — CLOSED**：Projection/Spool cache 已可审计复用；Fast
  Research 只能筛掉明显无希望的 proposal，不能选 winner。详见
  [final report](../reports/research_productivity_v1/REPORT.md)。
- **Clustering Ablation V1 — CLOSED / diagnostic-only**：移除每簇单 representative
  hard gate 的历史结果 mixed；新增成员确被 LightGBM 使用，但没有跨 split 一致改善，
  所以 gate 保持不变。详见
  [final report](../reports/ml_clustering_ablation_v1/REPORT.md)。
- **Historical Dataset & Validation Design Study V1 — RESEARCH COMPLETE**：2021 起点是
  工程 scope 继承，不是已证明的数据源硬限制；40 日 validation 的 market-level label
  ESS 约 2.6。后续候选应先扩展历史，并研究 120–252 日、4–6 个较长 chronological
  environments。详见 [final report](../reports/historical_dataset_validation_design_v1/REPORT.md)。
- **Maximum Historical Extension & Qualification V1 — QUALIFICATION COMPLETE**：复用
  Community Qlib、Tushare、BaoStock、AkShare 与既有缓存完成真实多源审计；技术
  price-volume 可追溯至 2000-01-04，但共同 full-feature frontier 受 PIT row-cap、
  revision、lifecycle 与 adjustment 证据限制，未生成 extended Matrix。详见
  [final report](../reports/maximum_historical_extension_qualification_v1/REPORT.md)。
- **Historical Frontier Admission V1 — MARKET-LEVEL QUALIFICATION COMPLETE**：按上市
  cohort 与 listed/delisted 状态分层抽样 28 个 issuer，并对 48 个季度代表交易日做
  daily_basic/moneyflow 覆盖、2010–2017 statement PIT、lifecycle 交集和 adjustment
  continuity canary。daily_basic/moneyflow 稳定尾部候选为 2016-07-01，但 PIT row-cap
  与 lifecycle vintage 仍阻断 Full V2；未生成 extended Matrix。详见
  [final report](../reports/historical_frontier_admission_v1/REPORT.md)。
- **Historical Data Engineering Extension V1 — MATRIX GENERATED / PARTIAL EXTENSION**：
  practical reconstructed PIT 与 practical historical universe 已实际 materialize 为独立
  Extended Matrix，覆盖 2000-11-01 至 2021-01-29、8,014,460 PIT keys、4,913 dates、
  3,874 instruments，2000–2009 为 733 因子层，2010-01-29 起为 774 因子层。分区完整性、
  VPT/NVI/ADI/OBV 跨年度状态、PIT 和 universe overlap 均通过；frozen-parent overlap
  key set 一致，但 36 因子仍有值级 lineage 差异，故状态为 `partial_extension`，不得启动
  Structured ML。详见 [final report](../reports/historical_data_engineering_extension_v1/REPORT.md)。
- **Extended Matrix Overlap Lineage Resolution V1 — LINEAGE RESOLVED**：剩余 36 个
  overlap residual 已逐因子归因；739/774 exact、35 explained、0 quarantined。15 个
  Alpha101 修正 dated PIT rank scope，KAMA 改为因果连续状态，KCP comparator 修复，
  19 个 Fundamental residual 作为已公开历史 source-window 差异保留。新 Matrix identity
  为 `extended-matrix:22fbf692d22e97a90d3b63ad1258f4867be38f5476494e27fbf68d5825cc38f0`；
  旧 frozen 与 partial-extension 均保持 immutable。详见
  [final report](../reports/extended_matrix_overlap_lineage_resolution_v1/REPORT.md)。
- **Canonical Historical Dataset Assembly V1 — AUTHORITY / DATA ENGINEERING CLOSED**：
  lineage-resolved history 与 corrected continuation 已组成 2010-01-29 至 2026-06-09 的唯一
  推荐 research input：
  `canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`。
  2021+ 重算 15 个 Alpha101、causal KAMA 和 19 个 Fundamental，其他 739 个因子沿用已证明
  一致的 semantics；765/774 research-usable，9 个 blocked。PIT、universe、state、timeline、
  boundary、partition 与 old artifact immutability 全通过，0 unexplained mismatch。Historical
  Data Engineering 已 CLOSED；详见 [authority](CANONICAL_RESEARCH_DATASET.md) 与
  [final report](../reports/canonical_historical_dataset_assembly_v1/REPORT.md)。

这些已观察历史结果不能被描述为 fresh OOS，也不能授权修改 Strategy V1 或创建
Strategy V2。

## Immediate Next Research Direction

Forward Track 继续具有时间优先级。Factor Universe V2 已冻结为 research-only 的
774 因子目录，历史 bootstrap、V2 Matrix readiness 与 Economic Multi-Factor Research
V1 均已完成并关闭。Research Protocol V2 artifact 保持冻结，但 Historical Dataset &
Validation Design Study 已证明不能直接沿用其短 folds 启动正式模型竞争。下一研究方向
只能以 canonical dataset identity 为输入，另行预注册较长 chronological validation 候选并
设计 Dataset / Research Protocol redesign；当前尚未启动，Structured ML
仍未授权。不得自动切换
Strategy V1、daily paper path 或修改 Forward evidence。

## Environment

当前 Windows 工作站：

```text
repository: E:\qlib_prj\qlib_baseline
Python:     E:\anaconda_envs\qlib_env\python.exe
Qlib:       E:\qlib_prj\qlib_clone
```

机器相关数据路径只进入 ignored `configs/project.local.yaml`。配置和实际 Qlib import
是否一致由以下命令检查：

```powershell
qlib-doctor --strict
```

完整环境说明见 [ENVIRONMENT.md](ENVIRONMENT.md)。

## Active Commands

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

prediction、finalize、cutoff、calendar、label maturity 和 paper refresh 的具体参数以
[CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) 为准。

## Quality Commands

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

Ruff 范围有限，不格式化全仓。CI 不下载完整 A 股数据、不训练模型、不运行完整矩阵或
历史回测。

## Change Discipline

- 先确认目标属于 ACTIVE、FROZEN、CLOSED、LEGACY 还是 EXPERIMENTAL。
- 复用现有业务模块和冻结证据，优先最小修改。
- correctness failure 必须 fail loudly；非关键覆盖缺口可 warning 并记录限制。
- 新研究默认采用普通 Python、YAML、CSV/JSON、Markdown 和 focused pytest。
- 新 manager、registry、protocol、gate、manifest 或抽象层必须解决已证明的问题。
- 完成文档变更时检查全仓 Markdown links、`DOC_INDEX`、`git diff --check` 和 fast tier。
