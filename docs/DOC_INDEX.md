# Documentation Index

本文件是当前开发文档入口。`docs/` 顶层只保留日常推进需要频繁查看的文档；历史计划、阶段审计和一次性验证记录已归档到 `docs/_archive/`。

## Current Working Documents

- `SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md`
  PR #4 合并后选择链审计形成的最高优先级计划：撤回 test-influenced allowlist/model readiness，实施逻辑 PR #4.1 的 provenance、nested selection、split-scoped FDR、date-bounded clustering 和 anti-leakage 门禁，并定义 PR #5A—#5D 的完整顺序。
- `FULL_RESEARCH_669_RUN_V1.md`
  PR #4 的 669 因子冻结目录、30 分区矩阵、FDR/稳定性/聚类历史结果、Qlib 执行、readiness 与复现说明；其中模型 readiness 和 16 因子 allowlist 结论已由合并后审计撤回。
- `FULL_RESEARCH_FACTOR_TRIAL_V1.md`
  PR #3 的 80 因子真实 PIT 特征矩阵、purged/FDR/稳定性/聚类/score、Qlib 执行、readiness 与复现说明。
- `QLIB_EXCHANGE_INTEGRATION_V1.md`
  PR #2 已实施范围、单位/约束语义、合成精确对账、30 股票真实小样本、readiness 和复现命令。
- `QLIB_EXCHANGE_SEMANTIC_AUDIT_V1.md`
  固定 Qlib commit 的 Exchange、Executor、Signal、成本、成交量、T+1 和输出语义源码审计。
- `REFERENCE_PIPELINE_CONSISTENCY_V1_1_1.md`
  V1.1.1 已实施计划与验收结果；已修复全 holdout 与旧下游混用、stale artifact、未生效 lineage gate 和 readiness 假阳性。
- `FACTOR_VALIDATION_HARDENING_V1_1.md`
  V1.1 已实施计划与历史证据；其 `reference_ready=true` 结论已被 V1.1.1 一致性审计更正。
- `Qlib A股因子研究框架完整升级计划 V1.md`
  新一轮研究框架升级总纲，定义阶段目标、约束、输出和最终完成标准。
- `FACTOR_VALIDATION_ROADMAP_V1.md`
  上述升级总纲的详细执行路线图，包含工作包编号、依赖、预计文件、验证顺序、阶段门禁和失败停止条件。
- `outputs/research_data_contracts_v1/current/schema_report.md`
  阶段 1 DataFrame contract 对现有 factor、tradability、screening 与 judgement 输出的兼容审计。
- `outputs/point_in_time_universe_v1/local_smoke/universe_report.md`
  阶段 2 动态股票池真实 provider smoke、PIT 审计与 Qlib instruments 回读结果。
- `outputs/purged_walk_forward_v1/local_reference/purged_walk_forward_report.md`
  阶段 3 date-level Purged Walk-Forward manifest、泄漏审计与 mlfinpy 非依赖语义参考边界。
- `outputs/factor_multiple_testing_v1/local_reference/multiple_testing_report.md`
  阶段 4 block bootstrap、BH/BY FDR、null simulation 与 test-family 审计。
- `outputs/factor_rolling_stability_v1/local_reference/stability_report.md`
  阶段 5 严格窗口选择历史、冻结方向、OOS degradation 与稳定性角色看板。
- `outputs/factor_clustering_v1/local_reference/clustering_report.md`
  阶段 6 当前 blocked reference 输出；无 eligible factor，活动 representatives 为空。
- `outputs/factor_score_construction_v1/local_reference/score_construction_report.md`
  阶段 7 当前 blocked reference 输出；活动 weights 为空且 score parquet 不存在。
- `outputs/a_share_execution_v1/local_reference/execution_report.md`
  阶段 8 执行会计基础设施；当前因无有效 score 被预期阻断，没有沿用旧执行结果。
- `outputs/external_exposure_data_v1/current/exposure_data_report.md`
  阶段 9 AKShare forward-only 快照、PIT 字段契约和当前外部采集阻塞状态。
- `outputs/pre_model_diagnostics_v1/local_reference/final_portfolio_report.md`
  阶段 10 当前 blocked pre-model diagnostics；legacy baseline 仅独立展示，current methods 不再由旧 score 补齐。
- `outputs/legacy_common_scores_v1/local_reference/legacy_common_scores_report.md`
  Alpha158 与旧 V3.5 candidate pool 在相同 purged test windows 下的共同口径等权 score。
- `outputs/factor_model_comparison_v1/gated/model_comparison_report.md`
  阶段 11 V1.1.1 能力门禁；真实 lineage/freshness/semantic gate 已启用，pipeline/reference ready 均为 false，训练未启动。
- `PROJECT_CONTEXT_SUMMARY.md`
  项目当前状态、最新阶段、关键路径和下一步入口。
- `STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md`
  因子研究与筛选主线总线文档。
- `FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md`
  当前因子研究工具链 readiness、能力边界和下一步约束。
- `LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1_PLAN.md`
  V3.39 liquidity residualized factor evaluation 最小实现计划。

## Baseline And Environment

- `ENVIRONMENT.md`
  本地 Python、Qlib、数据路径和运行环境快照。
- `BASELINE_REPRODUCIBILITY.md`
  Qlib baseline 复现说明，包括 Windows tempfile 和 multiprocessing wrapper。
- `DATA_SOURCE_DECISION.md`
  数据源选择、字段口径和数据使用原则。
- `UNIVERSE_POLICY.md`
  股票池与 universe 口径。
- `TRADABILITY_LABEL_LAYER.md`
  可交易性标签层设计；后续因子评估必须复用该层，不绕过 data_quality/tradability。

## Archive

历史文档入口：

```text
docs/_archive/README.md
```

归档文档不是废弃文档，而是阶段性证据和参考材料。需要追溯某个已完成阶段时，优先从归档 README 的主题目录进入。

## Current Stage

PR #4 的工程规模化部分已经完成：669 因子目录、30 个可恢复矩阵分区、daily IC、purged outer split 和统一 Qlib execution 均保留为有效证据。合并后审计确认 selection/stability 使用 outer test 信息、clustering 未限制 development dates、Stability 未真实消费上游 FDR，且 raw/provider/source provenance 不完整。当前 16 个代表只作为 `exploratory/test-influenced` 历史证据，不得用于模型。

```text
docs/SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md
docs/Qlib A股因子研究框架完整升级计划 V1.md
docs/FACTOR_VALIDATION_ROADMAP_V1.md
docs/FACTOR_VALIDATION_HARDENING_V1_1.md
docs/REFERENCE_PIPELINE_CONSISTENCY_V1_1_1.md
```

当前状态为 `full_research_669_infrastructure_ready=true`、`full_research_669_matrix_content_ready=true`、`full_research_669_qlib_execution_operational=true`、`feature_selection_holdout_clean=false`、`clustering_holdout_clean=false`、`fdr_artifact_consumed=false`、`raw_input_provenance_complete=false`、`feature_allowlist_frozen=false`、`core_model_ready=false`、`pr5_model_training_ready=false`、`full_research_authoritative_tradability_ready=false`、`model_training_started=false`。下一阶段是逻辑 PR #4.1；完成前不得实施 PR #5。
