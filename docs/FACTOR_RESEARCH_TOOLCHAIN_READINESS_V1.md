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

## 3. 当前缺口

在大规模扩张因子池前，最小缺口如下：

| 缺口 | 影响 | 处理方式 |
| --- | --- | --- |
| 非 Alpha158 来源尚无 promoted runnable adapter | 无法安全进入真正多来源研究 | 先选择一个开源来源做 adapter、审计和 smoke。 |
| 多来源 screening / candidate pool 契约尚未统一 | 后续 TA、Alpha101、Alpha158 难以共用候选池 | 将 Alpha158 专用输出抽象成通用 contract。 |
| source readiness 没有自动检查 | 容易把仅登记、未审计的因子源误放入批量评估 | 新增 readiness 审计脚本。 |
| 新因子源 license / local path / source file / runnable count 未统一出表 | 后续来源变多后难追踪 | 由 readiness 输出统一表。 |

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

## 6. 当前结论

预期结论应是：

```text
Alpha158 研究链路 ready。
多来源大规模因子研究 partial / blocked。
```

原因不是评价体系不够，而是非 Alpha158 因子源目前仍处于 `metadata_registered_adapter_pending` 或 formula reference 阶段。此时直接大规模跑新因子，容易把未审计字段、窗口、数据假设或 license 问题混进候选池。

V3.19 后，`ta` 已有 5 个 smoke-level runnable 因子，但仍未达到大规模阈值：

```text
new_source_runnable: 5
large_scale_threshold: 20
status: blocked
```

这表示 adapter 路径已经打通，但还需要对剩余 eligible TA 因子执行 batch V4 后才能进入大规模筛选。

## 7. 下一步目标

下一步不继续围绕 Alpha158 微调，而是进入“首个非 Alpha158 开源因子源 promoted adapter”阶段：

1. 优先选择 `ta` 作为首个来源，因为本地参考仓库已存在、license 为 MIT、入口函数清晰。
2. 审计 `ta/wrapper.py` 的 OHLCV 字段、窗口、是否存在未来函数、输出命名和 NaN 行为。
3. 新增最小 adapter，将 Qlib OHLCV 面板转换为 `ta` 所需 DataFrame，再转回项目因子 frame。
4. 只做少量 TA 因子 smoke，不立即全量评估。
5. smoke 通过后，才把 TA 因子登记为 runnable catalog entries，并进入 batch V4。
6. 同步抽象 multi-source screening/candidate-pool contract，让 Alpha158、TA、Alpha101 可以共用后续筛选流程。
