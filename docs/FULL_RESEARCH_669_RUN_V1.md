# 669 因子 Full-Research 全量运行 V1

> **2026-07-21 合并后审计增补：**本文中的矩阵规模、批处理、IC、outer split 和 Qlib Exchange 数字仍是 PR #4 的历史工程证据；“16 个代表已冻结为模型 allowlist”和模型 readiness 结论已经撤回。当前代表读取了 outer-test 信息，聚类没有按 development dates 截断，Stability 没有真实消费上游 FDR artifact，raw/provider/source provenance 也不完整。当前 16 个代表只允许作为 `exploratory/test-influenced` 证据，`model_input_allowed=false`。已提交机器 readiness 仍错误显示三个模型门禁为 true，当前 Draft PR 必须先实施 hard-stop；下述状态是必须落地的安全目标，不是对当前机器 artifact 的描述。下一步不是模型 PR，而是先执行 [Selection Holdout Integrity 与后续模型计划 V1](./SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md) 中的逻辑 PR #4.1。

## 状态与边界

PR #4 已按 PR #3 冻结的研究语义完成全部 669 个 runnable 因子的规模化运行。当前安全目标为：

```text
full_research_669_infrastructure_ready = true
full_research_669_matrix_content_ready = true
full_research_669_qlib_execution_operational = true
full_research_authoritative_tradability_ready = false
feature_selection_holdout_clean = false
clustering_holdout_clean = false
fdr_artifact_consumed = false
raw_input_provenance_complete = false
feature_allowlist_frozen = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
```

本阶段扩大因子规模并验证了批处理与执行链，没有训练模型。历史停牌和方向性涨跌停仍由代理字段推导，因此权威 tradability capability 保持 blocked。PR #4 当时报告的模型输入冻结结论已被合并后审计撤回，旧 artifact 不删除、不覆写，仅作为历史证据。

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

目录无重复、无表现筛选；每批最多 25 个因子。本轮稳定性和聚类产生的 16 个代表是历史探索结果，不是可用于模型的最终 allowlist；逻辑 PR #4.1 将按 outer split 分别重新生成 holdout-clean allowlist，数量由数据决定。

## 全量结果

```text
Feature matrix:    669/669 因子、30/30 partitions、每批 2,588,000 PIT keys
Matrix runtime:    7,361,301,484 bytes；首轮 14,204.8 秒；缓存复跑约 32 秒
Label:             label_20d_t1，2,538,428 / 2,588,000 有效，覆盖率 98.0845%
Daily Rank IC:     669 因子、865,686 factor-date rows；最少 1,228 个有效 IC 日
Purged folds:      3 个 expanding walk-forward splits；泄漏/embargo violation = 0
FDR families:      3 个独立 split family × 669 hypotheses；合计 BH 通过 1,600，BY 通过 1,277，null FDR = 0
Stability:         65 stable_core、518 conditional_signal、86 monitor
Clustering:        65 eligible → 16 clusters → 16 exploratory representatives
Transparent score: 3 methods × 736,000 rows = 2,208,000 rows
Qlib execution:    3 splits、34,906 orders、34,898 fills、365 accounting days
```

30 个矩阵分区都有输入哈希、输出哈希、尝试次数、耗时、大小和 cache-hit 元数据。首轮完整物化后，第二轮 30/30 从哈希缓存恢复，证明断点续跑与缓存有效。大型 parquet 保留在 ignored runtime；仓库保存 manifest、schema、覆盖率、失败清单、确定性样本和复现配置。

## 研究与执行语义

- 标签固定为观察日 `t`、`t+1` 入场、持有 20 个交易日。
- FDR 输出实际包含 3 个独立 split family，每个 family 固定 669 个 hypotheses，不是单一 2,007-hypothesis family。
- 当前 Stability 虽把 FDR artifact 声明为上游，实际内部重新 bootstrap/FDR；两套结果的 2,007 个 q-value 全部不一致，必须在 PR #4.1 改为逐行消费上游结果。
- 当前稳定性角色和 eligibility 读取 outer-test IC、test coverage 与 degradation；因此“测试指标不参与选择”的历史表述不成立。
- 当前聚类联合使用最多 60 个截面 exposure 和日度 IC 相关性，但没有按每个 outer split 的 development dates 过滤，必须重做。
- Qlib 执行复用 PR #2 的统一 Exchange 语义与 PR #3 的配置，不因全量因子结果修改交易假设。
- 当前 16 个代表及相应透明 score/Qlib execution 仅作探索性历史证据；不得进入 PR #5。

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

先完成逻辑 PR #4.1：机器级撤回 false-positive readiness，补齐 raw/provider/source provenance 与 cache key v3，建立 outer-train FDR eligibility + development robustness 语义，让 Stability 真实消费三个 split-scoped FDR artifacts，并按 development dates 生成 split-specific clustering、allowlists、透明 score 和 Qlib execution。Outer-test IC、exposure、labels、OHLCVA、row order 和缺失 mutation 必须不能改变任何选择产物；test evaluation 前必须生成 pre-test freeze。

30 批矩阵重跑前必须先完成受限 canary 并推送 bulk-run review bundle，由用户核对 commit/config/input hashes、日期/FDR 语义、资源预算和 exact command 后针对 run ID 明确批准。没有批准或批准范围发生变化时必须停止。

只有逻辑 PR #4.1 全部门禁通过后，才进入 PR #5A—#5D：先冻结共同输入协议并重跑 Equal Weight / Stability Weight，再依次运行 Ridge、Elastic Net、LightGBM，最后在相同 outer test、common period 和 Qlib Exchange 上统一比较。
