# Alpha360 Strict OOS Stability V1

本阶段比较 3 个 strict candidates 的主窗口指标与 recent-OOS 指标稳定性：

```text
alpha360_HIGH36
alpha360_HIGH37
alpha360_HIGH40
```

它只做稳定性诊断，不训练模型，不调整策略，不改变开源评价体系。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha360_strict_oos_stability_v1.py --config configs\alpha360_strict_oos_stability_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 结果

```text
metric pairs: 54
summary rows: 3
recent Alphalens mean IC min: 0.063736
recent Qlib information ratio min: 5.025121
signal sign flips: 0
all sign flips: 3 beta-only flips
strict OOS stability contract rows: 8 pass
```

## 关键指标

| factor | main 10D IC | recent 10D IC | main 20D IC | recent 20D IC | 10D IC retention | 20D IC retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alpha360_HIGH36 | 0.067448 | 0.063736 | 0.077548 | 0.072231 | 0.944977 | 0.931441 |
| alpha360_HIGH37 | 0.068568 | 0.065477 | 0.078303 | 0.073073 | 0.954925 | 0.933205 |
| alpha360_HIGH40 | 0.073413 | 0.065851 | 0.082376 | 0.072314 | 0.896994 | 0.877854 |

Qlib IR 仍为正但 recent-OOS 变弱：

| factor | recent 10D IR | recent 20D IR |
| --- | ---: | ---: |
| alpha360_HIGH36 | 5.025121 | 6.289686 |
| alpha360_HIGH37 | 5.153590 | 6.354661 |
| alpha360_HIGH40 | 5.157218 | 6.298794 |

## 解释

- 3 个因子的 Alphalens mean IC 在 recent-OOS 中仍为正，且主窗口到 recent-OOS 的 IC 保留率较高。
- Qlib information ratio 仍为正，但相对主窗口下降，标记为 `positive_but_weaker`。
- 3 个 sign flip 全部来自 Alphalens beta 的 10D 指标，recent beta 接近 0，不作为信号指标阻断。
- 这些因子仍然是研究候选，不是训练输入。

## 输出

```text
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_metrics.csv
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_summary.csv
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_contract_status.csv
outputs/alpha360_strict_oos_stability_v1/current/alpha360_strict_oos_stability_report.md
```

## 下一步

1. 对 19 个 `tradability_exposure_review` probes 做流动性/可交易性暴露归因。
2. 推进 FactorTest-style 行业/风格/Barra 暴露数据能力审计。
