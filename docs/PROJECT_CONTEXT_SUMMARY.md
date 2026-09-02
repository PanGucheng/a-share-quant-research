# Project Context Summary

本文件用于让新会话在 1–3 分钟内恢复当前上下文。阶段历史和详细数字不在此重复，
按需从 [DOC_INDEX.md](DOC_INDEX.md)、`reports/` 或 `docs/_archive/` 追溯。

## Project Positioning

- 项目：`A-Share Quant Research` / `A 股量化研究框架`。
- Repository：
  [PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)。
- personal、research-first 的中国 A 股量化研究项目；Microsoft Qlib 是主要底层框架。
- 用于因子、模型、组合与 genuine forward research；不是生产交易、机构或合规系统。
- 首要原则：研究逻辑正确、无未来数据、时间隔离、保护 holdout/forward evidence。

## New-Session Reading Path

1. 根目录 `AGENTS.md` — 长期工作规则和禁止事项；
2. 本文件 — 紧凑当前上下文；
3. [CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) — ACTIVE/FROZEN/CLOSED/NEXT 与命令；
4. 与当前任务直接相关的 authority doc。

常用 authority：

- 数据输入：[CANONICAL_RESEARCH_DATASET.md](CANONICAL_RESEARCH_DATASET.md)；
- 当前历史研究主线：
  [LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md](LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md)；
- 第一开发单元：
  [LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md](LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md)；
- 研究路线：[PERSONAL_QUANT_RESEARCH_ROADMAP.md](PERSONAL_QUANT_RESEARCH_ROADMAP.md)；
- 架构：[ARCHITECTURE.md](ARCHITECTURE.md)；
- 输出边界：[OUTPUT_POLICY.md](OUTPUT_POLICY.md)；
- 环境：[ENVIRONMENT.md](ENVIRONMENT.md)；
- 质量检查：[CI_POLICY.md](CI_POLICY.md)。

`docs/operations/` 是活动 operational contracts；`docs/_archive/`、historical reports 和
历史 outputs 是按需读取的 evidence，不是当前执行指令。

## Current State

| 对象 | 状态 | 当前含义 |
|---|---|---|
| Forward Track | ACTIVE / time-priority | Daily Update、冻结 Strategy V1 prediction、paper portfolio、成熟标签评价 |
| Strategy V1 | FROZEN | LightGBM、固定 52 因子顺序、P01 Top50 等权、每 5 个交易日调仓 |
| Historical Data Engineering | CLOSED | 不再默认继续 extension/frontier/authority 工作 |
| Canonical Research Dataset | READY / authority | 当前长历史因子研究主线及后续 protocol work 的唯一推荐数据输入 |
| Long-History Robust Core Factor Selection V1 | ACTIVE RESEARCH MAINLINE / PLANNING | 以 765 个 research-usable factors 提炼 Small Stable Alpha Core，并分离 Risk / Conditioning Controls；当前只完成路线与 Phase 0 计划 |
| Phase 0 Backward Replication | READY FOR IMPLEMENTATION / NOT STARTED | 冻结旧 52、mature 39、旧 roles/directions/clusters，并在 canonical early history 不调参复核 |
| Structured ML | NOT AUTHORIZED | 不得从 prior protocol 直接启动 |
| Strategy V2 | NOT AUTHORIZED | 需要独立 protocol、freeze date 与新 forward evidence |

Forward Track 的机器状态以以下文件为准，不以文档中的日期摘要为准：

- `outputs/forward/status.json`；
- `outputs/forward/paper_portfolio/status.json`；
- `outputs/prospective_forward_hardening_v1/current/forward_candidate_freeze.json`。

## Canonical Dataset Authority

后续新的 Dataset / Research Protocol work 必须绑定：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

- 范围：`2010-01-29` 至 `2026-06-09`；
- definitions：774；research-usable：765；blocked：9；
- Historical Data Engineering：`CLOSED`；
- old frozen Matrix、partial extension、lineage-resolved intermediate Matrix：immutable
  historical evidence，不是新研究默认输入。

机器入口和 effective-date 读取合同见
[CANONICAL_RESEARCH_DATASET.md](CANONICAL_RESEARCH_DATASET.md)。

## Research Boundary

Research Protocol V2 是模型 outcomes 前冻结的 prior protocol evidence，但后续 validation
study 已证明其中 35–43 日的短 development environments 不足以充当正式 Structured ML
selection authority。它不能被解释为“可以直接运行 Structured ML”。当前历史研究主线已明确为
以 canonical dataset 为输入的 Long-History Robust Core Factor Selection V1。该路线先做旧结论
backward replication，再做 quality、long-history evidence、candidate board、redundancy map、
core team selection 与 stopping rule；它不是 Structured ML 或 Strategy V2 授权。

Forward Track 继续具有时间优先级，因为 genuine forward prediction/decision 不能事后回填。
Strategy V1 的 prediction、decision、position、trade 和 NAV 保持 append-only；任何历史诊断
都不能静默修改 Strategy V1，也不能授权 Strategy V2。

## Environment And Commands

当前 Windows 工作站：

```text
repository: E:\qlib_prj\qlib_baseline
Python:     E:\anaconda_envs\qlib_env\python.exe
Qlib:       E:\qlib_prj\qlib_clone
```

机器路径只进入 ignored `configs/project.local.yaml`。检查环境：

```powershell
qlib-doctor --strict
```

活动入口：

```powershell
qlib-daily-update --target-date YYYY-MM-DD
qlib-forward-predict --help
qlib-forward-label-update --help
qlib-paper-portfolio --help
qlib-forward-status
```

cutoff、Git binding、label maturity 和 paper refresh 参数以
[CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) 为准。

质量入口：

```powershell
python scripts/check_quality.py fast
python scripts/check_quality.py full
python scripts/check_quality.py qlib
```

## Critical Rules

- 任何决策只能使用当时可得信息；train/validation/test/forward label evaluation 必须隔离。
- `split_003` 已观察，只能诊断，不得重新调优后声称 fresh OOS。
- correctness failure 必须 fail loudly；不覆盖 frozen、historical 或 Forward evidence。
- 开始任务前确认对象是 ACTIVE、FROZEN、CLOSED、historical 还是 experimental。
- 复用现有实现，优先最小修改；不为普通研究新增 manager/registry/gate/protocol。
- 详细历史结论只在 reports/archive 维护，不回填或改写历史 evidence。
