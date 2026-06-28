# Alpha360 Strict OOS Extension V1

本阶段承接 `new_source_probe_review_v1`，只对 3 个 strict OOS extension candidates 做 recent-OOS 复核：

```text
alpha360_HIGH36
alpha360_HIGH37
alpha360_HIGH40
```

它复用 Qlib Alpha360 expression adapter 和 Factor Evaluation V4 batch runner，不训练模型，不调整策略，不改评价体系定义。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha360_expression_frame_v1.py --config configs\alpha360_expression_adapter_strict_oos_recent_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_evaluation_batch_v1.py --config configs\factor_evaluation_batch_v1_alpha360_strict_oos_recent.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_extension_v1.py --config configs\alpha360_strict_oos_extension_audit_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 结果

```text
recent OOS factor frame rows: 286,944
candidate factors: 3
min coverage: 0.996236
V4 batches: 1 pass
metric index rows: 54
strict OOS contract rows: 8 pass
alpha360_strict_oos_extension: pass
readiness overall_status: ready
```

## Recent OOS Metrics

| factor | alphalens 10D mean IC | alphalens 20D mean IC | qlib 10D IR | qlib 20D IR |
| --- | ---: | ---: | ---: | ---: |
| alpha360_HIGH36 | 0.063736 | 0.072231 | 5.025121 | 6.289686 |
| alpha360_HIGH37 | 0.065477 | 0.073073 | 5.153590 | 6.354661 |
| alpha360_HIGH40 | 0.065851 | 0.072314 | 5.157218 | 6.298794 |

这些指标说明 3 个因子在 recent OOS 窗口仍可被现有多评价体系正常消费，并且 Rank IC 方向仍为正。它们仍然只是研究候选，不是训练输入或策略结论。

## Evaluator Status

```text
alphalens_reloaded: pass for 3 factors
qlib_eval: pass for 3 factors
jqfactor_analyzer: partial_pass for 3 factors
```

`jqfactor_analyzer` 的 partial pass 仍是已知的 `factor_returns` / `factor_alpha_beta` index-name 问题；`mean_information_coefficient` 正常输出，contract 中仅允许这个已知 partial。

## 输出

```text
outputs/alpha360_expression_frame_v1/strict_oos_recent_2024_2026/expression_frame_summary.csv
outputs/alpha360_expression_frame_v1/strict_oos_recent_2024_2026/expression_frame_report.md
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_expression_summary.csv
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_metric_summary.csv
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_evaluator_status.csv
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_contract_status.csv
outputs/alpha360_strict_oos_extension_v1/current/alpha360_strict_oos_extension_report.md
```

## 下一步

1. main vs recent OOS 稳定性对比已在 `docs/ALPHA360_STRICT_OOS_STABILITY_V1.md` 完成。
2. 对 19 个 `tradability_exposure_review` probes 做流动性/可交易性暴露归因。
3. 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
