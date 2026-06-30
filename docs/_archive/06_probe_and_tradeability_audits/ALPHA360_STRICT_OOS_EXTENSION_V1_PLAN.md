# Alpha360 Strict OOS Extension V1 Plan

本阶段接在 `new_source_probe_review_v1` 之后，只处理 3 个严格 OOS extension candidates：

```text
alpha360_HIGH36
alpha360_HIGH37
alpha360_HIGH40
```

这些因子来自 Qlib `Alpha360DL.get_feature_config`，已经通过 Alpha360 batch promotion 和 new-source probe review。它们仍然只是研究候选，不是模型输入。

## 目标

1. 复用现有 Alpha360 expression adapter，不重写因子公式。
2. 在 2024-01-01 至 2026-06-09 recent OOS 窗口生成 3 因子的 factor frame。
3. 复用现有 Factor Evaluation V4 batch runner，产出 Alphalens Reloaded、jqfactor_analyzer 和 Qlib eval 指标。
4. 输出可复现 contract，为后续稳定性诊断和暴露数据能力审计提供输入。

## 输入

```text
outputs/new_source_probe_review_v1/current/oos_extension_candidates.csv
outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml
outputs/factor_catalog_alpha360_v1/alpha360_formula_inventory.csv
outputs/tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09
outputs/data_quality_tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09
```

## 新增配置

```text
configs/alpha360_expression_adapter_strict_oos_recent_v1.yaml
configs/alpha360_factor_evaluation_strict_oos_recent_base_v1.yaml
configs/factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
```

## 运行命令

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_strict_oos_recent_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
```

## 输出

```text
outputs/alpha360_expression_frame_v1/strict_oos_recent_2024_2026/expression_frame_summary.csv
outputs/alpha360_expression_frame_v1/strict_oos_recent_2024_2026/expression_frame_report.md
outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/batch_manifest.csv
outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/batch_output_summary.csv
outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/open_source_metric_index.csv
```

## Contract

最小 contract：

1. recent OOS factor frame 至少包含 3 个候选因子。
2. 每个候选 coverage 不低于 0.95。
3. V4 batch 至少有 1 个 batch 完成。
4. `open_source_metric_index.csv` 至少有 54 行，覆盖 3 factors * 2 labels * 3 evaluator families 的主要指标。
5. 结果只作为 strict-OOS 诊断，不自动进入训练。

## 下一步

完成后再做：

1. main vs recent OOS 指标稳定性对比。
2. 19 个 tradability exposure watchlist 的流动性/可交易性暴露归因。
3. FactorTest-style 行业/风格/Barra 暴露数据能力审计。
