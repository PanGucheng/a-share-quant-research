# PR #5A 模型输入协议交接计划 V1（延后）

> **2026-07-23 状态：暂停，不能作为当前启动清单。** 当前唯一执行计划为 [Research / Execution Accuracy Correction V1](./ACCURACY_CORRECTION_V1_PLAN.md)。本文件保留后续模型协议设计，但只能在 GitHub PR #6 与 PR #7 全部门禁通过后重新启用。

## 1. 定位与停止边界

本文是逻辑 PR #5A 的延后设计。逻辑 PR #4.1 已完成 holdout 隔离，但其后实现审计发现研究公式与历史执行语义缺陷；不得在 PR #6/#7 完成前实现或训练 Ridge、Elastic Net、LightGBM，也不得创建任何模型 binary、coefficient、feature importance 或 prediction artifact。

固定顺序保持为：

```text
GitHub PR #6 Research Accuracy Correction V1
→ GitHub PR #7 Execution Accuracy Correction V1
→ PR #5A 透明基线与统一输入协议
→ PR #5B Ridge → Elastic Net
→ PR #5C LightGBM
→ PR #5D 历史 OOS 科学比较
→ 新未来数据 / forward paper confirmation
```

当前只有选择隔离前提成立：

```text
selection_integrity_status = ready
feature_selection_holdout_clean = true
clustering_holdout_clean = true
fdr_family_semantics_valid = true
fdr_artifact_consumed = true
raw_input_provenance_complete = true
model_training_started = false
```

当前模型与权威执行前提明确为 false：

```text
research_formula_accuracy_ready
matrix_v4_lifecycle_clean
pairwise_ic_ready
model_research_ready
execution_semantics_accuracy_ready
market_cache_v2_ready
authoritative_oos_execution_ready
core_model_ready
pr5_model_training_ready
full_research_authoritative_tradability_ready
historical_oos_comparison_complete
production_model_selected
model_training_started
```

## 2. PR #4.1 交接证据

本节数字只描述 2026-07-22 的历史运行。它们证明 holdout mutation 与 lineage 机制工作，但不能证明基础因子矩阵、IC 公式或 Exchange 执行数值正确。当前 48/46/54 allowlist、score 和 OOS execution 已被登记为 `superseded/non_authoritative`，不得直接交接给 PR #5A。

- 669 因子、30 个 cache-key v3 分区，矩阵与 PR #4 数值完全等价；
- 三个 outer-train FDR family，各 669 个唯一假设；
- holdout-clean stable-core 数：461 / 238 / 215；
- split allowlist 数：48 / 46 / 54；
- 36 组 test-only mutation 全部通过，weights hash 也保持不变；
- 3 份 pre-test freeze 在任何 test feature read 前生成；
- 3 份 test-release receipt 均为 `consumed`；
- Equal Weight 与 Stability Weight 共 1,472,000 行非空 score，逐 split coverage=1；
- Qlib 运行覆盖 3 split × 2 method、730 个会计日；所有 critical execution contract 通过；
- 旧 `exploratory_global_representatives_v1` 永久为 `test_influenced/model_input_allowed=false`。

除权威历史停牌与方向涨跌停仍缺失外，Accuracy Correction 审计还确认 PIT lifecycle、pairwise IC、同日 `$change`、印花税和长期陈旧估值问题。因此当前 Qlib 结果只能作为历史工程证据，不是 authoritative research execution。

历史 30 批 materialize/cache-verify 审批记录与 v3 哈希继续保留。是否重算某一 partition 由 PR #6 的 669 因子依赖分类和 `impact_date_manifest` 决定：纯时间序列因子可过滤非法 key 并证明 common-key bit-identical；横截面、混合和 unknown 因子必须按影响范围重算。不能再预先断言无需重算。

## 3. PR #5A 唯一目标

在 PR #6/#7 完成后，将重新冻结的两种透明方法纳入一个可供后续线性模型和 LightGBM 共用的输入、预测、评价与执行协议：

```text
split-specific allowlist
→ canonical feature order
→ common input schema
→ frozen preprocessing protocol
→ prediction-only artifact
→ common-period diagnostics
→ identical Qlib Exchange semantics
```

PR #5A 不重新选择因子、不改变权重、不重新解释 outer test、不训练任何统计学习模型。

## 4. 必须冻结的统计协议

在读取任何后续 validation metric 前，提交机器可读配置：

```text
primary_validation_metric = mean_daily_rank_ic
tie_break_1 = icir
tie_break_2 = prediction_coverage
tie_break_3 = lower_model_complexity
final_tie_break = canonical_config_sha256
minimum_prediction_coverage = 0.95
final_fit_scope = outer_train_plus_validation
```

透明基线没有超参数搜索，必须显式记录：

```text
search_method = not_applicable_fixed_transparent_method
maximum_candidates_per_split = 1
random_seed = not_applicable_deterministic
model_binary_sha256 = not_applicable_transparent_baseline
```

后续 PR #5B/#5C 只能复用该 primary metric 和 tie-break 顺序，不得模型跑完后改用收益、Sharpe 或 test IC 选参。

## 5. 统一输入与输出 schema

输入表至少包括：

```text
outer_split_id
fold
datetime
instrument
factor
feature_order
value
allowlist_sha256
feature_order_sha256
factor_frame_id
```

预测表固定为：

```text
outer_split_id
datetime
instrument
method
prediction
prediction_artifact_id
allowlist_sha256
feature_order_sha256
research_freeze_id
```

任何 prediction artifact 禁止包含 label、return、IC、portfolio NAV 或 test selection metric。评价和执行必须是独立下游阶段。

## 6. 透明基线采用政策

PR #5A 只能采用 PR #6/#7 生成并通过 readiness 的 Equal Weight 与 Stability Weight score。采用政策为：

1. 验证修正后 runtime SHA、score policy SHA 与 compact receipt；
2. 把 `composite_score` 无损映射为统一 `prediction` schema；
3. 证明 row/key/value/hash 与原 score 一致；
4. 保留旧 consumed release 的历史事实，不把修正版本伪装为新的首次打开；
5. 复用 PR #7 冻结的 corrected execution config，不修改成本、TopK、T+1、参与率或估值规则；
6. 读取 `bugfix_research_freeze_v1`，确认 `freeze_type=post_observation_bugfix`、`historical_test_already_observed=true`、`unbiased_final_estimate=false`。

若无法无损采用，必须先阻塞并解释；不得通过重算 test 后挑选更好的透明版本。

## 7. 实施步骤

1. 验证 PR #6 与 PR #7 已合并且 main CI/readiness 通过；
2. 从最新 main 创建独立 PR #5A 分支；
3. 审计修正后 Manifest commit/freshness，不伪造旧产物的新 commit；
4. 新增 `model_input_protocol_v1.yaml` 和 compact validator；
5. 冻结 validation metric、tie-break、coverage 和 final-fit scope；
6. 物化三个 split 的 canonical feature-order receipts；
7. 运行无 test read 的 schema/preprocessing canary；
8. 无损采用修正后的 Equal Weight 与 Stability Weight predictions；
9. 验证 prediction schema 不含 label/return/IC；
10. 生成 common-period inventory，但不根据 test 表现改变方法、权重或协议；
11. 复用 corrected Qlib semantics 生成统一 transparent baseline evidence；
12. 更新 readiness：只标记 `pr5a_protocol_ready=true`，仍保持 `model_training_started=false`；
13. 运行全量 pytest、compact validators 与 CI，合并后在 main 复验。

## 8. Canary 与批量门禁

PR #5A 任何 runtime materialization 前必须：

- 全仓审阅；
- clean committed HEAD；
- 单 split、最多 5 个因子的 schema canary；
- row-order、missing、feature-order mutation；
- exact config/input/command/resource review bundle；
- 若达到大批量阈值，使用当前授权生成 exact session-waiver artifact；
- canary、hash 或 lineage 任一异常立即停止。

PR #5A 不应重算 669 因子矩阵；只能读取 PR #6 Matrix v4 的 hash-verified、split-allowlisted columns，禁止回退到当前 v3 或已被替代的 48/46/54 输入。

## 9. Definition of Done

只有以下全部成立，才允许创建 PR #5B：

1. `model_research_ready=true` 且 `authoritative_oos_execution_ready=true`；
2. `core_model_ready=true` 且 `pr5_model_training_ready=true`；
3. 三个 split 的修正后 allowlist 和 feature order hash 固定；
4. primary metric 与 tie-break 机器可读且不可在结果后修改；
5. Equal Weight、Stability Weight 预测无损采用；
6. prediction schema 不包含结果或选择字段；
7. common-period 与 corrected Qlib semantics 完全一致；
8. post-observation freeze/release lineage 被保留，不伪造新的 untouched test；
9. mutation、freshness、output hashes 和 lineage 全通过；
10. `pr5a_protocol_ready=true`；
11. `historical_oos_comparison_complete=false`；
12. `production_model_selected=false`；
13. `model_training_started=false`；
14. pytest、validators、PR CI 与 main CI 全部通过。

## 10. PR #5B 前的强制停点

PR #5A 完成后必须再次提交 Ridge/Elastic Net 的 exact candidate grid、资源预算、canary 和 run approval。不得因为 readiness 为 true 自动启动训练；readiness 表示输入资格成立，不表示已授权任意模型搜索。当前阶段在进入任何 PR #5A 模型实现前停止。
