# New-Source Probe Review V1 Plan

本阶段消费 `new_source_probe_diagnostics_v1` 的输出，做第一轮人工可读的复核分层。它不重新计算因子，不训练模型，不改变任何开源 evaluator 定义。

## 目标

1. 把高相关 probes 聚成冗余簇。
2. 在每个冗余簇中选一个代表因子，其他因子标记为 `redundant_holdout_candidate`。
3. 把与 liquidity / tradability 代理高度相关的 probes 标记为 `tradability_exposure_review`。
4. 输出可以进入更长 OOS / 暴露数据能力审计的候选列表。

## 输入

```text
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostic_board.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_correlation_top_pairs.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_tradability_exposure.csv
```

## 规则

```text
high_abs_corr: 0.95
high_abs_tradability_exposure: 0.30
```

代表因子排序优先级：

1. `strong_signal_probe` 优先。
2. portfolio smoke selected 优先。
3. `max_abs_mean_ic` 更高优先。
4. `max_abs_qlib_ir` 更高优先。
5. `direction_agreement_ratio` 更高优先。
6. tradability exposure 高的降权。

## 输出

```text
outputs/new_source_probe_review_v1/current/probe_review_board.csv
outputs/new_source_probe_review_v1/current/redundancy_pairs.csv
outputs/new_source_probe_review_v1/current/redundancy_groups.csv
outputs/new_source_probe_review_v1/current/tradability_exposure_watchlist.csv
outputs/new_source_probe_review_v1/current/oos_extension_candidates.csv
outputs/new_source_probe_review_v1/current/probe_review_contract_status.csv
outputs/new_source_probe_review_v1/current/probe_review_report.md
```

## 边界

- review action 只是研究分层，不是投资建议。
- `oos_extension_candidate` 只是进入更长窗口和暴露诊断的候选，不是训练输入。
- 任何 new-source probe 仍不得自动成为 downstream default。
