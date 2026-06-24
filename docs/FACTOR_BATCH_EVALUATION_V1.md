# Factor Batch Evaluation V1

本文档记录因子研究下一阶段的工程接口。目标是在不替换现有 Qlib baseline、不修改开源评价口径、不训练新模型的前提下，为后续大规模扩张因子池提供可恢复、可追溯、可分批运行的工具链。

## 1. 定位

现有 `scripts/run_factor_evaluation_v4.py` 已经能把同一批因子送入 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 和本项目当前评价体系，并且接入了 point-in-time context。

V1 batch layer 只做三件事：

1. 从因子目录中选择可运行因子。
2. 生成每个 batch 的独立 V4 配置。
3. 记录 manifest、日志、输出摘要和失败批次，便于断点续跑。

它不做以下事情：

- 不实现新的 IC、分组收益或换手率算法。
- 不把多个开源评价体系合并成单一分数。
- 不绕过 `data_quality` 和 `tradability`。
- 不直接接入实盘或模型训练。

## 2. 新增文件

```text
factor_research/factor_catalog.yaml
factor_research/catalog.py
configs/factor_evaluation_batch_v1.yaml
configs/factor_evaluation_batch_v1_smoke.yaml
scripts/run_factor_evaluation_batch_v1.py
```

## 3. 因子目录

`factor_research/factor_catalog.yaml` 是后续扩张因子池的统一入口。每个可运行因子至少记录：

```text
name
category
source_project
source_file
source_function
source_commit
license
expected_direction
required_fields
labels
stage
enabled
runnable
compute_adapter
registry_name
notes
```

当前可运行因子仍来自本项目 `factor_research/factor_library.py::add_basic_factors`，因为这些因子已经接入现有 registry 和 V4 评价流程。

同时，目录中登记了后续扩池来源：

| source | role | current status |
| --- | --- | --- |
| Qlib Alpha158 | Qlib 官方因子族 | adapter pending |
| qlib_factor_platform presets | 因子组织方式与命名参考 | design reference |
| ta | 技术指标扩张来源 | adapter pending |
| KunQuant Alpha101 | Alpha101 公式参考 | adapter pending |
| Ginkgo Alpha101 | Alpha101 公式交叉参考 | adapter pending |

这些来源暂不自动运行，避免把未审计的公式、字段口径或依赖假设直接放进筛选主线。

## 4. 批量运行流程

默认配置：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1.yaml
```

默认选择 `stage = current_v4_seed` 的 5 个已验证种子因子，并按 2 个因子一个 batch 调用 V4：

```text
rev_5
rev_20_exclude_5
std_20
downside_std_20
amount_mean_20
```

每个 batch 会生成：

```text
outputs/factor_evaluation_batch_v1/<run>/
  factor_catalog_snapshot.csv
  selected_factor_catalog.csv
  factor_catalog_validation.csv
  generated_configs/batch_001.yaml
  batch_manifest.csv
  batch_output_summary.csv
  factor_evaluation_batch_v1_report.md
  logs/batch_001.stdout.log
  logs/batch_001.stderr.log
  runs/batch_001/
```

`runs/batch_*/` 内部仍然是原始 V4 输出结构。

## 5. 断点续跑

配置中默认：

```yaml
batching:
  resume: true
```

如果某个 batch 已经存在以下文件，runner 会跳过该批次：

```text
evaluator_status.csv
open_source_metric_index.csv
factor_evaluation_v4_report.md
```

这能避免后续扩展到几十或几百个因子时，因为单个因子失败或中断而重跑全部任务。

## 6. 快速验证

只验证批量编排，不执行耗时评价：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_smoke.yaml --dry-run
```

该命令只会生成：

```text
outputs/factor_evaluation_batch_v1/smoke_dry_run/
```

它用于确认：

- 因子目录能被加载。
- 选择器能筛出目标因子。
- registry 对齐检查通过。
- 每个 batch 的 V4 配置能正确生成。
- manifest 和 report 能落盘。

## 7. 后续扩展目标

下一阶段应继续保持“开源优先、先登记后运行”的节奏：

1. 为 Qlib Alpha158 增加表达式读取和字段审计。
2. 将 Alpha158 候选拆成可运行 catalog entries。
3. 为 `ta` 增加 OHLCV DataFrame 适配器，先小批量验证技术指标。
4. 将 Alpha101 公式作为第三批扩张来源，先做字段、窗口和 look-ahead 审计。
5. 每次扩张都先跑 `--dry-run`，再跑少量 smoke batch，最后进入完整批量评估。

大规模因子池可以开始扩张，但前提是每个来源都有清楚的 license、字段依赖、计算适配和失败记录。
