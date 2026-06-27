# Alpha101 Batch Promotion V1

本文档记录 KunQuant Alpha101 从 5 因子 smoke 扩展到 82 个已审计公式的批量评价结果。本阶段仍然只做因子研究工具链，不训练模型、不调整策略、不改开源评价口径。

## 输入

```text
outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml
outputs/alpha101_factor_adapter_v1/smoke/alpha101_factor_catalog_smoke_passed.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_inventory.csv
outputs/factor_evaluation_batch_v1/alpha101_candidate71_batch1
```

## 运行

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\prepare_alpha101_batch_catalogs_v1.py --config configs\alpha101_factor_batch_catalogs_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha101_factor_adapter_smoke_v1.py --config configs\alpha101_factor_adapter_batch82_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha101_candidate71.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\promote_alpha101_batch_catalog_entries_v1.py --config configs\alpha101_factor_batch_promotion_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_multi_source_screening_v1.py --config configs\multi_source_screening_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 结果

```text
metadata formulas: 82
batch factor frame: 82 factors, 500 instruments, 89,000 rows
adapter eligible: 76
adapter zero-valid holdout: 6
smoke promoted: 5
V4 batch candidates: 71
V4 batch promoted: 59
V4 batch holdout: 12
combined promoted Alpha101 catalog: 64
combined holdout Alpha101 catalog: 18
```

## 关键输出

```text
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_batch_candidate71.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_adapter_holdout6.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_batch_passed59.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_v4_holdout12.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_promoted64.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_holdout18.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_batch_promotion_audit.csv
outputs/factor_evaluation_batch_v1/alpha101_candidate71_batch1/alpha101_candidate71_metric_index.csv
```

## 重要修正

- 部分 KunQuant pandas reference 公式返回时会丢失股票代码列名，adapter 已在形状一致时重贴 Qlib 的 date/instrument 标签。
- `run_factor_evaluation_batch_v1.py` 现在使用 catalog `name` 作为项目内唯一因子 ID，避免不同来源的 `alpha001` 等原始名称互相撞。
- 6 个 `zero_valid_rows` 因子不送入 V4，直接进入 adapter holdout。
- Alphalens / jqfactor turnover 无数值或 not_run 的因子进入 holdout；JQFactor 已知 `factor_returns` / `factor_alpha_beta` index-name partial 不单独阻塞 promotion。

## Multi-Source 影响

```text
multi-source screening rows: 319
new-source strict rows: 141
Alpha101 strict rows: 64
Alpha101 holdout rows: 18
factor research readiness: ready
total runnable factors: 311
new-source runnable factors: 141
```

Alpha101 promoted 因子在 screening contract 中仍保守放入 `monitor`，不直接作为 alpha 信号。V3.26 已在 multi-source 输出上新增通用 judgement 层，其中 14 个 Alpha101 因子进入 `new_source_alpha_probe` 研究队列。
