# TA Batch Evaluation Plan V1

V3.19 已经证明 `ta` adapter 可以接入 Qlib 数据、现有 data_quality/tradability 前置过滤和 V4 开源评价体系。V3.20 先为剩余 eligible 因子建立可恢复 batch 计划；V3.21 已完成真实 batch 执行和 promotion。

## 1. 输入

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke_passed.yaml
outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl
```

当前状态：

```text
eligible TA factors: 79
smoke-passed factors: 5
remaining pending factors: 74
```

## 2. 新增配置

```text
configs/ta_factor_batch_catalogs_v1.yaml
configs/ta_factor_evaluation_batch_base_v1.yaml
configs/factor_evaluation_batch_v1_ta_remaining74.yaml
```

## 3. 生成 batch catalogs

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_ta_batch_catalogs_v1.py --config configs\ta_factor_batch_catalogs_v1.yaml
```

输出：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_remaining74.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_combined79.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_catalog_audit.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_catalog_report.md
```

## 4. Dry-run

先只生成 manifest 和 batch configs：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --dry-run
```

预期输出：

```text
outputs/factor_evaluation_batch_v1/ta_remaining74_smoke/batch_manifest.csv
outputs/factor_evaluation_batch_v1/ta_remaining74_smoke/generated_configs/batch_*.yaml
outputs/factor_evaluation_batch_v1/ta_remaining74_smoke/factor_evaluation_batch_v1_report.md
```

## 5. 执行策略

TA V4 smoke 中 5 个因子耗时较长，因此后续执行必须用 batch/resume：

1. 先 `--dry-run`。
2. 再 `--max-batches 1` 做真实小批验证。
3. 若通过，再分段提高 `--max-batches`。
4. 每批完成后汇总 metric index 和 failure reasons。
5. 达到至少 20 个新源 promoted runnable 后，重新运行 readiness gate。

边界：

- 不一次性全量硬跑。
- 不把未通过 V4 的 TA 因子标成 runnable。
- 不改变开源评价口径。
- 不训练模型。

## 6. 实际执行结果

真实 batch 使用同一份剩余 74 因子配置执行：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_ta_remaining74.yaml --max-batches 15 --output-root outputs\factor_evaluation_batch_v1\ta_remaining74_batch1
```

输出：

```text
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/batch_manifest.csv
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/batch_output_summary.csv
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/factor_evaluation_batch_v1_report.md
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/ta_remaining74_metric_index.csv
```

结果：

```text
selected factors: 74
batch count: 15
Qlib eval: 74 pass
Alphalens Reloaded: 72 pass, 2 partial_pass
jqfactor_analyzer: 74 partial_pass
```

jqfactor_analyzer 的 partial 仍是已知 pandas MultiIndex 兼容问题，失败项为 `factor_returns` 和 `factor_alpha_beta`，暂不改开源评价口径。

## 7. Promotion

promotion 使用明确白名单：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_batch_catalog_entries_v1.py --config configs\ta_factor_batch_promotion_v1.yaml
```

新增输出：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_batch_passed72.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_holdout2.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_audit.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_report.md
```

promotion 结果：

```text
smoke promoted: 5
batch promoted: 72
batch holdout: 2
combined promoted: 77
```

holdout 因子：

```text
ta_volatility_bbli
ta_volatility_kchi
```

原因：这两个因子在 Alphalens Reloaded 的 `quantile_turnover` 步骤没有产生数值。它们通过了 Qlib eval，但在统一筛选工具链里应保留为 holdout，而不是进入 promoted runnable catalog。

## 8. 后续衔接

TA promoted77 已经让 readiness 的 `new_source_adapter_inventory` 通过。下一步不是继续单独研究这些常见技术指标，而是把 Alpha158 与 TA 的评价结果接入通用多来源 screening/candidate-pool contract。该 contract 通过后，才适合继续接 Alpha101、更多公式库、基本面数据和行业风格暴露。
