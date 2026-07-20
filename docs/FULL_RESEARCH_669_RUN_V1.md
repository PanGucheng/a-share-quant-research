# 669 因子 Full-Research 全量运行 V1

## 状态与边界

PR #4 已按 PR #3 冻结的研究语义完成全部 669 个 runnable 因子的规模化运行：

```text
full_research_669_infrastructure_ready = true
full_research_669_validation_chain_ready = true
full_research_669_qlib_execution_operational = true
full_research_authoritative_tradability_ready = false
feature_allowlist_frozen = true
core_model_ready = true
pr5_model_training_ready = true
model_training_started = false
```

本阶段只扩大因子规模、验证批处理和冻结模型输入，不调整筛选阈值、不训练模型。历史停牌和方向性涨跌停仍由代理字段推导，因此权威 tradability capability 保持 blocked。

## 冻结因子家族

因子目录在计算 IC 和收益前冻结，不读取本轮表现：

| 来源 | 因子数 | 分区数 |
| --- | ---: | ---: |
| Alpha158 | 155 | 7 |
| Alpha360 | 358 | 15 |
| TA | 77 | 4 |
| KunQuant Alpha101 | 64 | 3 |
| 项目基础因子 | 15 | 1 |
| 合计 | 669 | 30 |

目录无重复、无表现筛选；每批最多 25 个因子。最终模型特征 allowlist 是本轮稳定性和聚类产生的 16 个冻结代表，而不是全部 669 个原始因子。

## 全量结果

```text
Feature matrix:    669/669 因子、30/30 partitions、每批 2,588,000 PIT keys
Matrix runtime:    7,361,301,484 bytes；首轮 14,204.8 秒；缓存复跑约 32 秒
Label:             label_20d_t1，2,538,428 / 2,588,000 有效，覆盖率 98.0845%
Daily Rank IC:     669 因子、865,686 factor-date rows；最少 1,228 个有效 IC 日
Purged folds:      3 个 expanding walk-forward splits；泄漏/embargo violation = 0
FDR family:        2,007 hypotheses；BH 通过 1,600，BY 通过 1,277，null FDR = 0
Stability:         65 stable_core、518 conditional_signal、86 monitor
Clustering:        65 eligible → 16 clusters → 16 frozen representatives
Transparent score: 3 methods × 736,000 rows = 2,208,000 rows
Qlib execution:    3 splits、34,906 orders、34,898 fills、365 accounting days
```

30 个矩阵分区都有输入哈希、输出哈希、尝试次数、耗时、大小和 cache-hit 元数据。首轮完整物化后，第二轮 30/30 从哈希缓存恢复，证明断点续跑与缓存有效。大型 parquet 保留在 ignored runtime；仓库保存 manifest、schema、覆盖率、失败清单、确定性样本和复现配置。

## 研究与执行语义

- 标签固定为观察日 `t`、`t+1` 入场、持有 20 个交易日。
- FDR family 固定为 669 因子 × 3 个 purged 训练窗口，不按结果缩小 family。
- 稳定性选择只读取 train/validation 字段，测试指标不进入筛选函数。
- 聚类联合使用最多 60 个历史截面暴露相关性和日度 IC 相关性。
- Qlib 执行复用 PR #2 的统一 Exchange 语义与 PR #3 的配置，不因全量因子结果修改交易假设。
- 最终 16 个代表冻结为 PR #5 的 feature allowlist；PR #5 必须按 Equal Weight、Stability Weight、Ridge、Elastic Net、LightGBM 顺序推进。

## 复现顺序

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\freeze_full_research_factor_catalog_669_v1.py --config configs\full_research_factor_catalog_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_feature_matrix_v1.py --config configs\full_research_feature_matrix_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_labels_v1.py --config configs\full_research_labels_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_full_research_daily_ic_v1.py --config configs\full_research_daily_ic_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_purged_walk_forward_v1.py --config configs\purged_walk_forward_full_research_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_multiple_testing_v1.py --config configs\factor_multiple_testing_full_research_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_rolling_stability_v1.py --config configs\factor_rolling_stability_full_research_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_clustering_v1.py --config configs\factor_clustering_full_research_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_factor_score_construction_v1.py --config configs\factor_score_construction_full_research_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\run_qlib_exchange_full_research_v1.py --config configs\qlib_exchange_full_research_669_v1.yaml
E:\anaconda_envs\qlib_env\python.exe scripts\report_full_research_669_readiness_v1.py
E:\anaconda_envs\qlib_env\python.exe scripts\validate_full_research_669_v1.py
```

## 下一阶段

PR #5 只使用冻结的 16 因子 allowlist 和相同的 purged folds、common period 与 Qlib Exchange。先运行等权和稳定性加权透明基线，再运行 Ridge、Elastic Net，最后才运行 LightGBM。测试集只用于最终评价，不用于特征选择或调参。
