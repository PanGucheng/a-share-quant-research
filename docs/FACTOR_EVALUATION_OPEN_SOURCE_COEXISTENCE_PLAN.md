# V3.6 开源评价体系共存计划

本文档用于修正下一阶段因子研究路线：先不要急着自研一套综合评价体系，而是优先参考并复现成熟开源项目的评价口径，让多个评价体系在本项目中并行产出结果。等结果跑通、口径可追溯、差异可解释之后，再增加主观判断参数和本项目自己的综合筛选规则。

## 1. 核心原则

1. 开源优先，不重新发明已有评价指标。
2. 评价体系先共存，不强行合并成一个分数。
3. 只写适配层，不随意改动开源评价逻辑。
4. 每个外部评价结果必须标明来源、版本、commit、license 和本地适配方式。
5. 继续保留本项目已有的 `data_quality` 和 `tradability` 约束，所有因子评价必须先经过可交易性过滤。
6. 暂不训练新模型，暂不调整具体策略，暂不引入复杂 UI，暂不做实盘。

## 2. 为什么要这样改

当前项目已经具备基本的因子研究模块，包括 IC、Rank IC、ICIR、分组收益、换手率、覆盖率、缺失率、相关性、单调性和中性化后保留率。但这些指标多数是本项目实现的简化版。

在进入大规模因子池之前，最重要的不是继续研究少量常见因子，而是降低评价口径出错的风险。成熟开源项目已经沉淀了大量指标定义和边界处理逻辑，下一阶段应优先让这些评价体系原样跑通。

## 3. 借鉴与复用来源

临时参考仓库位于：

```text
tmp/reference_repos/
```

该目录被 `.gitignore` 忽略，不直接作为项目依赖提交。正式引入时需要在文档和源码中记录来源。

| source | planned role | reuse policy |
| --- | --- | --- |
| `alphalens-reloaded` | 因子评价主参考：IC、Rank IC、分组收益、分位换手、factor returns、alpha/beta、rank autocorrelation | 优先照搬评价函数或调用原包；不改核心指标口径 |
| `jqfactor_analyzer` | A 股风格参考：行业分组、行业中性、中文报告组织、分组 IC、月度 IC、top-bottom 收益 | 优先复用评价和预处理口径；行业/权重数据由本项目适配 |
| `Qlib` | 与主线框架保持兼容：数据读取、已有 Alpha158/Alpha360、风险分析工具 | 保持 Qlib baseline，不替换主线 |
| `qlib_factor_platform` | 模块组织、配置化 workflow、因子管理方式 | 只借鉴组织方式，不引入复杂 UI |
| `ta` | 技术指标因子池来源 | 后续用于批量扩张价量/技术因子，不作为评价体系 |
| `KunQuant` / `Ginkgo_Alpha101` | Alpha101/Alpha158 公式和高性能计算参考 | 后续用于因子池扩张，先不改评价模块 |
| `FactorTest` / `multi-factor` | A 股因子测试、基本面因子、行业/风格暴露参考 | 后续用于数据层与基本面因子扩展 |

## 4. 目标架构

下一阶段新增的是“开源评价适配层”，不是替换现有模块。

```text
Qlib provider
  -> data_quality diagnostics
  -> tradability labels
  -> factor registry / factor values
  -> tradable_only factor data adapter
      -> alphalens-compatible evaluator
      -> jqfactor-compatible evaluator
      -> qlib-compatible evaluator
      -> current project evaluator
  -> coexistence report
  -> later: project judgement layer
```

现有模块继续保留：

```text
data_quality/
tradability/
factor_research/
outputs/factor_research_v3/
outputs/factor_screening_v3/
outputs/factor_candidate_pool_v3/
```

新增模块建议：

```text
factor_research/
  external/
    __init__.py
    source_manifest.yaml
    adapters.py
    alphalens_adapter.py
    jqfactor_adapter.py
    qlib_eval_adapter.py
    coexistence_report.py
```

如果后续需要复制少量开源源码，建议放在：

```text
third_party/
  evaluator_sources/
    SOURCES.md
    alphalens_reloaded/
    jqfactor_analyzer/
```

所有复制文件必须保留原 license 说明和来源路径。默认优先通过本地 reference repo 或 pip 包调用，只有依赖不稳定或接口不适配时才考虑 vendor。

## 5. 输出结构

不要把多个项目的结果揉成一个 CSV。先让它们并列输出。

```text
outputs/factor_evaluation_v4/<run_name>/
  source_manifest.csv
  data_adapter_report.md
  factor_data_alphalens_sample.csv
  factor_data_jqfactor_sample.csv

  alphalens_reloaded/
    information_table.csv
    ic_series.csv
    mean_return_by_quantile.csv
    factor_returns.csv
    factor_alpha_beta.csv
    quantile_turnover.csv
    rank_autocorrelation.csv
    report.md

  jqfactor_analyzer/
    ic_summary.csv
    ic_series.csv
    monthly_ic.csv
    ic_by_group.csv
    mean_return_by_quantile.csv
    top_bottom_spread.csv
    quantile_turnover.csv
    report.md

  qlib_eval/
    risk_analysis.csv
    indicator_analysis.csv
    report.md

  project_current/
    factor_neutralized_summary.csv
    factor_neutralized_group_return_summary.csv
    factor_neutralized_correlation.csv
    factor_exposure_correlation.csv
    report.md

  coexistence_summary.md
```

## 6. 第一阶段实施计划

### 6.1 来源清单与 license 记录

目标：

- 为每个参考项目记录 repo、commit、license、计划复用文件、计划复用函数。
- 明确哪些是“直接调用”，哪些是“复制源码”，哪些只是“设计参考”。
- 任何复制源码都不得混入本项目自研逻辑。

交付：

```text
factor_research/external/source_manifest.yaml
docs/FACTOR_EVALUATION_SOURCE_MANIFEST.md
```

验收：

- 每个外部指标都能追溯到项目、文件、函数。
- 文档写清楚本项目只负责数据适配和结果汇总。

### 6.2 统一数据适配层

目标：

- 从现有 Qlib provider、factor registry、label 和 tradability 输出中生成不同项目需要的输入格式。
- 统一执行 `tradable_only` 前置过滤。
- 保留原始样本数、过滤后样本数、覆盖率、缺失率。

适配格式：

| target | input schema |
| --- | --- |
| Alphalens | MultiIndex `(date, asset)`，列包含 `factor`、forward returns、`factor_quantile`，可选 `group` |
| jqfactor_analyzer | factor Series/DataFrame、prices、groupby、weights、periods |
| Qlib eval | prediction/score 与 label 对齐后的 DataFrame |
| project_current | 复用现有 `factor_research` 长表和中性化输出 |

交付：

```text
factor_research/external/adapters.py
outputs/factor_evaluation_v4/<run>/data_adapter_report.md
```

验收：

- 同一批因子能导出至少 Alphalens 和 jqfactor 两种输入样本。
- 适配层不计算评价指标，只转换数据。
- 报告中清楚说明收益周期、T+1 假设、可交易性过滤比例。

### 6.3 开源评价器并行运行

目标：

- 对同一批小样本因子并行运行多个评价体系。
- 不改开源项目核心计算函数。
- 各体系结果分别落盘，只做轻量汇总。

第一批跑通因子：

- `rev_5`
- `rev_20_exclude_5`
- `std_20`
- `amount_mean_20`
- `downside_std_20`

第一批周期：

- `1D`
- `5D`
- `10D`
- `20D`

交付：

```text
scripts/run_factor_evaluation_v4.py
outputs/factor_evaluation_v4/liquid2000_open_source_eval/
```

验收：

- Alphalens 风格结果、jqfactor 风格结果、本项目当前结果同时存在。
- 结果中能看出各体系口径差异，不强行给出单一结论。
- 若某个外部体系因依赖或字段缺失无法运行，必须输出 failure reason。

### 6.4 更多数据层探测

目标：

- 明确当前 Qlib provider 里有哪些字段可用于更完整的因子评价。
- 优先探测行业、市值、指数成分、上市天数、ST、停牌、涨跌停、基准指数收益。
- 不在字段未确认前硬写行业中性或市值中性逻辑。

交付：

```text
scripts/inspect_provider_fields.py
outputs/data_inventory/provider_field_inventory.csv
outputs/data_inventory/provider_field_inventory_report.md
```

验收：

- 每个候选数据层标记为 `available`、`missing` 或 `needs_external_source`。
- 后续因子池扩张能知道哪些类别能马上做，哪些需要补数据。

### 6.5 批量因子池接口准备

目标：

- 为后续大量扩张因子池做工程准备。
- 因子注册时必须记录来源项目、公式来源、依赖字段、预期方向、类别、是否启用。
- 批量运行时允许部分因子失败，并记录失败原因。

建议注册字段：

```text
factor_name
category
source_project
source_file
source_function
source_commit
license
expected_direction
required_fields
enabled
notes
```

交付：

```text
factor_research/factor_catalog.yaml
factor_research/external/factor_catalog_loader.py
outputs/factor_evaluation_v4/<run>/factor_failure_reasons.csv
```

验收：

- 能注册来自 Qlib Alpha158、`ta`、Alpha101 参考项目的因子元信息。
- 因子计算失败不会中断整批任务。

## 7. 第二阶段：主观判断层

只有在多个开源评价体系跑通后，才新增本项目自己的判断层。

主观判断层不替代开源结果，只在其上做标注：

```text
source results
  -> project judgement parameters
  -> candidate labels
```

可加入的主观参数：

- 更偏好 10D/20D，弱化 1D。
- 更偏好低换手。
- 更偏好可解释性强、数据覆盖稳定的因子。
- 对高度暴露于流动性/波动率/市值的因子降级。
- 对多个评价体系一致通过的因子升级。
- 对不同体系冲突明显的因子标记为 `needs_review`。

候选标签建议：

| label | meaning |
| --- | --- |
| `alpha_candidate` | 多体系表现较一致，可进入后续组合/模型候选池 |
| `risk_control` | 更适合作为风险、波动率、流动性控制变量 |
| `style_exposure` | 主要反映风格暴露，不直接当 alpha |
| `redundant` | 与已入池因子高度相关 |
| `needs_review` | 多体系结论冲突或依赖数据不完整 |
| `rejected` | 覆盖率、稳定性、换手或方向性明显不满足 |

## 8. 风险与防错规则

1. 不混淆“复制开源评价函数”和“自研改写评价函数”。
2. 不把不同项目的 ICIR、收益分组、换手率直接横向比较，必须注明口径。
3. 不绕过 `tradability`，否则会把不可交易样本误判为有效 alpha。
4. 不在行业/市值数据缺失时伪造行业中性或市值中性结论。
5. 不把 `1D` 结果当成最终目标，个人投资者阶段仍优先看 `10D/20D`。
6. 不在评价体系未跑通前大规模训练模型。

## 9. 下一步执行顺序

建议按以下顺序推进：

1. 建立 `source_manifest.yaml`，把 Alphalens、jqfactor、Qlib、qlib_factor_platform、ta、Alpha101 等来源登记清楚。
2. 实现只做数据转换的 adapter，不在 adapter 中计算指标。
3. 先用 5 个已存在因子跑通 Alphalens 和 jqfactor 风格评价。
4. 增加 provider 字段探测，确认行业、市值、指数成分等数据可用性。
5. 增加 `factor_catalog.yaml`，为大规模因子池扩张做元数据准备。
6. 在结果稳定后，再实现本项目自己的 judgement layer。

## 10. 阶段目标

V3.6 完成时，本项目应达到：

- 能保留并复现多个开源评价体系的原始结果。
- 能清楚解释每个指标来自哪里、口径是什么。
- 能把 Qlib 数据、可交易性标签、因子值转换为多个评价项目需要的输入。
- 能输出并列结果，而不是过早给出自研单分数。
- 能支撑后续从 Qlib Alpha158/Alpha360、`ta`、Alpha101 等来源批量扩张因子池。

完成 V3.6 后，再进入 V3.7：大规模因子池扩张与批量筛选。
