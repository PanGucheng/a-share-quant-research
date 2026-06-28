# Factor Research Toolchain Readiness V1

本文档回应当前阶段的方向调整：不继续把 Alpha158 做成单一研究对象，而是先检查因子研究与筛选工具链是否已经足够完整。只有工具链完整后，才适合引入更多开源因子源并开始大规模研究。

## 1. 阶段定位

本阶段只做 readiness 审计和最小闸门实现：

- 不替换现有 Qlib baseline。
- 不训练新模型。
- 不调整具体交易策略。
- 不引入复杂 UI。
- 不修改 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 等开源评价口径。
- 不绕过已有 `data_quality` 和 `tradability` 结果。

Alpha158 的角色应从“继续深入调参的唯一对象”切换为“验证研究机器是否可靠的基准因子族”。接下来真正需要推进的是多来源因子接入、批量评估、筛选和候选池冻结能力。

## 2. 已具备能力

当前项目已经具备以下基础：

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| Qlib baseline | 已验证 | LightGBM + Alpha158 baseline 可复现。 |
| data_quality | 已有 | 为因子研究提供数据诊断输入。 |
| tradability | 已有 | 因子评价前置过滤使用流动性和可交易性标签。 |
| open-source evaluator coexistence | 已跑通 | Alphalens Reloaded、jqfactor_analyzer、Qlib eval、本项目现有评价结果共存。 |
| batch runner | 已有 | 支持 dry-run、分批、断点续跑、manifest、日志和输出摘要。 |
| Alpha158 full pipeline | 已跑通 | 158 个 Qlib Alpha158 已进入表达式适配、批量评价、筛选、judgement、候选池、组合 smoke 和 OOS 稳定性诊断流程；其中 155 个进入 runnable catalog，3 个保留为 holdout。 |
| TA promoted source | 已跑通 | `bukosabino/ta` 已完成 adapter smoke、剩余 74 个 eligible 因子 batch V4 和 promotion；77 个进入 promoted runnable catalog，2 个保留为 holdout。 |
| Alpha101 promoted source | 已跑通 | KunQuant Alpha101 已完成 source audit、82 公式 adapter、candidate71 V4 batch 和 promotion；64 个进入 promoted runnable catalog，18 个保留为 holdout。 |
| multi-source screening contract | 已跑通 | Alpha158、TA、Alpha101 和 Alpha360 promoted 因子已进入统一 screening input、candidate board、candidate pool 和 contract status。 |
| multi-source judgement contract | 已跑通 | 在统一 screening input 之上生成 679 行 judgement board、342 个 research candidates 和 328 个 new-source alpha probes。 |
| new-source probe diagnostics | 已跑通 | 对 328 个 probes 生成诊断看板，120 个进入相关性/可交易性暴露诊断，50 个进入 portfolio smoke，readiness contract pass。 |
| new-source probe review | 已跑通 | 识别 4 个高相关冗余组、19 个可交易性暴露 watchlist，并收缩出 3 个严格 OOS extension candidates。 |
| open-source expansion audit | 已跑通 | 已审计 8 个下一阶段因子/数据来源；`qlib_alpha360` 为 direct adapter 下一候选，FactorTest 为 data audit 下一候选。 |

## 3. 当前缺口

在大规模扩张因子池前，最小缺口如下：

| 缺口 | 影响 | 处理方式 |
| --- | --- | --- |
| 后续来源 adapter 尚未接入统一闸门 | Alpha101、基本面、行业风格等来源容易重复造轮子 | 沿用 source manifest -> adapter audit -> V4 batch -> promotion/holdout -> generic screening 的流程。 |
| 后续更丰富数据尚未接入 | 基本面、行业/风格暴露和更长 OOS 时段还不能参与 judgement | 下一阶段继续参考开源数据/因子框架，按相同闸门接入更多数据和因子源。 |

## 4. 新增闸门

新增配置：

```text
configs/factor_research_toolchain_readiness_v1.yaml
```

新增脚本：

```text
scripts/audit_factor_research_toolchain_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

输出目录：

```text
outputs/factor_research_toolchain_readiness_v1/current
```

关键输出：

```text
catalog_summary.csv
factor_catalog_entries.csv
factor_stage_counts.csv
source_readiness.csv
required_output_contracts.csv
config_status.csv
toolchain_readiness_checks.csv
toolchain_readiness_report.md
```

## 5. Readiness 判定

大规模研究不能只看“已有因子能否跑通”，而要同时满足：

| 检查项 | 要求 |
| --- | --- |
| prefilter policy | `factor_catalog.yaml` 和 `source_manifest.yaml` 都声明必须使用 `data_quality` 与 `tradability`。 |
| evaluator systems | V4 同时保留 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和 project_current。 |
| batch runner | 存在可复现、可恢复、可分批运行的配置和脚本。 |
| required output contracts | Alpha158 已验证输出必须存在，作为后续多来源研究的对照；runnable 与 holdout 要分别留痕。 |
| runnable factor inventory | 至少有足够数量的可运行因子证明工具链容量。 |
| new source adapter inventory | 至少一个非 Alpha158 开源来源完成 promoted runnable adapter。 |
| generic multi-source screening | 筛选与候选池接口能承接多个来源，而不是只服务 Alpha158。 |
| generic multi-source judgement | judgement board 能承接 Alpha158、TA、Alpha101 和后续 promoted 因子，并区分默认 alpha、研究 probe、monitor、data watch 与 holdout。 |

## 6. 当前结论

当前结论是：

```text
Alpha158 研究链路 ready。
TA promoted 新来源 ready。
多来源大规模因子研究 ready。
```

当前不是评价体系不够，也不是缺少 Alpha158 细节研究。Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和 project_current 已经共存；TA 也已提供 77 个 promoted runnable 新来源因子。V3.22 已经冻结一个能同时承接 Alpha158、TA、Alpha101 和后续来源的通用候选池契约。

V3.22 后 readiness 关键状态：

```text
total_runnable: 247
new_source_runnable: 77
new_source_adapter_inventory: pass
generic_multi_source_screening: pass
overall_status: ready
```

V3.24 后 readiness 关键状态：

```text
total_runnable: 311
new_source_runnable: 141
new_source_adapter_inventory: pass
generic_multi_source_screening: pass
overall_status: ready
```

V3.26 后 readiness 关键状态：

```text
total_runnable: 311
new_source_runnable: 141
generic_multi_source_screening: pass
generic_multi_source_judgement: pass
multi_source_judgement_board rows: 319
multi_source_new_source_alpha_probes rows: 29
overall_status: ready
```

V3.27 后新增 readiness contract：

```text
open_source_factor_expansion_candidates rows: 8
open_source_factor_expansion_next_steps rows: 3
top direct adapter candidate: qlib_alpha360
top data audit candidate: factortest_exposure_diagnostics
```

V3.28 后新增 Alpha360 adapter smoke contract：

```text
alpha360_formula_inventory rows: 360
alpha360_smoke_catalog rows: 24
alpha360_smoke_expression_table rows: 24
alpha360_smoke_expression_summary rows: 24
overall_status: ready
```

V3.29 后新增 Alpha360 V4 smoke contract：

```text
alpha360_smoke_external_factor_summary rows: 22
alpha360_smoke_evaluator_status rows: 66
alpha360_smoke_metric_index rows: 396
alpha360_smoke_context_metric_index rows: 4,224
overall_status: ready
```

V3.30 后新增 Alpha360 batch dry-run contract：

```text
alpha360_batch_candidate_catalog rows: 358
alpha360_adapter_holdout_catalog rows: 2
alpha360_batch_catalog_audit rows: 4
alpha360_batch_dry_run_manifest rows: 72
alpha360_batch_dry_run_selected_catalog rows: 358
overall_status: ready
```

V3.31 后新增 Alpha360 batch frame 与 smoke batch1 contract：

```text
alpha360_batch_expression_table rows: 358
alpha360_batch_expression_summary rows: 358
alpha360_batch_smoke_manifest rows: 1
alpha360_batch_smoke_output_summary rows: 1
overall_status: ready
```

V3.32 后新增 Alpha360 完整 batch / promotion / multi-source contract：

```text
total_runnable: 669
new_source_runnable: 499
alpha360_execution_manifest rows: 72
alpha360_candidate358_metric_index rows: 6,444
alpha360_batch_promoted_catalog rows: 358
multi_source_screening_input rows: 679
multi_source_judgement_board rows: 679
multi_source_new_source_alpha_probes rows: 328
overall_status: ready
```

V3.33 后新增 new-source probe diagnostics contract：

```text
new_source_probe_inventory rows: 328
new_source_probe_diagnostic_board rows: 328
selected_probe_factor_coverage rows: 120
selected_probe_correlation_top_pairs rows: 200
selected_probe_tradability_exposure rows: 120
portfolio_smoke_weights rows: 50
portfolio_smoke_summary rows: 1
new_source_probe_diagnostics: pass
overall_status: ready
```

V3.34 后新增 new-source probe review contract：

```text
probe_review_board rows: 328
probe_review_redundancy_pairs rows: 200
probe_review_redundancy_groups rows: 4
probe_review_tradability_exposure_watchlist rows: 19
probe_review_oos_extension_candidates rows: 3
new_source_probe_review: pass
overall_status: ready
```

这表示“引入更多因子”的入口已经打开，并且已由 TA、Alpha101 与 Alpha360 三类非 seed 来源验证；第一层 probes 诊断与 review 也已经接入 readiness。下一阶段应为 3 个严格 OOS candidates 扩展 recent OOS factor frame，并继续推进行业/风格数据能力审计。所有扩张仍需沿用 adapter audit、V4 batch、promotion/holdout、multi-source screening、multi-source judgement、probe diagnostics 和 probe review contract。

## 7. 下一步目标

下一步不继续围绕 Alpha158 微调，也不急着训练模型，而是进入“严格 OOS 扩展 + 暴露数据能力审计”阶段：

1. 为 `alpha360_HIGH36`、`alpha360_HIGH37`、`alpha360_HIGH40` 扩展 recent OOS factor frame 与 OOS 诊断。
2. 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
3. 继续接入更多开源因子源，但必须沿用 source audit、adapter、V4 batch、promotion/holdout、multi-source screening、multi-source judgement 的路径。
4. 工具链继续保持“不训练模型、不改策略、不改开源评价口径”的边界，直到候选池有足够多经过多层筛选的新来源因子。
