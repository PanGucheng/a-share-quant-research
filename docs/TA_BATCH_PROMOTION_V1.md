# TA Batch Promotion V1

本文档记录 `bukosabino/ta` 因子源在完成 adapter smoke 与剩余 74 个 eligible 因子 V4 batch 后的晋级规则。它的目的不是评价 TA 因子好坏，而是确认“新来源因子能否安全进入后续多来源筛选工具链”。

## 输入

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_remaining74.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_smoke_passed.yaml
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/
```

## 配置与脚本

```text
configs/ta_factor_batch_promotion_v1.yaml
scripts/promote_ta_batch_catalog_entries_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\promote_ta_batch_catalog_entries_v1.py --config configs\ta_factor_batch_promotion_v1.yaml
```

## 晋级规则

晋级为 promoted runnable 的因子必须满足：

- Alphalens Reloaded 为 `pass`。
- Qlib eval 为 `pass`。
- jqfactor_analyzer 只允许已知的 `factor_returns` 与 `factor_alpha_beta` partial。

进入 holdout 的因子不会被删除，但不能进入 promoted runnable catalog。当前 holdout 白名单仅包含 Alphalens Reloaded `quantile_turnover` 无数值的情况。

## 结果

```text
source factors: 74
batch promoted: 72
batch holdout: 2
combined promoted: 77
```

输出：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_batch_passed72.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_holdout2.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_audit.csv
outputs/ta_factor_adapter_v1/smoke/ta_factor_batch_promotion_report.md
outputs/factor_evaluation_batch_v1/ta_remaining74_batch1/ta_remaining74_metric_index.csv
```

Holdout 因子：

```text
ta_volatility_bbli
ta_volatility_kchi
```

## 后续用途

`ta_factor_catalog_promoted77.yaml` 是后续通用多来源筛选工具链的 TA 输入。大规模扩张因子池时，新的来源也应沿用同样路径：

```text
source manifest -> adapter audit -> V4 batch -> promotion/holdout -> generic screening -> candidate pool
```
