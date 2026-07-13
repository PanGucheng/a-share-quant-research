# Documentation Index

本文件是当前开发文档入口。`docs/` 顶层只保留日常推进需要频繁查看的文档；历史计划、阶段审计和一次性验证记录已归档到 `docs/_archive/`。

## Current Working Documents

- `REFERENCE_PIPELINE_CONSISTENCY_V1_1_1.md`
  当前最高优先级执行计划；修复新版稳定性全 holdout 与旧 clustering/score/execution/diagnostics 混用、stale artifact、未生效 lineage gate 和 readiness 假阳性。
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
  阶段 6 历史 reference 输出；当前仍含 3 个旧 representatives，已被 V1.1.1 判定为 stale，不得继续作为活动链证据。
- `outputs/factor_score_construction_v1/local_reference/score_construction_report.md`
  阶段 7 历史 reference 输出；当前权重和 runtime 与全 holdout stability 不一致，待 V1.1.1 受控替换。
- `outputs/a_share_execution_v1/local_reference/execution_report.md`
  阶段 8 执行会计能力证据；当前业务结果消费 stale score，只能证明基础设施，不证明 reference pipeline 可用。
- `outputs/external_exposure_data_v1/current/exposure_data_report.md`
  阶段 9 AKShare forward-only 快照、PIT 字段契约和当前外部采集阻塞状态。
- `outputs/pre_model_diagnostics_v1/local_reference/final_portfolio_report.md`
  阶段 10 pre-model 历史诊断；common-period 算法仍需 NAV 归一化，且 current stability methods 来自 stale score，当前不得用于 readiness。
- `outputs/legacy_common_scores_v1/local_reference/legacy_common_scores_report.md`
  Alpha158 与旧 V3.5 candidate pool 在相同 purged test windows 下的共同口径等权 score。
- `outputs/factor_model_comparison_v1/gated/model_comparison_report.md`
  阶段 11 V1.1 能力门禁；其旧 `reference_ready=true` 未执行真实 lineage/freshness/semantic gate，已由 V1.1.1 更正为 false，训练仍禁止启动。
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

V1.1 基础设施硬化已实施，但 V1.1.1 审计确认真实 reference 数据链不一致：新版稳定性为 10 个 holdout、0 eligible windows，活动下游仍保留旧 3 个代表因子及 score/runtime。当前先修复 freshness、阻断传播和 readiness 语义；未训练模型、未运行 669 因子全量结果、未接入 Qlib Exchange。

```text
docs/Qlib A股因子研究框架完整升级计划 V1.md
docs/FACTOR_VALIDATION_ROADMAP_V1.md
docs/FACTOR_VALIDATION_HARDENING_V1_1.md
docs/REFERENCE_PIPELINE_CONSISTENCY_V1_1_1.md
```

当前诚实状态应解释为 `reference_infrastructure_ready=true`、`reference_pipeline_ready=false`、兼容字段 `reference_ready=false`；full/core/扩展能力和 `model_training_started` 均为 false。V3.39 低 coverage 与 AKShare 历史暴露仍只阻塞各自能力。完成 V1.1.1 后，下一 PR 才进入 Qlib Exchange integration。
