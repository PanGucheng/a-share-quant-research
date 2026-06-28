# Tradability Exposure Attribution V1 Plan

本阶段承接 `new_source_probe_review_v1` 的 19 个 `tradability_exposure_review` probes，做第一层流动性/可交易性暴露归因。

## 目标

1. 复用 `new_source_probe_diagnostics_v1` 与 `new_source_probe_review_v1` 输出，不重新计算因子。
2. 为每个 watchlist probe 标记主暴露代理、暴露方向、暴露强度和冗余叠加状态。
3. 输出训练前的处理建议：holdout、残差化候选、或继续人工复核。
4. 继续保持“不训练模型、不调策略、不改评价体系”的边界。

## 输入

```text
outputs/new_source_probe_review_v1/current/probe_review_board.csv
outputs/new_source_probe_review_v1/current/tradability_exposure_watchlist.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_tradability_exposure.csv
```

## 规则

```text
strong_abs_exposure: 0.65
material_abs_exposure: 0.45
moderate_abs_exposure: 0.30
strong_bucket_z_gap: 0.80
```

归因优先级：

1. 取 `liquidity_value`、`liquidity_bucket`、`tradability_score` 三个代理中绝对相关最高者为 `primary_exposure_proxy`。
2. 同时记录高低流动性 z-score 差异，判断是否像流动性分层暴露。
3. 如果同时高冗余，则标记 `redundancy_compounded=true`。
4. 输出建议动作不等于投资结论，只是后续研究过滤/残差化建议。

## 输出

```text
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_board.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_source_summary.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_action_summary.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_contract_status.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_report.md
```

## 下一步

完成后再推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计，并考虑为高暴露 probes 增加 residualized factor evaluation。
