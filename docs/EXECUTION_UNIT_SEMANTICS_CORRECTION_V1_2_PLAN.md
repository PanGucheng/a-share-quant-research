# Execution Unit Semantics Correction V1.2

> 状态：正式实施基线  
> 前置证据：`data_source_audit_v2:500812e9...`  
> 硬边界：不进入 PR #5A，不训练模型，不修改 Matrix v4、labels、IC、FDR、stability、clustering、allowlist、weights 或 score。

## 1. 根因与影响

Data Source Audit V2 在 150 只股票、2024-08-01 至 2026-02-04 的隔离 canary 上得到：

```text
Community 与 BaoStock:
raw close tolerance match = 100%
volume tolerance match = 100%
amount tolerance match = 100%

Community raw price = provider price / factor
Community volume_shares = provider volume × factor × 100
Community amount_cny = provider amount × 1000
```

当前 `build_market_cache_v2.py` 使用：

```text
reported_volume = provider volume × factor
amount = provider amount
```

因此：

- participation volume 被缩小 100 倍；
- 5% 参与率约束被错误收紧 100 倍；
- amount 保留为千元而非元，当前执行未消费该字段，但 schema 语义错误；
- 旧 corrected execution 的订单、部分成交、拒单、现金、费用和 NAV 都必须视为 superseded / non-authoritative；
- 研究 score 不受影响，禁止重算选择链。

## 2. 立即机器级撤回

第一个业务动作必须设置：

```text
data_source_audit_v2_ready = true
research_formula_accuracy_ready = true
corrected_score_ready = true

execution_unit_semantics_ready = false
market_cache_volume_unit_ready = false
execution_semantics_accuracy_ready = false
market_cache_v2_ready = false

authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
model_entry_hard_stop_active = true
```

状态名：

```text
accuracy_correction_status = execution_unit_semantics_correction_required
```

旧 Market Cache v2、bugfix freeze 与 corrected execution 必须标记为 superseded；旧 score 继续是当前冻结研究信号。

## 3. 实施范围

### 3.1 单位契约

新增显式配置：

```text
community_volume_unit = adjusted_board_lots
community_volume_to_shares_multiplier = 100
community_amount_unit = cny_thousands
community_amount_to_cny_multiplier = 1000
market_cache_semantics_version = v3
```

禁止通过自动寻找“最接近缩放倍数”推断单位。配置值必须由冻结 fixture 和 Data Source Audit V2 receipt 共同约束。

### 3.2 Market Cache v3

修正：

```text
reported_volume = provider_volume × factor × 100
amount_cny = provider_amount × 1000
participation_volume = lagged 20-day median(reported_volume)
```

保持不变：

- current open 执行；
- previous close 涨跌停基准；
- signal lag=1；
- 无 valuation bfill；
- stale valuation 20 个交易日；
- board-aware lot；
- ST、盘前停牌和 terminal event capability blockers。

cache key 必须加入单位配置与 Data Source Audit V2 artifact ID。

### 3.3 Canary 门禁

先运行：

- 单股固定 fixture：`SZ000001 / 2025-01-02`；
- 150 股审计样本的 Community/BaoStock 单位对账；
- split_001、10 日、200 股 market cache canary；
- corrected execution canary。

canary 必须证明：

```text
volume unit match >= 99.99%
amount unit match >= 99.99%
no future market field
cash non-negative
accounting conservation
dynamic lot valid
unknown execution difference = 0
```

canary 未通过不得全量运行。

### 3.4 最小全量重发

顺序固定：

```text
unit fixtures/tests
→ Market Cache v3 canary
→ Market Cache v3 full
→ bugfix_research_freeze_v1_2
→ corrected execution canary
→ corrected execution full
→ readiness/governance
```

不得重发 instrument state 或 score，因为二者业务载荷未受单位错误影响。

### 3.5 归因

新旧对账至少输出：

- participation volume ×100 是否逐 key 成立；
- order/fill/partial/rejected count delta；
- turnover、费用、现金和 NAV delta；
- 因容量约束变化新增的成交；
- unit semantics 以外的差异必须为 0；
- `SZ302132` 单证券影响；
- 旧/新 artifact ID 和 cache key。

历史 test 已经观察，新执行仍只能称：

```text
post-observation corrected historical evidence
non-authoritative OOS
unbiased_final_estimate = false
```

## 4. Definition of Done

```text
community_volume_unit_fixture_pass = true
community_amount_unit_fixture_pass = true
market_cache_volume_unit_ready = true
market_cache_amount_unit_ready = true
execution_unit_semantics_ready = true
market_cache_v3_ready = true
unknown_unit_difference_count = 0
unknown_execution_difference_count = 0
score_business_payload_unchanged = true
Matrix v4 artifact ID unchanged
selection artifact ID unchanged
```

同时必须保持：

```text
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
model_entry_hard_stop_active = true
historical_oos_comparison_complete = false
production_model_selected = false
unbiased_final_estimate = false
```

## 5. 后续边界

完成 V1.2 后，不得因此进入模型阶段。下一项只能是 Historical Instrument State v2 的独立方案：

- 证明 ST/tradestatus 的 before-open 可用性；
- 建立权威停复牌与 terminal event 证据；
- AKShare Eastmoney 端点继续仅作为不稳定审计源，不成为生产依赖；
- 在 authoritative state 未解决前，PR #5A 继续暂停。
