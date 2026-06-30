# New-Source Probe Diagnostics V1 Plan

本阶段承接 `multi_source_judgement_v1` 的 328 个 `new_source_alpha_probe`。目标是补齐进入训练前的诊断工具层，而不是调整策略、训练模型或修改开源评价口径。

## 背景

当前 multi-source judgement 已经把 TA、Alpha101、Alpha360 promoted 因子分成研究队列：

```text
new-source alpha probes: 328
TA probes: 15
Alpha101 probes: 14
Alpha360 probes: 299
```

这些 probes 只说明它们在现有 Alphalens Reloaded / jqfactor_analyzer / Qlib eval 指标下具备进一步研究价值，不代表可以直接进入模型或组合。

## 目标

V1 做一个最小但可复现的诊断层：

1. 生成 328 个 probes 的统一诊断看板。
2. 对高优先级 probes 做 factor-frame 级别相关性诊断。
3. 复用现有 tradability / liquidity 标签，做可交易性暴露代理诊断。
4. 用 10d/20d 和多 evaluator 指标做 horizon / direction 稳定性诊断。
5. 选取受控数量 probes 做一个低频 TopK portfolio smoke，只验证接口和风险，不作为策略。
6. 输出 contract status，并纳入 readiness 防回退。

## 输入

```text
outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv
outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv
outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl
outputs/alpha101_factor_adapter_v1/batch82/factor_frame.pkl
outputs/alpha360_expression_frame_v1/batch358/factor_frame.pkl
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
```

## 第一版选择策略

- 全量保留 328 个 probes 的 metric / judgement 记录。
- factor-frame 诊断默认最多选 120 个高优先级 probes。
- portfolio smoke 默认最多选 50 个 probes。
- 排序优先级：`strong_signal_probe` 优先于 `consistent_signal_probe`，然后看 `max_abs_mean_ic`、`max_abs_qlib_ir` 和 `direction_agreement_ratio`。
- 新来源 probes 即使通过 portfolio smoke，也只能进入后续研究队列，不能成为 downstream default。

## 输出

```text
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_inventory.csv
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostic_board.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_factor_coverage.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_correlation_summary.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_correlation_top_pairs.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_tradability_exposure.csv
outputs/new_source_probe_diagnostics_v1/current/portfolio_smoke_summary.csv
outputs/new_source_probe_diagnostics_v1/current/portfolio_smoke_weights.csv
outputs/new_source_probe_diagnostics_v1/current/portfolio_smoke_liquidity_exposure.csv
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_contract_status.csv
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_report.md
```

## 边界

- 不改 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 的定义。
- 不绕过 data_quality / tradability。
- 不引入复杂 UI。
- 不训练新模型。
- 不把 new-source probe 自动加入组合或 Qlib baseline。

## 后续

V1 跑通后，再继续参考 FactorTest / jqfactor_analyzer 的行业、风格、Barra 暴露组织方式，做真正的行业/风格数据能力审计。
