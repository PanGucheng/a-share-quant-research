# New-Source Probe Diagnostics V1

本阶段承接 multi-source judgement 输出的 328 个 `new_source_alpha_probe`，补齐进入训练前的第一层诊断工具。它不是策略优化，不训练模型，不修改 Alphalens Reloaded / jqfactor_analyzer / Qlib eval 的评价定义。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_new_source_probe_diagnostics_v1.py --config configs\new_source_probe_diagnostics_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 输入

```text
outputs/multi_source_judgement_v1/current/multi_source_new_source_alpha_probes.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv
outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl
outputs/alpha101_factor_adapter_v1/batch82/factor_frame.pkl
outputs/alpha360_expression_frame_v1/batch358/factor_frame.pkl
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
```

## 选择策略

```text
all probes: 328
frame diagnostics selected: 120
portfolio smoke selected: 50
correlation dates: 60
exposure dates: 60
portfolio smoke TopK: 50
portfolio smoke rebalance_every: 20
portfolio smoke cost_bps: 10
```

排序优先级为 `strong_signal_probe`、`consistent_signal_probe`、`max_abs_mean_ic`、`max_abs_qlib_ir`、`direction_agreement_ratio`。V1 只做受控 smoke，不把通过 smoke 的因子自动升级为默认组合或模型输入。

## Contract

```text
probe_count: pass, probes=328
frame_selection_count: pass, selected=120
portfolio_selection_count: pass, selected=50
correlation_pairs: pass, pairs=200
portfolio_smoke_executed: pass, executed_rebalances=4
new_source_not_downstream_default: pass, downstream_default=0
```

`factor_research_toolchain_readiness_v1` 已新增 `new_source_probe_diagnostics` 检查：

```text
new_source_probe_diagnostics: pass
contracts: 8
failed: 0
```

## 关键结果

诊断标签分布：

```text
alpha101 metric_only_probe: 6
alpha101 redundancy_watch: 3
alpha101 tradability_exposure_watch: 5
alpha360 frame_diagnostic_probe: 1
alpha360 metric_only_probe: 199
alpha360 portfolio_smoke_probe: 39
alpha360 redundancy_watch: 60
ta frame_diagnostic_probe: 1
ta metric_only_probe: 3
ta portfolio_smoke_probe: 11
```

Portfolio smoke 结果：

```text
executed_rebalances: 4
trading_days: 80
topk: 50
average_turnover: 0.49
net_excess_ir: 2.752063
net_annualized_excess: 0.161770
```

该 portfolio smoke 只说明接口、可交易性过滤和低频组合管道可以跑通，不应视为可交易策略结论。当前 factor frame 只覆盖 2021 H1 的有效调仓窗口，后续需要更长窗口 OOS 验证。

相关性诊断暴露出高冗余：

```text
ta_trend_sma_fast vs ta_volatility_kcc: abs corr 0.999893
kunquant_alpha101_alpha041 vs kunquant_alpha101_alpha005: abs corr 0.999856
ta_volatility_kcc vs ta_trend_ema_fast: abs corr 0.999811
```

可交易性暴露代理诊断显示部分 TA / Alpha101 因子与 liquidity/tradability 代理高度相关，应先作为风险暴露或冗余候选复核：

```text
kunquant_alpha101_alpha083 max_abs_tradability_exposure: 0.784104
ta_volatility_atr max_abs_tradability_exposure: 0.721224
kunquant_alpha101_alpha042 max_abs_tradability_exposure: 0.657406
```

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
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_contract_status.csv
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostics_report.md
```

## 下一步

1. 先复核 `redundancy_watch` 与 `tradability_exposure_watch`，避免把同质价格/流动性暴露误当成多样 alpha。
2. 参考 FactorTest / jqfactor_analyzer 的行业、风格、Barra 暴露组织方式，做数据能力审计。
3. 扩展 Alpha360 / TA / Alpha101 factor frame 到 recent OOS，再跑稳定性和 portfolio smoke。
4. 保持边界：不训练模型，不改策略，不把 probes 自动设为 downstream default。
