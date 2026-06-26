# Alpha158 Portfolio Diagnostics V1

本文档是 V3.15 的具体计划与执行记录。它承接 V3.14 portfolio smoke，只做诊断，不调整 candidate pool，不优化策略，不新增因子。

## 1. 目标

V3.14 已经证明：

```text
candidate pool -> score -> tradability-aware low-frequency portfolio -> report
```

V3.15 继续回答四个问题：

1. 14 个候选里，哪些单因子对组合 smoke 贡献较明显。
2. 组合结果对 TopK 是否敏感。
3. 组合结果对交易成本是否敏感。
4. 当前持仓是否明显偏向某些流动性 bucket。

## 2. 输入

```text
configs/alpha158_candidate_portfolio_smoke_v1.yaml
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/alpha158_expression_frame_v1/full158_main_research/
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
```

## 3. 诊断口径

本阶段复用 V3.14 口径：

```text
score_policy: equal_directional_zscore
date_range: 2021-01-01 to 2023-12-29
rebalance_every: 20
base_topk: 100
base_cost_bps: 10
min_liquidity_bucket: 3
min_tradability_score: 75
min_capacity_multiple: 2
```

新增诊断：

```text
single_factor: each alpha candidate independently
topk_sensitivity: 50, 100, 200
cost_sensitivity: 5, 10, 20 bps
liquidity_bucket_exposure: selected positions from base combined scenario
```

## 4. 实现文件

```text
configs/alpha158_portfolio_diagnostics_v1.yaml
factor_research/alpha158_portfolio_diagnostics.py
scripts/run_alpha158_portfolio_diagnostics_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_portfolio_diagnostics_v1.py --config configs\alpha158_portfolio_diagnostics_v1.yaml
```

## 5. 输出

```text
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/
  alpha158_portfolio_diagnostics_report.md
  base_summary.csv
  single_factor_summary.csv
  topk_sensitivity.csv
  cost_sensitivity.csv
  liquidity_bucket_exposure.csv
```

## 6. 验收标准

- [x] 单因子候选诊断包含 14 行。
- [x] TopK 敏感性包含 50、100、200 三档。
- [x] 成本敏感性包含 5、10、20 bps 三档。
- [x] 输出基础组合持仓的 liquidity bucket 分布。
- [x] Markdown 报告总结主要风险。
- [x] README 和总计划文档记录当前状态。

## 7. 当前结果

输出目录：

```text
outputs/alpha158_portfolio_diagnostics_v1/main_2021_2023/
```

单因子候选中 `net_excess_ir` 排名前三：

```text
alpha158_ROC30     0.803985
alpha158_ROC60     0.704626
alpha158_QTLD60    0.692407
```

TopK 敏感性：

```text
topk_50:  net_excess_ir 0.676352, average_turnover 0.889714
topk_100: net_excess_ir 0.552843, average_turnover 0.824857
topk_200: net_excess_ir 0.405610, average_turnover 0.715714
```

成本敏感性：

```text
cost_5bps:  net_excess_ir 0.596277
cost_10bps: net_excess_ir 0.552843
cost_20bps: net_excess_ir 0.465720
```

基础组合持仓 liquidity bucket 分布：

```text
bucket 3: 34.63%
bucket 4: 34.17%
bucket 5: 31.20%
```

主要结论：

- 当前组合 smoke 对 TopK 和交易成本都敏感。
- `topk_50` 表现更强，但平均换手率也更高。
- `alpha158_ROC30`、`alpha158_ROC60`、`alpha158_QTLD60` 是当前最值得优先深挖的候选。
- `alpha158_MIN5` 单因子结果接近无效，且带有 `low_monotonicity` warning，后续应谨慎处理。

## 8. 下一步

V3.15 完成后，再决定是否进入：

```text
V3.16 Alpha158 Portfolio Diagnostics Extension
```

可能扩展项：

- recent OOS 需要先扩展 Alpha158 expression frame 到 2026。
- 暴露诊断需要补入行业、市值和风格代理。
- 若换手过高，再设计低换手 score smoothing 或持仓缓冲规则。
