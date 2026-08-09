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
2. [ARCHITECTURE.md](ARCHITECTURE.md) — 当前模块和依赖边界；
3. [OUTPUT_POLICY.md](OUTPUT_POLICY.md) — 输出、artifact、report、cache 和 Forward evidence；
4. [CI_POLICY.md](CI_POLICY.md) — 本地/CI quality tiers；
5. [ENGINEERING_REFACTOR_CLOSEOUT.md](ENGINEERING_REFACTOR_CLOSEOUT.md) — Phase 0–6 最终绿色工程基线。

`docs/_archive/` 中的计划和回执是 CLOSED/HISTORICAL/SUPERSEDED 证据，不是当前授权。

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

截至 2026-08-09：

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
  `b46b4f614f3be5388bf7a26ebf2b035d14906f5f`；不存在隐式 Phase 7。
- Matrix v4、raw snapshot manifest、lineage 和全部历史研究结果保持冻结。

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
