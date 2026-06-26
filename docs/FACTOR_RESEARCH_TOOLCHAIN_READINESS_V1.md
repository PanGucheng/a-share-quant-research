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

## 3. 当前缺口

在大规模扩张因子池前，最小缺口如下：

| 缺口 | 影响 | 处理方式 |
| --- | --- | --- |
| 多来源 screening / candidate pool 契约尚未统一 | 后续 TA、Alpha101、Alpha158 难以共用候选池 | 将 Alpha158 专用输出抽象成通用 contract。 |
| 多来源候选池缺少机器可检验 contract | 容易把未评价、holdout 或不同口径的因子混入候选池 | 为筛选输入、候选池、holdout 和晋级决策建立统一输出表。 |
| 后续来源 adapter 尚未接入统一闸门 | Alpha101、基本面、行业风格等来源容易重复造轮子 | 沿用 source manifest -> adapter audit -> V4 batch -> promotion/holdout -> generic screening 的流程。 |

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

当前结论是：

```text
Alpha158 研究链路 ready。
TA promoted 新来源 ready。
多来源大规模因子研究 partial。
```

当前不是评价体系不够，也不是缺少 Alpha158 细节研究。Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和 project_current 已经共存；TA 也已提供 77 个 promoted runnable 新来源因子。真正缺口是筛选层仍偏 Alpha158 专用，尚未冻结一个能同时承接 Alpha158、TA、Alpha101 和后续来源的通用候选池契约。

V3.21 后 readiness 关键状态：

```text
total_runnable: 247
new_source_runnable: 77
new_source_adapter_inventory: pass
generic_multi_source_screening: partial
overall_status: partial
```

这表示“引入更多因子”的入口已经打开，但大规模研究前还需要先把多来源筛选输入、主观判断列、候选池角色和 holdout 规则统一起来。

## 7. 下一步目标

下一步不继续围绕 Alpha158 微调，也不急着训练模型，而是进入“通用多来源筛选与候选池契约”阶段：

1. 读取 Alpha158 全量筛选输入和 TA promoted77 metric index，生成统一 screening input。
2. 明确每个候选因子的 `source_project`、`stage`、`runnable`、`holdout_reason`、评价系统通过状态和核心指标列。
3. 输出多来源 candidate board，先让不同开源评价体系结果共存，不改写其定义。
4. 输出多来源 candidate pool，区分 `alpha_candidate`、`risk_control`、`monitor`、`holdout` 等角色。
5. 将上述输出加入 readiness required contracts，使大规模新增因子前必须先通过工具链检查。
6. 通过后再继续接 Alpha101、更多 TA 扩展、基本面和行业风格数据。
