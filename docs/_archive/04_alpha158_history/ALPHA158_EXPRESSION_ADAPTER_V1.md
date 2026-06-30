# Alpha158 Expression Adapter V1

本文档记录 Alpha158 首批 20 个因子从 Qlib 原始表达式到本项目 V4 因子评价体系的最小闭环实现。

本阶段仍然只服务于因子研究与因子筛选工具链：不替换 Qlib 主线、不训练新模型、不改开源评价体系、不生成自研综合分。

## 1. 定位

本模块解决的问题是：把 Qlib Alpha158 中已经审计过的公式，作为外部预计算因子接入现有因子评价系统，同时继续复用 data_quality、tradability、T+1 labels 和 context。

数据流如下：

```text
Qlib Alpha158 source audit
  -> alpha158 formula inventory/catalog
  -> Qlib D.features expression calculation
  -> precomputed factor frame
  -> V4 load_window_frame labels/data_quality/tradability
  -> merge external factor frame
  -> Alphalens Reloaded / jqfactor_analyzer / Qlib eval / context
  -> batch runner and runnable catalog promotion
```

和其他模块的关系：

- Qlib baseline 仍是模型训练和官方工作流复现主线。
- data_quality 仍负责数据诊断；Alpha158 不绕过基础数据检查。
- tradability 仍是因子评价前置过滤条件；外部因子只是在过滤后的 V4 frame 上 merge。
- factor_evaluation_v4 继续保留开源评价体系原始输出。
- 后续 screening 和 portfolio backtest 只能消费评价后的候选结果，不能直接跳过因子研究层。

## 2. 新增与更新文件

新增配置：

```text
configs/alpha158_expression_adapter_v1.yaml
configs/factor_evaluation_v4_alpha158_smoke5.yaml
configs/factor_evaluation_v4_alpha158_first20.yaml
configs/factor_evaluation_v4_alpha158_batch_base.yaml
configs/factor_evaluation_batch_v1_alpha158_first20.yaml
```

新增模块与脚本：

```text
factor_research/expression_adapter.py
factor_research/alpha158_registry.py
scripts/build_alpha158_expression_frame_v1.py
scripts/validate_alpha158_expression_frame_v1.py
scripts/promote_alpha158_catalog_entries_v1.py
scripts/summarize_alpha158_first20.py
```

更新脚本：

```text
scripts/run_factor_evaluation_v4.py
scripts/run_factor_evaluation_batch_v1.py
```

关键输出：

```text
outputs/alpha158_expression_frame_v1/first20_main_research/
outputs/factor_evaluation_v4/alpha158_first20_smoke/
outputs/factor_evaluation_batch_v1/alpha158_first20/
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

## 3. Expression Frame

构建命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_v1.yaml
```

配置范围：

```text
provider_uri: E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
market: all_stock_shsz_liquid2000
date range: 2020-10-01 to 2024-02-29
factor count: 20
```

结果：

```text
rows: 1,603,860
factor columns: 20
output frame: outputs/alpha158_expression_frame_v1/first20_main_research/factor_frame.pkl
```

`factor_frame.pkl` 体积较大，已由 `.gitignore` 排除；Git 中只保留 manifest、summary、sample 和 validation report。

## 4. Correctness Validation

验证命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_v1.yaml
```

验证结果：

```text
duplicate datetime/instrument: pass
alpha158_KMID manual max_abs_error: 0.0
alpha158_KLEN manual max_abs_error: 0.0
all selected factors have values: pass
```

覆盖率：

```text
base kbar / price ratio factors: 0.996408
alpha158_ROC5: 0.995139
alpha158_ROC10: 0.994550
alpha158_ROC20: 0.994235
alpha158_ROC30: 0.994231
alpha158_ROC60: 0.994271
```

这些缺失主要来自停牌、生命周期和 rolling/ref warm-up，不在本阶段手工填补。

## 5. V4 External Factor Frame

`scripts/run_factor_evaluation_v4.py` 增加了可选配置：

```yaml
external_factor_frame:
  enabled: true
  path: "outputs/alpha158_expression_frame_v1/first20_main_research/factor_frame.pkl"
  catalog_path: "outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml"
  factor_columns:
    - "alpha158_KMID"
```

实现约束：

- 先用 V4 原有 `load_window_frame()` 生成基础字段、labels、data_quality 和 tradability。
- 再按 `datetime, instrument` merge 外部 Alpha158 frame。
- factor specs 从 catalog 动态转换，避免手工维护 20 条 Python 常量。
- 若 catalog 缺因子、frame 缺列或 merge 后全为空，运行直接失败。

## 6. First20 Smoke Result

首批 20 个因子 V4 运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_v4.py --config configs\factor_evaluation_v4_alpha158_first20.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_factor_evaluation_context.py --output-dir outputs\factor_evaluation_v4\alpha158_first20_smoke
E:\anaconda_envs\qlib_env\python.exe scripts\summarize_alpha158_first20.py
```

结果摘要：

```text
Alphalens Reloaded: pass 20
jqfactor_analyzer: partial_pass 20
Qlib eval: pass 20
context: pass 240, skipped_non_informative 80
open_source_metric_index rows: 360
context_metric_index rows: 3840
combined metric index rows: 4200
```

`jqfactor_analyzer` 的 `factor_returns` 与 `factor_alpha_beta` 在当前 pandas 2.x 环境下继续记录为已知 partial，不修改开源实现、不作为本阶段阻塞项。

## 7. Batch Runner

批量运行配置：

```text
configs/factor_evaluation_batch_v1_alpha158_first20.yaml
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_first20.yaml --dry-run
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha158_first20.yaml
```

结果：

```text
batch count: 4
factor count per batch: 5
metric rows per batch: 90
context metric rows per batch: 960
```

本轮真实运行中发生过一次电脑断电。恢复后 batch runner 正确识别 batch_001 到 batch_003 已完整产出并跳过，只补跑 batch_004。最终四个 batch 均有完整 evaluator status、metric index 和 context metric index。

## 8. Catalog Promotion

晋升命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha158_catalog_entries_v1.py
```

输出：

```text
outputs/factor_catalog_alpha158_v1/alpha158_catalog_first20_runnable.yaml
```

晋升条件：

- expression frame validation 通过。
- V4 evaluator 中 Alphalens 和 Qlib eval 全部 pass。
- jqfactor 只允许已知 partial，不允许 adapter/缺列/空数据错误。
- context evaluator 无 failed。

晋升后的条目标记为：

```yaml
enabled: true
runnable: true
compute_adapter: qlib_expression_frame_v1
stage: alpha158_first20_v4_smoke_passed
```

## 9. 结论与下一步

本阶段说明：Alpha158 首批 20 个因子已经能通过 Qlib 原始表达式计算，并进入本项目的 V4 开源评价、context 分组评价和 batch runner 断点续跑流程。

这还不代表这些因子可用于实盘或模型训练。下一步更合理的方向是：

- 将同样流程扩展到 Alpha158 全量 158 个因子。
- 在扩容前保留 expression validation 和 runnable promotion 门槛。
- 继续让 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和 context 结果并列共存。
- 等全量因子池有足够候选后，再进入筛选 judgement layer 和组合回测接口。
