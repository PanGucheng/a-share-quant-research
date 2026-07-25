# Historical Model Comparison V1 实施计划

## 1. 目标与边界

本阶段是逻辑 PR #5D，只比较已经冻结和释放的五种方法：

```text
Equal Weight
Stability Weight
Ridge
Elastic Net
LightGBM
```

主结论仅来自 prediction-level 历史 OOS 科学比较。不得重新训练模型、重新选参、
改变透明权重或重新释放机器学习 test prediction。Historical Instrument State V2
Decision B 继续冻结，不搜索新公告或数据源。

因 `SZ300280` 在 `2025-04-18` 超过冻结的 20 个交易日 stale valuation 上限，
五方法组合/NAV 比较保持：

```text
five_method_historical_portfolio_comparison_complete = false
portfolio_comparison_status = blocked_execution_capability
```

不得用无限旧价、未来知情清仓或无 Tier-0 证据的结算价消除阻断。

## 2. 权威输入

直接 parent 固定为：

- `date_split_semantics_v1/current`；
- `research_selection_lineage_closure_v1/current`；
- `full_research_labels_v2/current`；
- `split_transparent_score_v2/current`；
- `research_linear_models_v1/current`；
- `research_lightgbm_v1/current`。

日期分配只读取 Selection Lineage Closure 的 `date_assignments.csv`。旧
`purged_walk_forward_v1/full_research_669/artifact_manifest.json` 只能是 legacy
payload，不得成为本阶段直接 parent。

透明基线从冻结的 `composite_scores.parquet` 计算 daily Rank IC。每个 split 的
标签 key/value 哈希必须同时等于 Ridge、Elastic Net 与 LightGBM 已消费 release
receipt 中的 `test_label_sha256`。线性模型和 LightGBM 只读取已发布
`test_daily_ic.csv` 与 `test_metrics.csv`。

## 3. 冻结指标

每个 split、每种方法必须报告：

- mean daily Rank IC；
- daily Rank IC IR；
- positive-IC day ratio；
- prediction coverage；
- daily IC count；
- moving-block bootstrap 95% 区间。

汇总必须同时保留三个 split，并报告：

- 三个 split 的等权 mean daily Rank IC；
- 三个 split 的等权 ICIR；
- pooled daily Rank IC（仅描述性）；
- 最差 split Rank IC；
- split 排名均值与标准差；
- 最低 prediction coverage。

历史科研 leader 按以下固定顺序选择：

```text
equal_split_mean_daily_rank_ic
→ equal_split_mean_daily_rank_ic_ir
→ minimum_split_prediction_coverage
→ lower_method_complexity
→ canonical_method_name
```

还需在每个 split 的共同日期上生成十组两两 daily IC 差异和 moving-block
bootstrap 区间。不得只展示对获胜方法有利的配对。

## 4. 完整性合同

发布前必须全部通过：

1. 六个直接 parent 均为 pass、complete、clean；
2. 所有 parent 已记录 output hash 仍有效；
3. 日期 authority 未引用 legacy purged manifest；
4. 透明 score runtime hash 与 `score_artifact.csv` 一致；
5. 三个 split 的 test 日期与 Selection Lineage Closure 精确一致；
6. 透明标签哈希与三个已发布模型方法完全一致；
7. 五方法 × 三 split 完整；
8. 每个方法在共同日期上都有合法 daily IC；
9. coverage 不低于 0.95；
10. bootstrap 使用固定 seed、样本数和 block length；
11. 所有数值和表格可重复生成；
12. production、authoritative execution、unbiased estimate 均为 false。

## 5. 输出

`outputs/historical_model_comparison_v1/current/` 至少包含：

- `split_metrics.csv`；
- `daily_ic.csv`；
- `bootstrap_uncertainty.csv`；
- `pairwise_daily_ic_differences.csv`；
- `method_summary.csv`；
- `historical_research_leader.json`；
- `execution_capability_status.csv`；
- `parent_receipts.csv`；
- `input_receipts.csv`；
- `contract_status.csv`；
- `readiness_summary.csv`；
- `comparison_report.md`；
- `resolved_config.json`；
- `artifact_manifest.json`。

## 6. 完成状态

PR #5D 完成时允许：

```text
historical_oos_model_comparison_complete = true
historical_oos_research_leader = <method>
```

但必须保持：

```text
five_method_historical_portfolio_comparison_complete = false
production_model_selected = false
authoritative_oos_execution_ready = false
unbiased_final_estimate = false
```

历史 leader 只支持本组已观察历史 test 的科研描述。生产候选确认必须依赖 PR #5D
之后出现的新未来时期或 forward/paper evidence。
