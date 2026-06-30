# Alpha158 表达式接入与首批真实评价阶段计划

本文档设计一个完整阶段：把已经完成来源审计的 Qlib Alpha158 metadata，推进到“首批 Alpha158 因子可以被现有 V4 开源评价体系真实评价”的状态。

本阶段仍然只服务于因子研究与因子筛选工具链，不训练新模型、不调整实盘策略、不改开源评价口径。

## 1. 阶段定位

当前状态：

- Qlib Alpha158 公式来源已审计。
- 158 个公式全部来自本地 Qlib `Alpha158DL.get_feature_config()`。
- 当前 derived provider 具备 Alpha158 所需字段。
- 首批 20 个 Alpha158 条目已经生成 metadata catalog。
- Alpha158 条目仍是 `enabled: false`、`runnable: false`，不能进入真实 V4 评价。

本阶段目标：

```text
Alpha158 formula inventory
  -> Qlib expression adapter
  -> precomputed factor frame
  -> tradability/data_quality filtered V4 input
  -> Alphalens/jqfactor/Qlib/context evaluation
  -> first-batch candidate summary
```

阶段完成后，项目应具备：

- 用 Qlib 表达式稳定计算一批 Alpha158 因子。
- 对首批 20 个 Alpha158 因子运行完整 V4 开源评价。
- 评价结果仍与现有体系共存，不产生自研综合分。
- 只有通过 adapter 验证和 V4 smoke 的 Alpha158 条目才允许标记为 `runnable: true`。

## 2. 非目标

本阶段明确不做：

- 不重写 Alpha158 公式。
- 不手工改 Alphalens Reloaded 或 jqfactor_analyzer 指标。
- 不新增主观综合评分。
- 不训练 LightGBM/XGBoost/CatBoost/深度学习模型。
- 不扩大到 Alpha101、`ta` 全量指标或基本面因子。
- 不启用行业/市值中性，除非有 point-in-time 行业和市值数据。
- 不做实盘、自动下单或资金管理。

## 3. 设计原则

1. **开源优先**：Alpha158 表达式直接使用 Qlib 生成结果，避免手写复刻。
2. **先 adapter，后筛选**：表达式计算、索引对齐、字段覆盖、缓存和验证必须先通过。
3. **继续复用现有约束**：所有 Alpha158 评价必须经过 `data_quality` 和 `tradability` 前置过滤。
4. **首批小样本 smoke**：先跑 20 个 Alpha158 因子，不直接跑 158 个。
5. **保留原始评价结果**：Alphalens Reloaded、jqfactor_analyzer、Qlib eval、project_current 和 context 输出继续并列。
6. **可恢复批量运行**：使用 V1 batch runner，避免中断后全量重跑。

## 4. 目标目录与文件

建议新增或更新：

```text
configs/
  alpha158_expression_adapter_v1.yaml
  factor_evaluation_v4_alpha158_first20.yaml
  factor_evaluation_batch_v1_alpha158_first20.yaml

factor_research/
  expression_adapter.py
  alpha158_registry.py

scripts/
  build_alpha158_expression_frame_v1.py
  validate_alpha158_expression_frame_v1.py
  promote_alpha158_catalog_entries_v1.py

docs/
  ALPHA158_EXPRESSION_EVALUATION_STAGE_PLAN.md
  ALPHA158_EXPRESSION_ADAPTER_V1.md

outputs/
  alpha158_expression_frame_v1/
  factor_evaluation_v4/alpha158_first20_smoke/
  factor_evaluation_batch_v1/alpha158_first20/
```

## 5. 模块设计

### 5.1 Expression Adapter

核心职责：

- 读取 `outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv`。
- 选择一批 catalog factor，例如首批 20 个。
- 将 `catalog_name` 映射到 Qlib 表达式。
- 调用 Qlib `D.features` 计算表达式。
- 输出按 `datetime, instrument` 对齐的宽表。

建议输出 schema：

```text
datetime
instrument
alpha158_KMID
alpha158_KLEN
...
alpha158_MA10
```

关键防错：

- 保持 Qlib 原始表达式，不手写等价公式替代。
- 只允许从审计 inventory 中读取表达式。
- 输出列名必须使用 `catalog_name`，避免与 Qlib 原始因子名或本项目基础因子重名。
- 记录 provider、market、start/end、Qlib commit、表达式列表和 cache digest。

### 5.2 Label 与基础字段对齐

V4 当前依赖 `load_window_frame()` 生成基础字段与 T+1 labels。因此 Alpha158 adapter 不能单独绕开现有数据流。

建议实现方式：

1. 继续用现有 `load_window_frame()` 生成基础字段、labels、tradability 和 data_quality flags。
2. 将 Alpha158 expression frame 按 `datetime, instrument` merge 到现有 frame。
3. 使用同一套 `to_factor_data()` 转换为 V4 evaluator 输入。

好处：

- 不重复实现 label 逻辑。
- 不绕过 tradability 和 data_quality。
- 不影响已有基础因子 V4 流程。

### 5.3 Registry / Catalog 接入

首批 Alpha158 因子需要进入 `FactorSpec` 风格的注册表，但不能手工维护 20 条 Python 常量。

建议新增：

```text
factor_research/alpha158_registry.py
```

职责：

- 从 `alpha158_catalog_first_batch.yaml` 读取 entries。
- 将 `runnable: true` 的条目转换成临时 `FactorSpec`。
- 在 V4 alpha158 config 中使用这些 specs。

防错：

- 如果 catalog entry 仍是 `runnable: false`，真实运行必须失败。
- 如果 expression frame 缺少任一因子列，真实运行必须失败。
- 如果 selected factor 不在 catalog 中，真实运行必须失败。

### 5.4 V4 Runner 扩展方式

推荐最小改动：

- 不复制 `run_factor_evaluation_v4.py`。
- 在 V4 runner 中增加可选 `factor_frame` 配置。
- 当配置存在时，在基础 `frame` 加载完成后 merge 预计算因子。
- `specs` 来源允许 current registry 与 external catalog specs 合并。

建议配置：

```yaml
external_factor_frame:
  enabled: true
  path: "outputs/alpha158_expression_frame_v1/first20_main_research/factor_frame.pkl"
  catalog_path: "outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml"
  factor_columns:
    - "alpha158_KMID"
    - "alpha158_KLEN"
```

保守替代方案：

- 新写 `scripts/run_factor_evaluation_v4_alpha158.py` 包装 V4 函数。
- 只在包装层 merge expression frame 和 specs。

优先选择第一种，除非改动 V4 runner 会让现有配置风险过大。

## 6. 分阶段实施

### 6.1 Adapter Skeleton

目标：

- 新增表达式 adapter 模块和构建脚本。
- 能读取首批 20 个 Alpha158 metadata。
- 能生成 expression frame。

交付：

```text
factor_research/expression_adapter.py
scripts/build_alpha158_expression_frame_v1.py
configs/alpha158_expression_adapter_v1.yaml
outputs/alpha158_expression_frame_v1/first20_main_research/
```

验收：

- 输出至少包含 `datetime, instrument` 和 20 个 Alpha158 列。
- 行数与 Qlib 查询结果一致。
- 无重复 `datetime, instrument`。
- 所有选中列至少有非空值。
- 写出 `expression_frame_manifest.json` 和 `expression_frame_summary.csv`。

### 6.2 Adapter Correctness Validation

目标：

- 不直接相信表达式输出，要做最小数值核对。

建议验证：

| factor | validation |
| --- | --- |
| `alpha158_KMID` | 与 `($close-$open)/$open` 手工计算对比 |
| `alpha158_KLEN` | 与 `($high-$low)/$open` 手工计算对比 |
| `alpha158_ROC5` | 与 Qlib `Ref($close, 5)/$close` 输出完整性检查 |
| `alpha158_MA5` | 与 Qlib `Mean($close, 5)/$close` 输出完整性检查 |

注意：

- 对 rolling/Ref 类公式，优先核查覆盖率、极值、日期对齐和缺失窗口，不轻易用 pandas 手写逻辑替代 Qlib 语义。
- 手工验证只用于 sanity check，不作为替代公式。

交付：

```text
scripts/validate_alpha158_expression_frame_v1.py
outputs/alpha158_expression_frame_v1/first20_main_research/validation_report.md
```

验收：

- 无重复键。
- `KMID/KLEN` 与手工计算误差在 `1e-10` 内。
- 首批 20 个因子覆盖率报告存在。
- 缺失集中在合理 rolling warm-up 区间。

### 6.3 V4 First20 Smoke

目标：

- 首次把 Alpha158 首批 20 个因子送入现有 V4 开源评价体系。

建议先跑单 batch：

```text
factor_evaluation_v4_alpha158_first20.yaml
```

评价范围：

```text
market: all_stock_shsz_liquid2000
window: main_research_2021_2023
labels: label_10d_t1,label_20d_t1
systems: alphalens_reloaded,jqfactor_analyzer,qlib_eval
context: enabled
```

交付：

```text
outputs/factor_evaluation_v4/alpha158_first20_smoke/
```

验收：

- V4 运行完成。
- `evaluator_status.csv` 对 20 个因子有记录。
- `factor_failure_reasons.csv` 中不能出现 adapter/缺列/空数据错误。
- `context/context_evaluator_status.csv` 无 failed。
- `context/context_metric_index.csv` 非空。
- 已知 jqfactor pandas 2.x 的 `factor_returns/factor_alpha_beta` 兼容问题允许继续记录为 partial，不作为本阶段阻塞。

### 6.4 Batch Runner Integration

目标：

- 让 Alpha158 首批因子走 batch runner，而不是一次性手工跑。

交付：

```text
configs/factor_evaluation_batch_v1_alpha158_first20.yaml
outputs/factor_evaluation_batch_v1/alpha158_first20/
```

验收：

- dry-run 能生成 4 个 batch，每批 5 个因子。
- 真实运行支持断点续跑。
- 每个 batch 有独立 V4 输出。
- `batch_output_summary.csv` 汇总 metric rows、context metric rows 和 failure rows。

### 6.5 Catalog Promotion

目标：

- 只有通过 adapter validation 和 V4 smoke 的 Alpha158 条目才能从 metadata 状态晋升。

建议新增脚本：

```text
scripts/promote_alpha158_catalog_entries_v1.py
```

晋升规则：

```yaml
enabled: true
runnable: true
compute_adapter: qlib_expression_frame_v1
stage: alpha158_first20_v4_smoke_passed
```

交付：

```text
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

验收：

- 晋升脚本必须读取 V4 evaluator status 和 context validator 输出。
- 若任一因子缺少 V4 输出或 context failed，不允许晋升。
- 原始 metadata catalog 保留，不覆盖。

### 6.6 First-Batch Summary

目标：

- 不做综合评分，但要给研究者一个可读摘要。

输出：

```text
outputs/factor_evaluation_v4/alpha158_first20_smoke/alpha158_first20_summary.md
outputs/factor_evaluation_v4/alpha158_first20_smoke/alpha158_first20_metric_index.csv
```

摘要内容：

- 各体系 pass/partial/failed 数量。
- Rank IC 均值范围。
- context 分组是否可用。
- 哪些因子只适合继续观察。
- 哪些因子因为缺失、低覆盖、评价失败需要暂缓。

注意：

- 不打综合分。
- 不直接说某因子可用于实盘。
- 不把 2021-2023 单窗口结果当成最终结论。

## 7. 配置设计

### 7.1 Expression Adapter Config

建议文件：

```text
configs/alpha158_expression_adapter_v1.yaml
```

建议内容：

```yaml
provider_uri: "E:/qlib_prj/qlib_data/cn_data_community_20260609_derived"
market: "all_stock_shsz_liquid2000"
start: "2020-10-01"
end: "2024-02-29"
catalog_path: "outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml"
inventory_path: "outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv"
output_dir: "outputs/alpha158_expression_frame_v1/first20_main_research"
cache:
  enabled: true
  refresh: false
```

说明：

- start 要早于研究窗口，给 rolling/Ref 类因子留 warm-up。
- end 要晚于研究窗口，保持与现有 label padding 习惯一致。

### 7.2 V4 Alpha158 Config

建议文件：

```text
configs/factor_evaluation_v4_alpha158_first20.yaml
```

核心：

```yaml
external_factor_frame:
  enabled: true
  path: "outputs/alpha158_expression_frame_v1/first20_main_research/factor_frame.pkl"
  catalog_path: "outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml"
```

## 8. 输出保留策略

建议纳入 Git：

- adapter 脚本和配置。
- manifest、summary、validation report。
- 小型 metric index。
- catalog promotion 文件。

建议忽略：

- 大型 `factor_frame.pkl`。
- 每个 batch 的大体积逐日明细。
- stdout/stderr runtime logs。

需要更新 `.gitignore`：

```text
outputs/alpha158_expression_frame_v1/*/factor_frame.pkl
outputs/factor_evaluation_batch_v1/alpha158_first20/runs/
```

## 9. 风险与防错

| risk | mitigation |
| --- | --- |
| 表达式计算结果与 label 日期错位 | 复用现有 `load_window_frame()` 和 T+1 label 逻辑，merge 后验证日期范围 |
| 误把 metadata 因子当 runnable | batch runner 已阻止 `runnable: false` 真实运行 |
| rolling warm-up 缺失被误判为数据问题 | validation report 单独统计 warm-up 缺失 |
| V4 运行时间过长 | 首批 20 个分 batch；必要时先跑 5 个 smoke |
| jqfactor pandas 2.x 部分函数失败 | 继续记录 failure reason，不改开源口径 |
| Alpha158 结果与现有基础因子高度重复 | 后续筛选阶段用相关性和 redundancy 标记，不提前删除 |

## 10. 阶段完成标准

本阶段全部完成需要满足：

- [x] Alpha158 expression frame builder 可运行。
- [x] 首批 20 个因子的 expression frame 生成成功。
- [x] adapter validation 通过。
- [x] V4 first20 smoke 完成。
- [x] context validator 通过。
- [x] batch runner 能 dry-run 和真实运行首批 20 个因子。
- [x] 通过 smoke 的 Alpha158 catalog entries 被单独晋升为 runnable catalog。
- [x] 输出 first-batch summary，但不生成综合分。
- [x] 文档说明 Alpha158 与 Qlib baseline、data_quality、tradability、V4 evaluation 和后续 screening 的关系。

## 11. 推荐执行顺序

1. 实现 `expression_adapter.py` 和 `build_alpha158_expression_frame_v1.py`。
2. 生成首批 20 个 Alpha158 expression frame。
3. 实现并运行 `validate_alpha158_expression_frame_v1.py`。
4. 扩展 V4 runner 支持 `external_factor_frame`。
5. 跑 3 到 5 个 Alpha158 因子的极小 smoke。
6. 跑首批 20 个 Alpha158 的 V4 smoke。
7. 用 batch runner 跑首批 20 个 batch 版本。
8. 晋升通过验证的 catalog entries。
9. 生成首批 summary。
10. 决定是否进入 Alpha158 全量 158 因子批量评价。

## 12. 阶段执行结果

状态：已完成。

主要结果：

```text
expression frame rows: 1,603,860
Alpha158 first batch factors: 20
adapter validation: pass
V4 first20 evaluator status:
  alphalens_reloaded: pass 20
  jqfactor_analyzer: partial_pass 20
  qlib_eval: pass 20
context status:
  pass: 240
  skipped_non_informative: 80
combined metric index rows: 4,200
batch count: 4
batch resume: batch_001-003 skipped_existing, batch_004 pass after interruption
```

新增实施文档：

```text
docs/ALPHA158_EXPRESSION_ADAPTER_V1.md
```

关键产物：

```text
outputs/alpha158_expression_frame_v1/first20_main_research/
outputs/factor_evaluation_v4/alpha158_first20_smoke/
outputs/factor_evaluation_batch_v1/alpha158_first20/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

保留边界：

- 不生成综合评分。
- 不因为首批 smoke 通过就进入实盘或模型训练。
- 不修改 Alphalens Reloaded、jqfactor_analyzer 或 Qlib eval 的原始指标口径。
- `factor_frame.pkl` 和 batch 逐因子大明细不进入 Git，只保留紧凑 summary 与 validation 结果。

## 13. 阶段之后的方向

如果本阶段顺利完成，下一阶段才考虑：

- Alpha158 全量 158 个因子分批评价。
- `ta` 技术指标因子小批量接入。
- Alpha101 来源的公式语义与数据字段审计。
- 因子筛选 judgement layer，但仍要保持开源评价原始结果并列。

如果首批 20 个 Alpha158 的评价体系或 adapter 暴露问题，应先修工具链，不扩因子池。
