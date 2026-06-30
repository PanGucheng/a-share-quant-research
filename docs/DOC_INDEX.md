# Documentation Index

本文件是当前开发文档入口。`docs/` 顶层只保留日常推进需要频繁查看的文档；历史计划、阶段审计和一次性验证记录已归档到 `docs/_archive/`。

## Current Working Documents

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

当前阶段是 V3.39：

```text
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1_PLAN.md
```

目标是在不训练新模型、不调整策略、不引入实盘模块的前提下，对 V3.38 识别出的 19 个高流动性/可交易性暴露 probes 做残差化复核，判断信号是否仍具有独立 alpha，还是主要来自 liquidity/tradability proxy。
