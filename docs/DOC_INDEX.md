# Documentation Index

本文件是仓库文档的权威入口。`docs/` 顶层只保留当前 authority/governance；仍在
执行的操作契约位于 `docs/operations/`；已完成、历史或 provenance 文档位于
`docs/_archive/`。

当前项目展示名称为 `A-Share Quant Research` / `A 股量化研究框架`，repository 为
[PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)。
旧 repository 名 `PanGucheng/qlib-baseline` 已永久退役，不得重新创建，以免破坏
GitHub rename redirect。

## Authority Order

发生冲突时按以下顺序判断：

1. `AGENTS.md` 的研究与修改纪律；
2. 当前路线与运行入口；
3. 当前架构、输出、CI 和环境政策；
4. 冻结 artifacts、machine status、receipts 和 manifests；
5. archive 中的历史计划和阶段回执。

Archive 保留证据，但不授权恢复已关闭工作。

## Current Authority

- `DOC_INDEX.md`
  本导航入口；不与其他 current 文档竞争其具体职责。
- `PROJECT_CONTEXT_SUMMARY.md`
  面向新会话的紧凑上下文，不承载逐阶段历史流水账。
- `CURRENT_PIPELINE.md`
  ACTIVE、FROZEN、CLOSED、LEGACY、EXPERIMENTAL 状态，Forward Track 命令与机器状态入口。
- `PERSONAL_QUANT_RESEARCH_ROADMAP.md`
  当前研究路线与不可放松的时间隔离、holdout 和 Strategy V1/V2 边界。
- `ARCHITECTURE.md`
  当前领域边界、依赖方向、settings/runtime、weak cache 和保留治理职责。
- `OUTPUT_POLICY.md`
  `outputs/`、`artifacts/`、`reports/`、`tmp/`、cache 与 official Forward evidence 的落盘政策。
- `CI_POLICY.md`
  本地/CI 共用的 `fast`、`full`、`qlib` 质量层及路径分类。
- `ENVIRONMENT.md`
  portable project settings、local override、doctor、Python/Qlib 与依赖环境。

## Operational References

- `operations/DAILY_DATA_UPDATE_V1.md`
  Daily Update 数据源、发布时间、fallback、覆盖率和输出契约。
- `operations/STRATEGY_V1_PAPER_PORTFOLIO_V1.md`
  冻结 Strategy V1 paper decision、执行刷新、持仓和 NAV 记录规则。
- `operations/UNIVERSE_POLICY.md`
  A 股 universe、动态 membership 和生命周期语义。
- `operations/TRADABILITY_LABEL_LAYER.md`
  可交易性标签字段与 fail-closed 边界。

## Repository Entry Documents

- `../README.md`
  英文项目入口与最小运行导航。
- `../README.zh-CN.md`
  中文项目入口与最小运行导航。
- `../data_quality/README.md`
  数据质量模块说明。
- `../tradability/README.md`
  可交易性模块说明。
- `../reports/README.md`
  compact human-readable reports 的目录政策。

## Current Machine Evidence

文档不覆盖机器状态。Forward Track 当前状态以这些 append-only 或受控文件为准：

- `outputs/forward/status.json`
- `outputs/forward/paper_portfolio/status.json`
- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`

历史研究 outputs 仍是冻结证据，但不能仅因目录名含 `current` 就视为 ACTIVE pipeline。

## Completed Recent Research

以下阶段均为 CLOSED。报告负责详细数字，current docs 只保留当前结论：

- [ML Feature Pool MVP V1](../reports/ml_feature_pool_mvp_v1/REPORT.md)：更宽输入显示部分
  历史增量，但 broad pool 稳定性较弱；仅为 post-observation diagnostic。
- [Performance Optimization V1](../reports/performance_optimization_v1/REPORT.md)：保留精确
  single-thread/float64 研究语义，拒绝不满足数值 parity 的加速方案。
- [Research Productivity V1](../reports/research_productivity_v1/REPORT.md)：Projection/Spool
  content-addressed cache 已实现；Fast Research 仅作资源筛查，不作 winner selection。
- [Clustering Ablation V1](../reports/ml_clustering_ablation_v1/REPORT.md)：取消每簇单代表门槛的
  历史证据 mixed，现有 representative gate 不变。
- [Factor Universe V2 — Pre-Network Checkpoint](../reports/factor_universe_v2/REPORT.md)：完成
  历史缺失/退化审计、Tushare 真实权限探测、PIT/修订与增量缓存基础，以及本地 716
  candidate catalog；按用户边界停止在外部成熟因子网络扩容前，尚未冻结最终 V2。

这些结果不修改 Strategy V1、不产生 Strategy V2 authorization，也不构成 fresh OOS。
Factor Universe V2 后续外部成熟体系扩容仍需单独继续授权。

## Archive Map

- `_archive/README.md`
  归档语义、目录说明和引用规则。
- `_archive/01_early_stage_plans/`
  初始 baseline、Step 1–4、数据与组合早期计划和回执。
- `_archive/02_data_layer_history/`
  首次 data-source upgrade decision、数据快照、字段验证和 provider 能力历史记录。
- `_archive/03_factor_research_history/`
  早期因子研究、算法审计和 V3/V4 设计。
- `_archive/04_alpha158_history/`
  Alpha158 catalog、evaluation、portfolio 与稳定性历史。
- `_archive/05_open_source_factor_batches/`
  TA、Alpha101、Alpha360、多来源 screening/judgement 历史。
- `_archive/06_probe_and_tradeability_audits/`
  probe、strict OOS、tradability exposure 与数据能力审计。
- `_archive/07_research_program_history/`
  已关闭的 full research、accuracy correction、model protocol、historical
  comparison/backtest、Forward MVP 与 Qlib execution 计划和回执。
- `_archive/08_engineering_refactor/`
  CLOSED Phase 0–6 closeout、原始工程优化指南和实施计划。
- `_archive/09_model_research_and_productivity_history/`
  近期已完成模型研究、性能与 productivity 阶段的历史实施计划；final evidence 位于
  `reports/`。

## Documentation Maintenance

- 本轮治理 inventory、归档决策和剩余债务见
  [Documentation Cleanup V1](../reports/documentation_cleanup_v1/REPORT.md)。
- 新文档先判断它是当前 authority、active operational reference，还是一次性历史记录。
- 阶段完成且结论已被当前总线吸收后，移动到 archive，并更新所有路径引用。
- 不在 README 或 `PROJECT_CONTEXT_SUMMARY.md` 重复堆积完整历史时间线。
- 不删除历史研究证据；归档 Markdown 与清理 outputs/artifacts 是完全不同的操作。
- 文档变更完成后运行全量 Markdown link audit、repository documentation check 和
  `python scripts/check_quality.py fast`。
