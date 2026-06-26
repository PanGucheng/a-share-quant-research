# TA Batch Evaluation Plan V1

V3.19 已经证明 `ta` adapter 可以接入 Qlib 数据、现有 data_quality/tradability 前置过滤和 V4 开源评价体系。V3.20 的目标不是马上把 79 个 TA 因子一次性跑完，而是为剩余 eligible 因子建立可恢复 batch 计划。

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
