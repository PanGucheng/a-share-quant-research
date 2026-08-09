# 80 因子 Full-Research 试运行 V1

> ARCHIVED / HISTORICAL：试运行阶段已完成。

## 状态与边界

PR #3 已贯通真实 PIT universe 到 Qlib Exchange 的研究链，并通过紧凑 evidence readiness：

```text
full_research_trial_infrastructure_ready = true
full_research_validation_chain_ready = true
full_research_qlib_execution_operational = true
full_research_authoritative_tradability_ready = false
full_research_trial_ready = true
pr4_scale_up_ready = true
model_training_started = false
```

这表示 80 因子试运行的数据链、批处理、断点续跑、统计验证、透明 score 和执行链可用，可以进入 PR #4 的 669 因子规模化运行。它不表示 80 个因子已成为模型 allowlist，也不表示历史停牌和方向性涨跌停数据已达到权威 PIT 标准。

## 冻结样本

80 个因子在计算 IC 或收益前按来源、类别和名称分层冻结，不读取历史筛选排名：

| 来源 | 数量 |
| --- | ---: |
| Alpha158 | 30 |
| Alpha360 | 18 |
| TA | 14 |
| KunQuant Alpha101 | 10 |
| 项目基础因子 | 8 |

样本覆盖 22 个类别、不同窗口、正负预期方向。该目录是 pipeline trial catalog，不是训练特征白名单。

## 真实数据链结果

```text
PIT universe:       65 月、130,000 snapshots、6,248 intervals、3,983 股票
Feature matrix:     80/80 因子、5/5 partitions、每批 2,588,000 PIT keys
Label:              label_20d_t1，2,538,428 / 2,588,000 有效
Daily Rank IC:      80 因子、103,520 factor-date rows
Purged folds:       3 个 expanding walk-forward splits，泄漏/embargo violation = 0
FDR:                240 hypotheses，null FDR = 0
Stability:          12 stable_core、57 conditional_signal、11 monitor
Clustering:         12 eligible → 9 clusters → 9 representatives
Transparent score:  3 methods × 736,000 rows = 2,208,000 rows
Qlib execution:     3 splits、36,014 orders、36,005 fills、365 accounting days
```

标签固定为 t 日观察、t+1 入场、持有 20 个交易日。FDR 只使用每个 split 的训练期 family；稳定性选择 API 不读取 test 指标。最终 score 用于验证端到端工程链，不应解读为严格无偏的最终收益证据，因为聚类代表集合汇总了本轮所有 trial splits。

## 执行与能力缺口

Qlib 执行的 critical contracts 全部通过，包括完整日历、t+1、100 股整手、现金非负、账户守恒、费用分项、方向性可交易约束、成交量参与率、unfilled 记录和 target-delta 买卖。逐笔完整表保存在 ignored runtime parquet；仓库提交行数、SHA256、确定性样本、日账户和摘要。

当前唯一能力级阻断为：provider 的历史停牌和方向性涨跌停仍由 `volume/change` 代理推导，并非权威 PIT 标签。因此 `full_research_authoritative_tradability_ready=false`，不得把本轮结果描述为正式可交易收益验证。

## 复现顺序

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_factor_trial_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_point_in_time_universe_v1.py --config configs\point_in_time_universe_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_feature_matrix_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_labels_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_daily_ic_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\run_purged_walk_forward_v1.py --config configs\purged_walk_forward_full_research_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_multiple_testing_v1.py --config configs\factor_multiple_testing_full_research_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_rolling_stability_v1.py --config configs\factor_rolling_stability_full_research_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_clustering_v1.py --config configs\factor_clustering_full_research_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_score_construction_v1.py --config configs\factor_score_construction_full_research_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_qlib_exchange_full_research_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\report_full_research_trial_readiness_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\validate_full_research_trial_v1.py
```

## 下一阶段

PR #4 只做 669 因子规模化：冻结全量批次和 FDR family，复用本轮研究语义，验证资源预算、缓存、断点续跑、失败重试和最终 allowlist。不得在 PR #4 同时启动 Ridge、Elastic Net 或 LightGBM；模型训练仍属于 PR #5。
