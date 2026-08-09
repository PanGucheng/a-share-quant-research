# Research Linear Models V1 实施计划

> ARCHIVED / HISTORICAL：线性模型研究已完成并冻结。

> 逻辑阶段：PR #5B
> 实验类别：`post_observation_research`
> Historical test：已被历史研究观察，不能解释为无偏最终估计
> Production model selection：禁止

## 1. 边界

本阶段只实现并依次运行：

```text
Ridge
→ Ridge 3/3 split 完成
→ Elastic Net
→ Elastic Net 3/3 split 完成
```

不实现 LightGBM，不改变 45/46/52 split-specific allowlist，不重新选择因子，
不把历史 OOS leader 宣布为生产模型，不声称得到 authoritative execution 或
unbiased final estimate。

唯一研究训练入口为：

```text
outputs/research_model_protocol_v1_1/current/artifact_manifest.json
```

直接读取 readiness CSV、旧 V1 protocol、旧 global representatives 或 legacy
purged manifest 必须 fail-closed。

## 2. 冻结候选与选择语义

精确机器配置为 `configs/research_linear_models_v1.yaml`。

Ridge：

```text
alpha = [0.01, 0.1, 1.0, 10.0, 100.0]
fit_intercept = true
solver = solver canary 冻结值
```

Solver canary 只使用 `split_001 × 5 factors × 20 train dates`，不读取
validation/test，不根据预测质量选择。`cholesky` 与 `lsqr` 必须各重复拟合两次；
只有 coefficient/prediction hash 稳定的 solver 合格，再按 peak memory、wall
time、canonical name 选择。

Elastic Net：

```text
alpha = [0.001, 0.01, 0.1, 1.0, 10.0]
l1_ratio = [0.1, 0.5, 0.9]
max_iter = 5000
tol = 1e-5
selection = cyclic
random_seed = 20260725
```

所有候选只按 outer-validation：

```text
mean_daily_rank_ic
→ daily_rank_ic_ir
→ prediction_coverage
→ lower_model_complexity
→ canonical_candidate_sha256
```

不得使用收益、Sharpe、test IC 或 test prediction 选参。Validation label
mutation必须改变 label、metric 和 search artifact hash；selected candidate
是否改变只记录，不作脆弱断言。

## 3. 数据与拟合

每个 split 只使用自己的 frozen feature order。训练样本资格为 label 非空且至少
一个 frozen feature 有限，target 在最终合格样本内按日横截面 rank-centered。

搜索阶段：

```text
outer train fit preprocessing/model
outer validation transform/predict/select
```

选参后：

```text
outer train + validation
→ 从头重新 fit weighted preprocessing
→ 从头重新 fit final model
```

每日样本权重之和为 1；weighted median、weighted scaler、全 NaN 行/列、
近零方差和 feature order 全部复用 V1.1 协议。

## 4. Test release

开发搜索、mutation、final refit和所有哈希冻结前，test feature/label read
预算为 0。每个 `(split, method)` 必须先生成不可变
`pre_test_freeze_manifest.json`，然后只允许一次 test release。

Test prediction只含 frozen prediction schema；label 进入独立 evaluation
artifact，不能进入 prediction artifact。重复执行只能验证同一 frozen input
的确定性，不能覆盖第一次 release receipt。

## 5. 分阶段停点

```text
solver canary
→ Ridge 5-factor/1-candidate canary
→ split_001 full Ridge grid
→ 3-split Ridge
→ split_001 full Elastic Net grid
→ 3-split Elastic Net
→ pre-test freeze
→ single test release
```

每一步必须验证 lineage、零提前 test read、资源预算和输出哈希；失败时停止后续
阶段，不得跳过或放宽门槛。

## 6. 资源预算与授权

冻结预算：

```text
peak RSS <= 4096 MiB
runtime disk <= 12 GiB
wall time <= 8 h
start free disk >= 20 GiB
threads = 1
```

本持续对话中用户已明确要求继续推进，登记为
`user_session_waiver`。该授权只覆盖本文件和机器配置定义的 scope；候选网格、
输入、指标、命令、代码或范围变化会使 run approval 失效，必须重新生成 review
bundle。

## 7. Definition of Done

```text
Ridge 3/3 split complete
Elastic Net 3/3 split complete
linear_model_research_complete = true
research_model_experiment_started = true
model_training_started = true
test_read_before_freeze = 0
unknown_leakage_difference = 0
production_model_selected = false
authoritative_execution = false
unbiased_final_estimate = false
```

## 8. 实施回执与执行能力边界

截至 2026-07-26，PR #5B 的模型研究部分已完成：

```text
Ridge                  3/3 split complete
Elastic Net            3/3 split complete
pre-test freeze        6/6
single test release    6/6
test predictions       1,471,764 rows
test read before freeze = 0
linear_model_research_complete = true
production_model_selected = false
```

使用冻结 Market Cache V3 和相同 Qlib 配置进行的辅助执行诊断为：

```text
successful scenarios = 4/6
split_001 Ridge / Elastic Net = complete
split_002 Ridge / Elastic Net = blocked
split_003 Ridge / Elastic Net = complete
```

两个 `split_002` 场景均在 `2025-04-18` 对已持有的 `SZ300280` 估值时触发
`blocked_unpriceable_held_position`。该股票长期停牌后已超过冻结的 20 个
交易日 stale valuation 上限。禁止：

- 为使回测通过而无限延用旧 close；
- 利用后来已知的停牌长度，在停牌前主动清仓；
- 构造没有 Tier-0 证据的退市或终止上市结算价；
- 将 Qlib 的底层 `NoneType` 异常误报为成功 execution。

执行器必须发布 blocked manifest、失败 split/method、精确日期和 instrument，并
继续运行其余独立场景。当前机器状态为：

```text
linear_model_research_complete = true
linear_model_execution_complete = false
linear_model_execution_operational_ready = false
historical_oos_linear_evaluation_complete = true
authoritative_execution = false
unbiased_final_estimate = false
production_model_selected = false
```

这一能力阻断不回滚已冻结的 prediction IC 研究结论，也不阻止 PR #5C 按同一
prediction-only、零泄漏协议训练 LightGBM；但在问题未由用户提供的新 Tier-0
数据源或新执行政策解决前，PR #5D 不得声称完成五方法的全历史组合或 NAV
比较。PR #5D 仍可完成 prediction-level 历史科学比较，并必须把组合比较标记为
`blocked_execution_capability`。
