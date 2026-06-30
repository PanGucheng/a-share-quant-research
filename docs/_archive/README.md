# Documentation Archive

本目录保存已完成阶段的计划、审计、调研和一次性验证记录。它们不是废弃材料，而是项目演进的证据库。日常开发请先看 `docs/DOC_INDEX.md` 和 `docs/PROJECT_CONTEXT_SUMMARY.md`。

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

## Archive Rule

新文档默认不进入归档。只有当一个阶段完成、被更高层总线文档吸收，且不再是当前执行入口时，才移动到本目录。

归档时使用 `git mv` 保留历史，并在需要时更新 `docs/DOC_INDEX.md`、`README.md` 和 `README.zh-CN.md`。
