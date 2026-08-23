# Documentation Archive

本目录保存已完成阶段的计划、审计、调研和一次性验证记录。它们不是废弃材料，而是
项目演进的证据库，但不再是当前执行入口。日常开发请先看
[`docs/DOC_INDEX.md`](../DOC_INDEX.md) 和
[`docs/PROJECT_CONTEXT_SUMMARY.md`](../PROJECT_CONTEXT_SUMMARY.md)。

## Directory Map

- `01_early_stage_plans/`
  早期总计划与 Step 1-4：baseline 复现、数据层升级、derived provider、组合约束等。
- `02_data_layer_history/`
  数据快照、字段验证、数据升级对比和 provider 能力历史检查。
- `03_factor_research_history/`
  早期因子研究规划、开源评价体系调研、V3.1-V3.5 计划、算法审计和 V4 smoke 设计。
- `04_alpha158_history/`
  Alpha158 catalog、expression adapter、full evaluation、candidate pool、组合 smoke 和稳定性诊断。
- `05_open_source_factor_batches/`
  TA、Alpha101、Alpha360、多源筛选、multi-source judgement 和开源因子扩张审计。
- `06_probe_and_tradeability_audits/`
  new-source probe diagnostics/review、strict OOS、tradability exposure attribution 和 exposure data capability audit。
- `07_research_program_history/`
  已完成或被接管的 full-research、accuracy correction、selection/model protocol、
  historical comparison/backtest、Forward MVP 与 Qlib execution 计划和回执。
- `08_engineering_refactor/`
  Phase 0–6 工程重构的原始开放式指南与实施计划。当前权威收尾见
  [`ENGINEERING_REFACTOR_CLOSEOUT.md`](../ENGINEERING_REFACTOR_CLOSEOUT.md)。
- `09_model_research_and_productivity_history/`
  已完成的 ML feature-pool、性能、research productivity 与 clustering 研究线中的
  历史实施计划。详细结果以 `reports/` 下相应 final report 为准。

## Archive Rule

新文档默认不进入归档。只有当一个阶段完成、被更高层总线文档吸收，且不再是当前执行
入口时，才移动到本目录。归档文档中的命令、路径和“下一步”只代表当时状态；若与
`docs/` 顶层当前文档冲突，以当前文档为准。

归档时保留 Git 历史，并同步更新 `docs/DOC_INDEX.md`、根 README、AGENTS、配置中的
文档路径及 Markdown 链接。不得因为归档而删除对应 outputs、artifacts、receipts、
manifests 或 lineage。
