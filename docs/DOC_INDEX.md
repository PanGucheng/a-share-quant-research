# Documentation Index

本文件是当前开发文档入口。`docs/` 顶层只保留日常推进需要频繁查看的文档；历史计划、阶段审计和一次性验证记录已归档到 `docs/_archive/`。

## Current Working Documents

- `ACCURACY_CORRECTION_V1_PLAN.md`
  已冻结的正式实施基线与当前唯一执行计划。2026-07-23 实现复核确认 PIT lifecycle、横截面因子污染、pairwise IC、字段时点、税费和陈旧估值问题；先以 GitHub PR #6 修复研究计算且不生成 OOS NAV，再以 PR #7 修复执行语义，PR #5A 继续暂停。
- `outputs/accuracy_correction_v1/current/`
  PR #6 第一个业务提交建立的当前机器治理状态：holdout integrity 保留为 true，研究/执行/model readiness 全部 false；旧 allowlist、weights、scores 已 superseded，历史 execution/NAV 为 non-authoritative。
- `outputs/point_in_time_universe_v2/full_research/`
  PR #6 lifecycle-clean Universe v2：29 个越界 interval 与 329 个非法 key 已修正，最终 lifecycle violation、interval overlap 和 removed-key residual 均为 0。
- `PR5A_MODEL_INPUT_PROTOCOL_HANDOFF_V1.md`
  延后的模型输入协议参考。只能在 PR #6/#7 全部门禁通过后重新启用，不能直接采用当前已被替代的 allowlist、score 或 OOS execution。
- `SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md`
- `SELECTION_HOLDOUT_IMPLEMENTATION_AUDIT_V1.md`
  PR #4 合并后的 holdout 修复计划与实现审计。其 holdout 隔离结论继续有效，但“直接进入 PR #5A”的结论已由 Accuracy Correction 计划接管。
- `FULL_RESEARCH_669_RUN_V1.md`
  PR #4 的 669 因子工程证据与 PR #4.1 的完成增补；旧 16 因子和当前 48/46/54 split allowlist 均只保留历史证据，后者等待 PR #6 重建。
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

逻辑 PR #4.1 已修复选择链的 outer-test 泄漏，`selection_holdout_integrity_ready=true` 继续有效。2026-07-23 的实现级准确性复核又确认：PIT membership 有 29 个越界 interval / 329 个非法 key，横截面或混合因子可能污染其他合法股票；Daily IC 不是严格 pairwise Spearman；开盘执行读取收盘后才能确定的同日 `$change`；历史印花税、陈旧估值和 market cache 语义也不正确或不完整。

```text
docs/ACCURACY_CORRECTION_V1_PLAN.md
docs/Qlib A股因子研究框架完整升级计划 V1.md
docs/FACTOR_VALIDATION_ROADMAP_V1.md
```

当前 48/46/54 allowlist、透明 score 和 OOS NAV 已分别标记为 `superseded` / `non_authoritative`。目标机器状态为 `model_research_ready=false`、`authoritative_oos_execution_ready=false`、`core_model_ready=false`、`pr5_model_training_ready=false`、`model_training_started=false`。

下一步固定为 GitHub PR #6 `Research Accuracy Correction V1`，随后为 PR #7 `Execution Accuracy Correction V1`。任何大规模运行仍须先完成因子依赖分类、完整自审、受限 canary、mutation/metamorphic tests、资源审阅和 exact review bundle；本次持续对话的 `user_session_waiver` 只免除等待，不免除技术门禁。PR #6/#7 全部完成前不得实施模型 PR #5A。
