# Alpha158 Recent OOS Extension V1

本文档是 V3.16 的具体计划与执行记录。它承接 V3.15 portfolio diagnostics，目标是把 Alpha158 候选因子的 expression frame 延展到 recent OOS 窗口，并复用既有 portfolio smoke/diagnostics 检查 2024-2026 表现是否稳定。

本阶段仍然不做策略优化、不新增因子、不训练模型。

## 1. 目标

建立如下链路：

```text
alpha158_alpha_candidates.csv
  -> candidate-only Alpha158 expression frame, 2024-2026
  -> candidate expression validation
  -> recent OOS portfolio smoke
  -> recent OOS portfolio diagnostics
```

## 2. 输入

```text
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/factor_catalog_alpha158_v1/alpha158_catalog_all.yaml
outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv
outputs/tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09/
```

## 3. 输出

候选 recent OOS expression frame：

```text
outputs/alpha158_expression_frame_v1/candidates_recent_oos_2024_2026/
  expression_table.csv
  expression_frame_summary.csv
  expression_frame_sample.csv
  expression_frame_manifest.json
  expression_frame_report.md
  candidate_expression_validation_report.md
  candidate_expression_validation_status.csv
  candidate_expression_validation_coverage.csv
```

说明：大体积 `factor_frame*.pkl` 继续由 `.gitignore` 排除，只保留 manifest、summary、sample 和验证报告。

recent OOS portfolio smoke：

```text
outputs/alpha158_candidate_portfolio_smoke_v1/recent_oos_2024_2026/
```

recent OOS portfolio diagnostics：

```text
outputs/alpha158_portfolio_diagnostics_v1/recent_oos_2024_2026/
```

## 4. 实现文件

```text
configs/alpha158_expression_adapter_candidates_recent_oos_v1.yaml
configs/alpha158_candidate_portfolio_smoke_recent_oos_v1.yaml
configs/alpha158_portfolio_diagnostics_recent_oos_v1.yaml
scripts/validate_alpha158_candidate_expression_frame_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\build_alpha158_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\validate_alpha158_candidate_expression_frame_v1.py --config configs\alpha158_expression_adapter_candidates_recent_oos_v1.yaml --candidate-pool outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_recent_oos_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_recent_oos_v1.yaml
```

## 5. 验收标准

- [x] expression frame 只包含 14 个 `alpha_candidate`。
- [x] `datetime, instrument` 无重复。
- [x] 14 个候选列都在 expression frame 中。
- [x] 每个候选因子覆盖率不低于 0.99。
- [x] recent OOS 输出不提交大体积 pickle。
- [x] recent OOS portfolio smoke 跑通。
- [x] recent OOS portfolio diagnostics 跑通。
- [x] README 和总计划文档记录当前状态。

## 6. 当前结果

Expression frame：

```text
rows: 1,096,231
candidate factors: 14
date range: 2024-01-02 to 2026-06-09
min factor coverage: 0.995898
validation: pass
```

Portfolio smoke：

```text
trading_days: 560
executed_rebalances: 28
net_annualized_excess: 0.019804
net_excess_ir: 0.221295
average_turnover: 0.799286
net_max_drawdown: -0.153772
```

recent OOS 单因子 `net_excess_ir` 排名前三：

```text
alpha158_VSUMN60    0.814553
alpha158_ROC60      0.462744
alpha158_ROC30      0.315209
```

TopK 敏感性：

```text
topk_50:  net_excess_ir 0.081597
topk_100: net_excess_ir 0.221295
topk_200: net_excess_ir -0.113919
```

成本敏感性：

```text
cost_5bps:  net_excess_ir 0.262459
cost_10bps: net_excess_ir 0.221295
cost_20bps: net_excess_ir 0.138893
```

## 7. 结论与下一步

与 main window 相比，recent OOS 结果明显降温：

```text
main topk_100 net_excess_ir:       0.552843
recent OOS topk_100 net_excess_ir: 0.221295
```

候选内部排序也发生变化：main window 最强单因子是 `alpha158_ROC30`，recent OOS 最强单因子变为 `alpha158_VSUMN60`。这说明当前候选池还不能直接进入策略优化。

下一步建议进入：

```text
V3.17 Alpha158 Stability And Exposure Diagnostics
```

重点：

- main vs recent OOS 单因子排名稳定性。
- 候选组合暴露到流动性、价格动量、波动率和成交量代理的程度。
- 针对高换手候选设计低换手诊断，而不是直接调参。
