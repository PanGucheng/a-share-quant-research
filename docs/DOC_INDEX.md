# Documentation Index

本文件是仓库文档导航入口。`docs/` 顶层只保留 current authority/governance；
`docs/operations/` 保存活动工作流的 operational contracts；`docs/_archive/` 与
`reports/` 保存 historical evidence。Archive 中的命令和“下一步”不构成当前授权。

## Recommended Reading

新 Codex 会话默认只需要：

```text
AGENTS.md
    ↓
PROJECT_CONTEXT_SUMMARY.md
    ↓
CURRENT_PIPELINE.md
    ↓
task-specific authority doc
```

详细历史按需追溯，不需要默认阅读所有 reports。

## Current Authority

- [PROJECT_CONTEXT_SUMMARY.md](PROJECT_CONTEXT_SUMMARY.md) — 1–3 分钟新会话上下文。
- [CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) — ACTIVE、FROZEN、CLOSED、NEXT / NOT
  STARTED、NOT AUTHORIZED 状态和活动命令。
- [CANONICAL_RESEARCH_DATASET.md](CANONICAL_RESEARCH_DATASET.md) — 当前长历史因子研究主线及
  后续 protocol work 的唯一推荐数据 identity、effective-date 读取合同和 qualification。
- [LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md](LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md)
  — 当前历史研究主线、Phase 0–6 范围、复用边界与完成标准。
- [LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md](LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md)
  — 第一开发单元：旧结论冻结与不调参 backward replication 的具体实现计划。
- [Phase 0 closeout report](../reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md)
  — 91 因子 fixed-union、same-era reconciliation、backward portability 与限制。
- [PERSONAL_QUANT_RESEARCH_ROADMAP.md](PERSONAL_QUANT_RESEARCH_ROADMAP.md) — Forward
  时间优先级与 Strategy V1/V2 长期边界。
- [ARCHITECTURE.md](ARCHITECTURE.md) — 当前领域职责、依赖方向和 frozen compatibility。
- [OUTPUT_POLICY.md](OUTPUT_POLICY.md) — `outputs/`、`artifacts/`、`reports/`、`tmp/`
  与 official Forward evidence 政策。
- [CI_POLICY.md](CI_POLICY.md) — 本地/CI `fast`、`full`、`qlib` 质量层。
- [ENVIRONMENT.md](ENVIRONMENT.md) — portable settings、local override、Python/Qlib
  与 doctor。

发生冲突时，先遵守根目录 `AGENTS.md` 的长期规则，再以 current authority 和实时 machine
evidence 判断；历史报告与 archive 只说明当时发生了什么。

## Operational References

- [operations/PERFORMANCE_EXECUTION_PROFILES_V1.md](operations/PERFORMANCE_EXECUTION_PROFILES_V1.md)
  — real LightGBM thread determinism audit, non-authoritative Fast MT fallback, and
  CPU/RAM-safe worker-thread benchmark planning.
- [operations/DAILY_DATA_UPDATE_V1.md](operations/DAILY_DATA_UPDATE_V1.md) — Daily
  Update 数据源、fallback、覆盖和输出合同。
- [operations/STRATEGY_V1_PAPER_PORTFOLIO_V1.md](operations/STRATEGY_V1_PAPER_PORTFOLIO_V1.md)
  — 冻结 Strategy V1 paper decision、execution refresh、持仓和 NAV。
- [operations/UNIVERSE_POLICY.md](operations/UNIVERSE_POLICY.md) — A 股 universe 与动态
  lifecycle membership。
- [operations/TRADABILITY_LABEL_LAYER.md](operations/TRADABILITY_LABEL_LAYER.md) —
  tradability label 与 fail-closed 边界。

## Repository Entry Documents

- [../README.md](../README.md) — 英文 landing page。
- [../README.zh-CN.md](../README.zh-CN.md) — 中文 landing page。
- [../reports/README.md](../reports/README.md) — compact report policy 与报告入口。
- [../data_quality/README.md](../data_quality/README.md) — 数据质量模块。
- [../tradability/README.md](../tradability/README.md) — 可交易性模块。

## Machine Evidence

文档不复制实时状态。Forward Track 以以下文件为准：

- `outputs/forward/status.json`；
- `outputs/forward/paper_portfolio/status.json`；
- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`。

Canonical dataset 的 authority 与 tracked evidence 入口：

- [CANONICAL_RESEARCH_DATASET.md](CANONICAL_RESEARCH_DATASET.md)；
- [canonical assembly report](../reports/canonical_historical_dataset_assembly_v1/REPORT.md)。

本地完整数据 assembly 还会生成 runtime-only 的 `manifest.json`、
`partition_manifest.csv` 和 `factor_lineage.csv`；它们体积较大的 parent partitions 与 runtime
输出不进入 Git checkout，不能作为仓库文档索引的存在性前提。

目录名含 `current` 不表示相应研究阶段仍 ACTIVE；必须结合
[CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) 判断。

## Historical Evidence

### Reports

完整研究结论、限制和小型审计证据位于 [../reports/](../reports/README.md)。当前关键
authority 的形成过程可从以下报告按需追溯：

- [Canonical Historical Dataset Assembly](../reports/canonical_historical_dataset_assembly_v1/REPORT.md)；
- [Extended Matrix Overlap Lineage Resolution](../reports/extended_matrix_overlap_lineage_resolution_v1/REPORT.md)；
- [Historical Data Engineering Extension](../reports/historical_data_engineering_extension_v1/REPORT.md)；
- [Historical Dataset & Validation Design Study](../reports/historical_dataset_validation_design_v1/REPORT.md)；
- [Research Protocol V2](../reports/research_protocol_v2/REPORT.md)；
- [Factor Universe V2](../reports/factor_universe_v2/REPORT.md) 与
  [Matrix Readiness](../reports/factor_universe_v2_matrix_readiness/REPORT.md)。
- [Performance Execution V1](../reports/performance_execution_v1/REPORT.md) —
  controlled thread determinism evidence and qualified Fast/Full 8T profiles.

这些链接用于 provenance，不把已观察结果提升为 fresh OOS 或新策略授权。

### Archive Map

[docs/_archive/ README](_archive/README.md) 解释完整分类：

- `_archive/01_early_stage_plans/` — 早期总计划与基础阶段；
- `_archive/02_data_layer_history/` — 数据层、snapshot 与 provider 历史；
- `_archive/03_factor_research_history/` — 早期因子研究计划与审计；
- `_archive/04_alpha158_history/` — Alpha158 catalog/evaluation 历史；
- `_archive/05_open_source_factor_batches/` — TA/Alpha101/Alpha360 批次；
- `_archive/06_probe_and_tradeability_audits/` — probe、strict OOS 与 exposure audits；
- `_archive/07_research_program_history/` — 已完成 research/model/data/Forward plans，
  包括 [frozen prior Research Protocol V2](_archive/07_research_program_history/RESEARCH_PROTOCOL_V2.md)；
- `_archive/08_engineering_refactor/` — CLOSED Phase 0–6 工程重构；
- `_archive/09_model_research_and_productivity_history/` — ML feature pool、性能、
  productivity 与 clustering 计划。

历史 task 完成且结论被 current authority 吸收后，其 plan 作为 provenance 归档，不再作为
current instruction。历史 outputs、artifacts、manifests、receipts 和 lineage 不因文档归档
而删除、移动或改写。

## Current Boundary Summary

- Forward Track：ACTIVE / time-priority；
- Strategy V1：FROZEN；
- Historical Data Engineering：CLOSED；
- Canonical Research Dataset：READY；
- Long-History Robust Core Factor Selection V1：ACTIVE RESEARCH MAINLINE / PHASE 0 CLOSED；
- Phase 0 Backward Replication：CLOSED / COMPLETED；
- Phase 1 Feature Quality Gate：NOT STARTED；
- Structured ML：NOT AUTHORIZED；
- Strategy V2：NOT AUTHORIZED。

Canonical identity：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```
