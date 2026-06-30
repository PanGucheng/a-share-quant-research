# Tradability Exposure Attribution V1

本阶段对 `new_source_probe_review_v1` 标记的 19 个 `tradability_exposure_review` probes 做流动性/可交易性暴露归因。

它复用 `new_source_probe_diagnostics_v1` 已经计算好的因子 frame + tradability labels 暴露结果，不重新训练模型，不调整策略。

## 运行命令

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_tradability_exposure_attribution_v1.py --config configs\tradability_exposure_attribution_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\audit_factor_research_toolchain_v1.py --config configs\factor_research_toolchain_readiness_v1.yaml
```

## 结果

```text
watchlist rows: 19
attribution rows: 19
source families: 2
primary proxy present: 19/19
diagnostic exposure rows: 120
downstream default: 0
contract rows: 6 pass
```

## 行动汇总

| recommended_action | exposure_strength | factor_count |
| --- | --- | ---: |
| holdout_before_residualization | strong | 6 |
| holdout_redundant_liquidity_proxy | material | 7 |
| holdout_redundant_liquidity_proxy | strong | 1 |
| manual_review_before_training | moderate | 4 |
| residualization_candidate_review | material | 1 |

## 来源汇总

```text
alpha101: 8
ta: 11
```

全部 19 个 watchlist probes 的主暴露代理都是 `liquidity_value`。TA 因子主要是正向流动性暴露，Alpha101 因子大多是负向流动性暴露。

## 解释

- 高 tradability exposure 不代表因子无效，但会阻止它直接进入训练输入。
- `holdout_before_residualization` 表示下一步应该先做 residualized / neutralized evaluation，而不是 raw factor training。
- `manual_review_before_training` 表示暴露较低但仍超过 watch 阈值，需要人工复核或残差化实验。

## 输出

```text
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_board.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_source_summary.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_action_summary.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_contract_status.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_report.md
```

## 下一步

1. FactorTest-style 行业/风格/Barra 暴露数据能力审计已在 `docs/EXPOSURE_DATA_CAPABILITY_AUDIT_V1.md` 完成。
2. 后续如要研究这些高暴露因子，应先做 liquidity residualized factor evaluation，或先接外部行业/市值数据。
