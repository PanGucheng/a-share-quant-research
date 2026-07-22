# PR #5A 模型输入协议交接计划 V1

## 1. 定位与停止边界

本文是逻辑 PR #4.1 完成后的下一阶段唯一启动清单。当前对话只负责把计划落实到仓库并完成 PR #4.1 收口；不得在本轮实现或训练 Ridge、Elastic Net、LightGBM，也不得创建任何模型 binary、coefficient、feature importance 或 prediction artifact。

固定顺序保持为：

```text
PR #5A 透明基线与统一输入协议
→ PR #5B Ridge → Elastic Net
→ PR #5C LightGBM
→ PR #5D 历史 OOS 科学比较
→ PR #6 新未来数据 / forward paper confirmation
```

当前进入 PR #5A 的机器前提已经成立：

```text
selection_integrity_status = ready
model_entry_hard_stop_active = false
feature_selection_holdout_clean = true
clustering_holdout_clean = true
fdr_family_semantics_valid = true
fdr_artifact_consumed = true
raw_input_provenance_complete = true
split_allowlists_frozen = true
pre_test_freeze_contract_ready = true
core_model_ready = true
pr5_model_training_ready = true
model_training_started = false
```

仍然明确为 false：

```text
full_research_authoritative_tradability_ready
historical_oos_comparison_complete
production_model_selected
model_training_started
```

## 2. PR #4.1 交接证据

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

权威历史停牌与方向涨跌停仍缺失，所以当前 Qlib 结果是 operational research evidence，不是 authoritative production backtest。

历史 30 批 materialize/cache-verify 审批记录保留两个事实：声明了 single-use，但当时尚未机器执行 current-HEAD binding 与 single-use consumption；该限制已在 run history 和 readiness evidence 中公开。矩阵 exact provenance、partition hash 与等价性通过，因此不要求第三次重算；未来所有批量运行必须使用已硬化 gate。

## 3. PR #5A 唯一目标

将已经冻结的两种透明方法纳入一个可供后续线性模型和 LightGBM 共用的输入、预测、评价与执行协议：

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
pre_test_freeze_id
```

任何 prediction artifact 禁止包含 label、return、IC、portfolio NAV 或 test selection metric。评价和执行必须是独立下游阶段。

## 6. 透明基线采用政策

当前 PR #4.1 已经在冻结后生成 Equal Weight 与 Stability Weight score。PR #5A 优先执行 deterministic adoption：

1. 验证现有 runtime SHA 与 compact receipt；
2. 把 `composite_score` 无损映射为统一 `prediction` schema；
3. 证明 row/key/value/hash 与原 score 一致；
4. 复用已 consumed 的 test release，不生成第二套“首次打开”记录；
5. 复用相同 `qlib_exchange_semantics_669_v1.yaml`，不修改成本、TopK、T+1、参与率或估值规则。

若无法无损采用，必须先阻塞并解释；不得通过重算 test 后挑选更好的透明版本。

## 7. 实施步骤

1. 从最新 main 创建独立 PR #5A 分支；
2. 审计 PR #4.1 合并后 Manifest commit/freshness，不伪造旧产物的新 commit；
3. 新增 `model_input_protocol_v1.yaml` 和 compact validator；
4. 冻结 validation metric、tie-break、coverage 和 final-fit scope；
5. 物化三个 split 的 canonical feature-order receipts；
6. 运行无 test read 的 schema/preprocessing canary；
7. 无损采用 Equal Weight 与 Stability Weight predictions；
8. 验证 prediction schema 不含 label/return/IC；
9. 生成 common-period inventory，但不根据 test 表现改变方法、权重或协议；
10. 复用 Qlib semantics 生成统一 transparent baseline evidence；
11. 更新 readiness：只标记 `pr5a_protocol_ready=true`，仍保持 `model_training_started=false`；
12. 运行全量 pytest、compact validators 与 CI，合并后在 main 复验。

## 8. Canary 与批量门禁

PR #5A 任何 runtime materialization 前必须：

- 全仓审阅；
- clean committed HEAD；
- 单 split、最多 5 个因子的 schema canary；
- row-order、missing、feature-order mutation；
- exact config/input/command/resource review bundle；
- 若达到大批量阈值，使用当前授权生成 exact session-waiver artifact；
- canary、hash 或 lineage 任一异常立即停止。

PR #5A 不应重算 669 因子矩阵；若实现要求重新读取全部矩阵，只允许读取当前 hash-verified runtime 的 allowlist columns。

## 9. Definition of Done

只有以下全部成立，才允许创建 PR #5B：

1. 三个 split 的 allowlist 和 feature order hash 固定；
2. primary metric 与 tie-break 机器可读且不可在结果后修改；
3. Equal Weight、Stability Weight 预测无损采用；
4. prediction schema 不包含结果或选择字段；
5. common-period 与 Qlib semantics 完全一致；
6. 已有 freeze/release lineage 被保留，不伪造新的首次打开；
7. mutation、freshness、output hashes 和 lineage 全通过；
8. `pr5a_protocol_ready=true`；
9. `historical_oos_comparison_complete=false`；
10. `production_model_selected=false`；
11. `model_training_started=false`；
12. pytest、validators、PR CI 与 main CI 全部通过。

## 10. PR #5B 前的强制停点

PR #5A 完成后必须再次提交 Ridge/Elastic Net 的 exact candidate grid、资源预算、canary 和 run approval。不得因为 `core_model_ready=true` 自动启动训练；readiness 表示输入资格成立，不表示已授权任意模型搜索。
