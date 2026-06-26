# Alpha158 Candidate Portfolio Smoke V1

本文档是 V3.14 的具体计划与执行记录。它承接 Alpha158 candidate pool，只做最小组合接口验证，不把当前结果解释为可交易策略。

本阶段继续遵守边界：

- 不训练新模型。
- 不调复杂策略参数。
- 不做实盘。
- 不替换 Qlib baseline。
- 不绕过 data_quality、tradability 和 candidate pool 约束。

## 1. 目标

建立如下链路：

```text
alpha158_alpha_candidates.csv
  -> Alpha158 expression frame
  -> tradability labels
  -> low-frequency portfolio smoke
  -> compact report
```

本阶段只回答三个问题：

1. 后续组合模块能否直接读取 `alpha_candidate`。
2. candidate pool 的排除规则是否在组合入口继续生效。
3. 低频换仓、可交易性过滤、交易成本、换手率和报告输出是否跑通。

## 2. 输入

```text
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
outputs/alpha158_expression_frame_v1/full158_main_research/
outputs/tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29/tradability_labels.csv
```

## 3. 组合 smoke 口径

默认组合口径：

```text
score_policy: equal_directional_zscore
candidate_count: 14
date_range: 2021-01-01 to 2023-12-29
rebalance_every: 20 trading days
topk: 100
cost: 10 bps per one-way turnover
min_liquidity_bucket: 3
min_tradability_score: 75
min_capacity_multiple: 2
```

因子分数：

```text
daily cross-sectional winsorized z-score
positive consensus_direction -> +1
negative consensus_direction -> -1
score = valid directional z-score mean
```

说明：

- 这是最小接口 smoke，不是最终 alpha 组合定义。
- 当前 14 个候选方向均为 positive，因此 V1 等价于候选因子的等权横截面 z-score 平均。
- `low_monotonicity` 只作为 warning 写入报告，不在本阶段二次剔除。
- 交易约束继续使用既有 `tradability_labels.csv`。

## 4. 实现文件

```text
configs/alpha158_candidate_portfolio_smoke_v1.yaml
factor_research/alpha158_portfolio_smoke.py
scripts/run_alpha158_candidate_portfolio_smoke_v1.py
```

运行命令：

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\run_alpha158_candidate_portfolio_smoke_v1.py --config configs\alpha158_candidate_portfolio_smoke_v1.yaml
```

## 5. 输出

```text
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/
  alpha158_candidate_portfolio_smoke_report.md
  summary.csv
  daily_returns.csv
  rebalance_summary.csv
  positions.csv
  candidate_weight_table.csv
  score_component_summary.csv
```

## 6. 验收标准

- [x] 只读取 `role == alpha_candidate` 的因子。
- [x] 组合入口不包含 holdout、excluded、high_turnover、unstable_context 或非代表冗余因子。
- [x] expression frame 中找到全部 14 个候选因子。
- [x] 输出低频换仓 summary、daily returns、positions 和 Markdown 报告。
- [x] 报告显式标记 `low_monotonicity` warning。
- [x] README 和总计划文档记录当前状态。

## 7. 当前结果

输出目录：

```text
outputs/alpha158_candidate_portfolio_smoke_v1/main_2021_2023/
```

结果摘要：

```text
candidate_count: 14
warning_low_monotonicity_count: 4
trading_days: 700
rebalance_count: 37
executed_rebalances: 35
positions: 3500
net_annualized_excess: 0.060632
net_excess_ir: 0.552843
average_turnover: 0.824857
net_max_drawdown: -0.321708
```

说明：

- 该结果只证明 candidate pool 到 portfolio smoke 的接口已经跑通。
- 当前平均换手率约 `0.824857`，仍然偏高，后续必须做换手、容量和暴露诊断。
- 当前窗口只覆盖 expression frame 与 tradability 都具备的 `2021-01-01` 至 `2023-12-29`。
- `alpha158_MIN5`、`alpha158_QTLD10`、`alpha158_VSUMN60`、`alpha158_ROC10` 的 `low_monotonicity` warning 已在报告中显式保留。

## 8. 下一步

V3.14 跑通后，再决定是否进入：

```text
V3.15 Portfolio Smoke Diagnostics
```

下一步重点不是立刻优化收益，而是补齐组合诊断：

- 单因子候选对比。
- 候选组合与等权 benchmark 对比。
- 行业/市值/流动性暴露诊断。
- 换手和容量敏感性。
- main window 与 recent OOS 的衔接方式。
