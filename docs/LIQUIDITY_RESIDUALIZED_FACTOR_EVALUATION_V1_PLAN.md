# Liquidity Residualized Factor Evaluation V1 Plan

本阶段编号：V3.39。

本阶段承接 `Tradability Exposure Attribution V1` 与 `Exposure Data Capability Audit V1`。当前 provider 缺少市值、行业和 Barra 字段，因此不直接做 FactorTest-style industry/Barra neutralization；先用已经可用的 `tradability_labels.csv` 做 liquidity / tradability residualized factor evaluation 的最小闭环。

## 目标

1. 对 19 个 `tradability_exposure_review` probes 做 liquidity residualization 复核。
2. 判断 raw 因子信号是否主要来自 `liquidity_value` / `liquidity_bucket` / `tradability_score`。
3. 输出 raw vs residualized 的评价对比，不训练模型，不进入策略优化。
4. 为后续行业/市值/Barra 数据接入后的 neutralized evaluation 预留相同接口。

## 边界

- 不替换 Qlib baseline。
- 不训练 LightGBM/XGBoost/CatBoost/深度模型。
- 不做实盘、不生成组合交易建议。
- 不修改 Alphalens Reloaded、jqfactor_analyzer、Qlib eval 的评价定义。
- 不把 residualized 因子自动加入 downstream default。

## 开源参考

本阶段只借鉴模块边界和流程，不复制实现。

```text
FactorTest:
- RegbySize / calcNeuSize
- Regbysize / calcNeuIndsize
- RegbyBarra / calcNeuBarra

qlib_factor_platform:
- neutralize_factor
```

本项目 V3.39 的等价最小能力：

```text
raw factor
  -> attach tradability proxies
  -> daily cross-sectional residualization
  -> residualized factor frame
  -> reuse Factor Evaluation V4
  -> raw vs residualized comparison
```

## 输入

```text
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_attribution_board.csv
outputs/new_source_probe_review_v1/current/probe_review_board.csv
outputs/new_source_probe_diagnostics_v1/current/selected_probe_tradability_exposure.csv
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
outputs/ta_factor_adapter_v1/smoke/factor_frame.pkl
outputs/alpha101_factor_adapter_v1/batch82/factor_frame.pkl
```

首批候选来自 `tradability_exposure_attribution_board.csv`：

```text
holdout_before_residualization
holdout_redundant_liquidity_proxy
manual_review_before_training
residualization_candidate_review
```

## 残差化口径

V1 只做 liquidity/tradability 残差化：

```text
proxies:
- liquidity_value
- liquidity_bucket
- tradability_score
```

每个交易日独立做横截面处理：

1. 对 factor 与 proxy 做 winsorized z-score。
2. 用 OLS 回归：

```text
factor_z = intercept + liquidity_value_z + liquidity_bucket_z + tradability_score_z + residual
```

3. 将 residual 作为新因子列：

```text
<factor>__resid_liquidity
```

4. 记录每天可用样本数、R2、残差 coverage、残差与原因子的相关性。

V1 不做行业哑变量、市值、Barra 暴露，因为 V3.38 已确认当前 provider 不具备这些字段。

## 新增文件规划

```text
configs/liquidity_residualized_factor_evaluation_v1.yaml
factor_research/liquidity_residualization.py
scripts/run_liquidity_residualized_factor_evaluation_v1.py
scripts/audit_liquidity_residualized_factor_evaluation_v1.py
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1.md
```

## 输出规划

```text
outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_factor_frame.pkl
outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_factor_summary.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/daily_residualization_diagnostics.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/raw_vs_residualized_metric_comparison.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_candidate_actions.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv
outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_factor_evaluation_report.md
```

大型 `residualized_factor_frame.pkl` 只作为本地可再生成缓存，不进入 Git；Git 中保留 summary、diagnostics、comparison、contract 和 report。

## V4 评价接入

Residualized factor frame 应复用现有 external factor frame 机制：

```text
scripts/run_factor_evaluation_v4.py
external_factor_frame:
  enabled: true
  path: outputs/liquidity_residualized_factor_evaluation_v1/current/residualized_factor_frame.pkl
```

评价系统继续共存：

```text
alphalens_reloaded
jqfactor_analyzer
qlib_eval
```

如果 `jqfactor_analyzer` 仍出现已知 `factor_returns` / `factor_alpha_beta` partial pass，只记录，不阻断 mean IC / Rank IC / Qlib IR 的比较。

## Contract

最小通过条件：

```text
input_watchlist_rows >= 19
residualized_factor_count >= 19
residualized_coverage_min >= 0.80
daily_diagnostics_rows > 0
raw_vs_residualized_metric_rows > 0
contract_status_rows >= 8
downstream_default_included == 0
```

信号判断不使用单一收益阈值，而使用分层动作：

```text
residual_signal_survives:
  residualized IC/IR 仍为正，且保留率足够高

liquidity_proxy_confirmed:
  raw 有效但 residualized 明显衰减或翻负

needs_manual_review:
  残差覆盖率不足、样本不稳或评价系统输出不足

holdout:
  高暴露且残差后无稳定信号
```

## 决策输出

`residualized_candidate_actions.csv` 应至少包含：

```text
factor
source_family
raw_action
primary_exposure_proxy
raw_mean_ic_10d
raw_mean_ic_20d
residualized_mean_ic_10d
residualized_mean_ic_20d
ic_retention_10d
ic_retention_20d
residualized_coverage
residualization_r2_mean
decision
decision_reason
```

## 实施顺序

1. 实现 residualization 数据准备：读取 watchlist、factor frames、tradability labels。
2. 实现 daily cross-sectional residualization。
3. 生成 residualized factor frame 和 diagnostics。
4. 复用 V4 external factor frame 评价 residualized 因子。
5. 汇总 raw vs residualized 指标。
6. 生成 candidate actions 与 contract。
7. 接入 `factor_research_toolchain_readiness_v1`。
8. 更新 README、中文 README、项目上下文与 Step 5 总计划。

## 风险与处理

| 风险 | 处理 |
| --- | --- |
| residualized 因子覆盖率不足 | contract 阻断，不进入候选动作 |
| liquidity proxy 与 factor 高度共线 | 记录 R2 与 IC retention，优先标记 proxy confirmed |
| TA / Alpha101 factor frame 日期范围不同 | 先按共同日期和 tradability labels inner join |
| V4 评价输出 partial | 仅允许已知 jqfactor partial，其他失败进入 blocked |
| 残差化后偶然保留信号 | 仍保持 research candidate，不进入训练 |

## 完成后的下一步

V3.39 完成后再决定：

1. 对 `residual_signal_survives` 的少量因子做 recent-OOS residualized evaluation。
2. 设计外部行业/市值数据接入 contract。
3. 在行业/市值数据 ready 后，再实现 FactorTest-style industry/size neutralized evaluation。
