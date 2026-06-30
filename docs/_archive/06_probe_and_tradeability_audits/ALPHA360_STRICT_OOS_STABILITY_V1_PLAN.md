# Alpha360 Strict OOS Stability V1 Plan

本阶段承接 `Alpha360 Strict OOS Extension V1`，比较 3 个 strict candidates 在主窗口与 recent-OOS 的评价指标稳定性。

## 目标

1. 复用已生成的 Alpha360 batch main-window metric index。
2. 复用 strict recent-OOS V4 metric index。
3. 对同一 factor/system/metric/horizon 生成 main vs recent 对比。
4. 输出稳定性标签和 contract，继续保持研究诊断边界。

## 输入

```text
outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/alpha360_candidate358_metric_index.csv
outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/open_source_metric_index.csv
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_contract_status.csv
```

## 候选

```text
alpha360_HIGH36
alpha360_HIGH37
alpha360_HIGH40
```

## 输出

```text
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_metrics.csv
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_summary.csv
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_contract_status.csv
outputs/alpha360_strict_oos_stability_v1/current/alpha360_strict_oos_stability_report.md
```

## Contract

1. 3 个 strict candidates 都有 main/recent 指标。
2. main vs recent metric pairs 至少 54 行。
3. Alphalens mean IC 在 recent-OOS 仍为正。
4. Qlib information_ratio 在 recent-OOS 仍为正。
5. IC、alpha、return、IR、mean 等信号指标不出现 main/recent 符号翻转。
6. 结果只做稳定性诊断，不自动进入训练。

## 下一步

完成后进入两个分支：

1. 对 19 个 `tradability_exposure_review` probes 做流动性/可交易性暴露归因。
2. 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
