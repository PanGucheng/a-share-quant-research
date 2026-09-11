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

Economic Translation MVP：**E1 IMPLEMENTED / AWAITING USER RUN；E2 BLOCKED BY EXECUTION / DATA GAP**。
计划修订已先独立提交 `6464937`，E1封闭B494结构reader/独立重放、E2专用Qlib执行原语/合成验证与短真实行情canary已交付。
见 [阶段报告](../reports/economic_translation_mvp/REPORT.md)、[执行合同与缺口](../reports/economic_translation_mvp/EXECUTION_CONTRACT.md)、
[用户运行说明](ECONOMIC_TRANSLATION_E1_E2_RUNBOOK.md)。仅用户运行E1长扫描；E2数据/公司行为/状态缺口不因测试通过消失。
B494是治理incumbent，10/20仅单一结构候选；E3冻结、E4/NAV、2024+、V2仍禁止。

2026-09-10：D1全量168个月、3382日结构扫描及独立oracle通过后，用户授权评估并实施正式冻结与D2。
R218/C201/H358以 `d05e7eb` [正式冻结](../reports/literature_factor_representation_d1/FORMAL_FREEZE.md)，
保留U质量限制、dense可变节点含义及跨family完整性代价。
2026-09-11：[D2完成核验](../reports/literature_factor_representation_d2/COMPLETION_REPORT.md)，
27模型、13,133,472行新prediction及独立replay全部通过，R/C/H均all_nine_exact；五臂封存，无需重跑。
用户随后授权[计划并实施 D3-A 五臂冻结预测评价](LITERATURE_D3A_FROZEN_PREDICTION_EVALUATION_PLAN.md)。
目前 **D3-A COMPLETE / VERIFIED / STOP FOR HUMAN REVIEW**，
[完成审阅](../reports/literature_factor_representation_d3a/COMPLETION_REVIEW.md)。
2,168个共同可评分日、4,144,939对；六项Holm检验均未拒绝零差异，不等于无损/非劣。
已揭封事实永久记录于 OUTCOME_OPENED.json，无需重跑；
D3-B、组合、调参、Strategy V2 和 2024+ 继续关闭。

| 对象 | 状态 | 当前含义 |
|---|---|---|
| Forward Track | ACTIVE / time-priority | Daily Update、冻结 Strategy V1 prediction、paper portfolio、成熟标签评价 |
| Strategy V1 | FROZEN | LightGBM、固定 52 因子顺序、P01 Top50 等权、每 5 个交易日调仓 |
| Historical Data Engineering | CLOSED | 不再默认继续 extension/frontier/authority 工作 |
| Canonical Research Dataset | READY / authority | 当前长历史因子研究主线及后续 protocol work 的唯一推荐数据输入 |
| Long-History Robust Core Factor Selection V1 | ACTIVE RESEARCH MAINLINE / PHASE 0 CLOSED | 以 765 个 research-usable factors 提炼 Small Stable Alpha Core，并分离 Risk / Conditioning Controls；Phase 0 已完成 |
| Phase 0 Backward Replication | CLOSED / COMPLETED | 91 因子 fixed-union、same-era reconciliation 与四时期 backward replication 已完成 |
| Phase 1 Feature Quality Gate | COMPLETE / MVP quality scope | 本轮质量审计完成；不等于可交易性认证 |
| Primary 20D Screening MVP | COMPLETE / STOP FOR HUMAN REVIEW | 765行Evidence/Candidate Board、三体系规则与FDR已交付 |
| Research Protocol V3-MVP | RECOMPUTED / ENGINEERING VERIFIED / STOP FOR REVIEW | [实施进度](../reports/research_protocol_v3_mvp/IMPLEMENTATION_PROGRESS.md)：P0/P1及两折8/494列重算与预测复核完成；旧宽表声明撤回，P3未解锁 |
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

当前收缩实施依据：[多体系筛选 MVP](LONG_HISTORY_MULTI_EVALUATOR_SCREENING_MVP_PLAN.md)；2026-09-08已交付[V0审阅报告](../reports/long_history_multi_evaluator_screening_v1/REPORT.md)，现在STOP人工审阅。2024+近期诊断、Core/组合及模型均未运行且不在本轮范围。

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
