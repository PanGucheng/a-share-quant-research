# Alpha360 Batch Catalogs V1

状态：已完成 dry-run。

本阶段目标是把 Alpha360 从 smoke 阶段推进到可恢复 batch V4 阶段的准备状态。这里仍不训练模型、不优化策略、不把 Alpha360 加入 multi-source screening；只是生成 batch candidate、adapter holdout 和 batch runner 计划。

## 1. 输入

```text
source_catalog: outputs/factor_catalog_alpha360_v1/alpha360_catalog_all.yaml
source factors: 360
```

运行命令：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha360_batch_catalogs_v1.py --config configs\alpha360_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_candidate358.yaml --dry-run
```

## 2. 输出

```text
outputs/factor_catalog_alpha360_v1/alpha360_catalog_batch_candidate358.yaml
outputs/factor_catalog_alpha360_v1/alpha360_catalog_adapter_holdout2.yaml
outputs/factor_catalog_alpha360_v1/alpha360_catalog_combined360.yaml
outputs/factor_catalog_alpha360_v1/alpha360_batch_catalog_audit.csv
outputs/factor_catalog_alpha360_v1/alpha360_batch_catalog_report.md

configs/alpha360_expression_adapter_batch358_v1.yaml
configs/alpha360_factor_evaluation_batch_base_v1.yaml
configs/factor_evaluation_batch_v1_alpha360_candidate358.yaml
```

Batch dry-run 输出：

```text
outputs/factor_evaluation_batch_v1/alpha360_candidate358_batch1
```

## 3. Catalog 结果

```text
source_all: 360
batch_candidate: 358
adapter_holdout: 2
combined: 360
```

Holdout 因子：

```text
alpha360_CLOSE0
alpha360_VOLUME0
```

原因：

```text
constant_or_near_constant_normalization_identity
```

## 4. Batch Dry-Run

```text
selected factors: 358
batch size: 5
planned batches: 72
batch_001: alpha360_CLOSE59..alpha360_CLOSE55
batch_072: alpha360_VOLUME3, alpha360_VOLUME2, alpha360_VOLUME1
```

dry-run 只生成计划和 batch configs，不运行 V4。

## 5. Readiness Contract

新增合同：

```text
alpha360_batch_candidate_catalog rows: 358
alpha360_adapter_holdout_catalog rows: 2
alpha360_batch_catalog_audit rows: 4
alpha360_batch_dry_run_manifest rows: 72
alpha360_batch_dry_run_selected_catalog rows: 358
```

## 6. 下一步

1. 运行 `configs/alpha360_expression_adapter_batch358_v1.yaml`，生成 358 因子 batch factor frame。
2. 先执行 `factor_evaluation_batch_v1_alpha360_candidate358.yaml --max-batches 1` 的小批验证。
3. 小批通过后再 resume 执行全部 72 个 batch。
4. 根据 batch V4 结果生成 promoted/holdout catalog，再接入 multi-source screening 和 judgement。
