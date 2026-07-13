# Documentation Index

本文件是当前开发文档入口。`docs/` 顶层只保留日常推进需要频繁查看的文档；历史计划、阶段审计和一次性验证记录已归档到 `docs/_archive/`。

## Current Working Documents

- `FACTOR_VALIDATION_HARDENING_V1_1.md`
  当前最高优先级执行计划；修复 PR #1 的诊断门禁循环、Profile 语义、稳定性 eligibility、common-period 比较、reference execution 会计和端到端 artifact lineage。
- `Qlib A股因子研究框架完整升级计划 V1.md`
  新一轮研究框架升级总纲，定义阶段目标、约束、输出和最终完成标准。
- `FACTOR_VALIDATION_ROADMAP_V1.md`
  上述升级总纲的详细执行路线图，包含工作包编号、依赖、预计文件、验证顺序、阶段门禁和失败停止条件。
- `outputs/research_data_contracts_v1/current/schema_report.md`
  阶段 1 DataFrame contract 对现有 factor、tradability、screening 与 judgement 输出的兼容审计。
- `outputs/point_in_time_universe_v1/local_smoke/universe_report.md`
  阶段 2 动态股票池真实 provider smoke、PIT 审计与 Qlib instruments 回读结果。
- `outputs/purged_walk_forward_v1/full_research/purged_walk_forward_report.md`
  阶段 3 date-level Purged Walk-Forward manifest、泄漏审计与 mlfinpy 非依赖语义参考边界。
- `outputs/factor_multiple_testing_v1/local_reference/multiple_testing_report.md`
  阶段 4 block bootstrap、BH/BY FDR、null simulation 与 test-family 审计。
- `outputs/factor_rolling_stability_v1/local_reference/stability_report.md`
  阶段 5 严格窗口选择历史、冻结方向、OOS degradation 与稳定性角色看板。
- `outputs/factor_clustering_v1/local_reference/clustering_report.md`
  阶段 6 exposure/performance 双相似度、SciPy 聚类与代表因子选择。
- `outputs/factor_score_construction_v1/local_reference/score_construction_report.md`
  阶段 7 三种透明组合、窗口权重、组件覆盖与防未来权重 contract。
- `outputs/a_share_execution_v1/local_reference/execution_report.md`
  阶段 8 A股订单约束、费用、部分成交、会计守恒和容量诊断。
- `outputs/external_exposure_data_v1/current/exposure_data_report.md`
  阶段 9 AKShare forward-only 快照、PIT 字段契约和当前外部采集阻塞状态。
- `outputs/final_portfolio_diagnostics_v1/local_reference/final_portfolio_report.md`
  阶段 10 现有 reference 诊断；V1.1 将其拆为 pre/post-model diagnostics，并要求 native/common-period 双输出。
- `outputs/legacy_common_scores_v1/local_reference/legacy_common_scores_report.md`
  Alpha158 与旧 V3.5 candidate pool 在相同 purged test windows 下的共同口径等权 score。
- `outputs/factor_model_comparison_v1/gated/model_comparison_report.md`
  阶段 11 现有前置门禁；V1.1 将改为 reference/full/core/可选能力分层，当前仍禁止启动训练。
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

阶段 0—4 已形成基础实现，阶段 5—10 已有局部 reference implementation，但尚不能视为 full-research 结果。当前进入 V1.1 收尾硬化：先修复门禁循环、Profile、lineage、稳定性 coverage、共同日期比较和 reference execution 会计；本轮不训练模型、不运行 669 因子全量结果、不接入 Qlib Exchange。

```text
docs/Qlib A股因子研究框架完整升级计划 V1.md
docs/FACTOR_VALIDATION_ROADMAP_V1.md
docs/FACTOR_VALIDATION_HARDENING_V1_1.md
```

V1.1 预期只让 `reference_ready=true`；`full_research_ready`、`core_model_ready`、`liquidity_residualized_model_ready`、`historical_exposure_model_ready` 和 `model_training_started` 均保持 false。V3.39 的 `residualized_coverage_min=0.1495 < 0.80` 只阻塞流动性残差化模型能力；AKShare 历史暴露缺口只阻塞历史暴露模型能力。
