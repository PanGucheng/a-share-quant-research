# Historical Instrument State V2 计划

> 状态：正式实施基线
> 当前分支：`fix/historical-instrument-state-v2`
> 前置：PR #9 / Execution Unit Semantics Correction V1.2 已完成
> 硬边界：不进入 PR #5A，不训练模型，不修改 Matrix v4、Labels v2、IC、FDR、stability、clustering、allowlist、weights 或冻结 score。

## 1. 目标与当前结论

本阶段只解决 corrected historical execution 尚未具备的三类 PIT 状态：

```text
historical ST / *ST state
full-day suspension / resumption state
held-instrument terminal event and disposition
```

Data Source Audit V2 已证明：

- BaoStock `isST` 与 `tradestatus` 可定位候选状态，但未证明 before-open 发布语义；
- AKShare Eastmoney 在当前环境仅 3/150 成功，不能成为依赖；
- Community 缺行情可以观察“没有行情”，但不能单独区分全天停牌、数据缺失、生命周期结束或终止上市；
- SSE/SZSE 的停复牌查询和交易所/发行人公告是最高优先级公开证据；
- 巨潮公告可提供风险警示、停牌、终止上市的生效日期和发布时间，但仍须逐条校验可用时间。

官方依据与检索入口：

- 中国证监会《上市公司股票停复牌规则》：
  `https://www.csrc.gov.cn/csrc/c101954/c1719627/content.shtml`
- 上交所停复牌信息：
  `https://www.sse.com.cn/disclosure/dealinstruc/suspension/`
- 深交所停复牌公告：
  `https://www.szse.cn/disclosure/notice/temp/index_1.html`
- 巨潮全文检索：
  `https://www.cninfo.com.cn/new/fulltextSearch`

这些入口证明存在公开事件证据，但不自动证明第三方日线字段在历史时点可用。

## 2. P0：撤销“生命周期结束即按最后价卖出”

V1.2 corrected execution 中共有 8 笔：

```text
terminal_event_settlement_approximation
```

只涉及：

```text
SZ000413  4 fills
SZ002308  2 fills
SH600811  2 fills
```

当前逻辑在 provider lifecycle 结束后的首个会计日：

```text
execution_price = last valid valuation price
volume = 1e15
can_sell = true
```

这不是权威的市场成交或公司行动处置。初步官方核对反而表明：

- SZ000413 自 2024-08-15 开市起停牌；
- SZ002308 自 2024-08-23 开市起停牌；
- SH600811 的连续 20 个交易日低于 1 元区间止于 2025-04-14，随后停止交易，终止上市决定到 2025-04-28 才公告。

所以必须拆分：

```text
trading_state:
  suspension => cannot trade

valuation_state:
  carry last valid close under explicit stale policy

disposition_state:
  cash payout / delisting-board transfer / write-down / other
  only after authoritative event evidence
```

规则：

```text
lifecycle end != executable liquidation
suspension date => can_buy=false AND can_sell=false
unknown disposition => no synthetic fill
zero-price liquidation => forbidden
last-price liquidation => forbidden
```

V1.2 的 8 笔成交继续作为已披露的 non-authoritative approximation，不直接原地改写。

## 3. Source Tier 与权威边界

### Tier 0：权威事件源

```text
SSE / SZSE / BSE structured suspension records
SSE / SZSE / BSE exchange notices
issuer announcements hosted by exchange or CNInfo
```

可用于最终状态的必要条件：

- 原始响应或文档保存；
- source URL、query、retrieval time、SHA256 完整；
- 证券代码与公告主体一致；
- effective date 明确；
- publication time/date 支持 before-open 判定；
- 解析规则和人工复核状态可追溯。

### Tier 1：候选定位源

```text
BaoStock isST
BaoStock tradestatus
```

用途：

- 找出 ST 边界和 non-trading 日期；
- 与 Tier 0 事件逐条对账；
- 在 full-scope 中作为 completeness cross-check。

禁止：

```text
BaoStock field name => authoritative PIT
```

### Tier 2：市场观察源

```text
Community OHLCVA missingness
Community lifecycle interval
```

只可证明观测状态，不能单独证明原因。

### Tier 3：不稳定或人工辅助源

```text
AKShare Eastmoney
果仁人工导出
新闻或搜索结果
```

只作发现和交叉验证，不能单独授权 execution state。

## 4. 严格时间语义

统一时区：

```text
Asia/Shanghai
```

保守的 before-open 截止：

```text
09:00:00
```

每条事件必须包含：

```text
effective_date
published_at
available_at
available_phase
```

判定规则：

1. `published_at < effective_date 00:00`：可判为前一日已知；
2. `published_at <= effective_date 09:00`：可判为当日 before-open 已知；
3. 只有发布日期且 `publication_date < effective_date`：可判为 before-open；
4. 只有发布日期且 `publication_date == effective_date`：必须为 `unknown`；
5. 抓取时间不等于历史可用时间；
6. PDF 文内日期不等于网站发布时间；
7. `unknown` 不得映射为 `before_open`。

盘中临停单独标为：

```text
suspension_type = intraday
```

日频开盘执行不把盘中临停误当作全天开盘不可交易，除非公告明确覆盖开盘。

## 5. 数据模型

### 5.1 Raw evidence receipt

```text
source_id
source_tier
source_url
query_parameters
retrieved_at
http_or_api_status
content_type
raw_snapshot_path
raw_snapshot_sha256
parser_version
```

### 5.2 Normalized state event

```text
instrument
state_type
state_value
effective_from
effective_to
published_at
available_at
available_phase
source_id
source_tier
evidence_id
confidence
review_status
reason_code
```

`state_type` 至少包括：

```text
st
suspension
resumption
listing_termination
asset_disposition
```

### 5.3 Daily state

```text
datetime
instrument
st_flag
suspended_full_day
can_buy
can_sell
price_limit_rule_id
state_available_at
state_evidence_id
state_authority_status
terminal_disposition_status
```

禁止把 `listing_termination` 自动翻译成已变现现金。

## 6. 影响范围冻结

不做无边界全市场爬取。范围分为：

### A. Decision scope

所有进入冻结 score、目标持仓、订单或拒单决策的 `(date, instrument)`。

### B. Valuation scope

所有在任一会计日实际持有的 `(date, instrument)`。

### C. State-boundary scope

Data Source Audit V2 中：

- 13 只有 ST 观测的股票；
- 30 只有 non-trading 观测的股票；
- 所有 `isST` transition ±5 trading days；
- 所有 `tradestatus` transition ±5 trading days。

### D. Terminal scope

必须完整覆盖：

```text
SZ000413
SZ002308
SH600811
```

以及未来 inventory 扫描发现的其他“曾持仓且 lifecycle termination”证券。

Scope manifest 必须绑定：

```text
score SHA
Market Cache v3 artifact ID
V1.2 execution artifact ID
Universe v2 artifact ID
date range
instrument/date key hashes
```

## 7. 实施阶段

### Phase 0：保持机器 hard-stop

本阶段开始到结束始终保持：

```text
historical_instrument_state_v2_ready = false
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
model_entry_hard_stop_active = true
```

### Phase 1：Scope Freeze 与现有近似审计

输出：

```text
outputs/historical_instrument_state_v2/scope/
  scope_manifest.csv
  terminal_approximation_inventory.csv
  state_boundary_candidates.csv
  artifact_manifest.json
  contract_status.csv
  scope_report.md
```

必须先明确：

- 8 笔 terminal approximation 的证券、日期、数量、金额；
- 若禁止这些成交，现金、持仓和估值从哪一天开始分叉；
- ST / non-trading canary 的边界数量；
- 所有输入哈希。

### Phase 2：Evidence Schema 与 fail-closed 单元测试

测试至少覆盖：

- 同日只有发布日期且无时间 => `available_phase=unknown`；
- 前一日公告 => before-open；
- 抓取时间不能回填为 published time；
- intraday halt 不等于 full-day suspension；
- suspension 不产生 synthetic liquidation；
- listing termination 不产生 cash disposition；
- source tier 1 不能单独标 authoritative；
- raw snapshot hash 变化使 cache key 失效；
- conflicting Tier 0 events => blocked；
- unknown state => authoritative readiness blocked。

### Phase 3：小样本官方 Canary

最低样本：

```text
ST start/remove boundaries          >= 10 events
full-day suspension/resumption      >= 10 events
intraday suspension controls        >= 3 events
terminal scope                       3/3 instruments
```

每个事件保存 Tier 0 原始证据和解析结果。Canary 只验证 schema、时间语义和 source hierarchy；不得直接改执行链。

### Phase 4：候选源对账

比较：

```text
BaoStock isST       vs Tier 0 ST events
BaoStock tradestatus vs Tier 0 suspension events
Community missingness vs Tier 0 suspension events
```

输出：

```text
boundary exact-match rate
one-day lead/lag inventory
false positive / false negative
before-open provable rate
unknown rate
```

如果 candidate source 与官方事件发生一日偏移，不允许通过任意 shift 自动“修正”；必须按公告 effective date 归因。

### Phase 5：Full Scope 决策

只有 canary 通过后，才决定是否执行 full-scope 下载。

```text
Decision A:
Tier 0 coverage complete
before-open semantics complete
unknown/conflict = 0
→ materialize Instrument State v2

Decision B:
candidate source useful but Tier 0 coverage incomplete
→ retain audit layer, authoritative readiness remains false

Decision C:
source semantics unreliable or irreproducible
→ reject source and document gap
```

任何 full-scope 操作前都必须生成 review bundle；本次持续会话有计算授权，但 source URL、parser、scope、commit 或 config 变化会使 bundle 失效。

### Phase 6：Instrument State v2

只有 Decision A 才发布：

```text
outputs/instrument_state_v2/current/
```

并要求：

```text
decision_scope_coverage = 1
valuation_scope_coverage = 1
before_open_unknown_count = 0
authoritative_conflict_count = 0
synthetic_terminal_liquidation_count = 0
```

### Phase 7：Execution 影响重发

只有 Instrument State v2 critical contracts 全部通过后，才：

```text
Market Cache v4 canary
→ corrected freeze v1_3
→ execution canary
→ full corrected historical execution
→ old/new attribution
```

研究 score 必须保持不变。新历史结果仍然是：

```text
post_observation_bugfix
historical_test_already_observed = true
unbiased_final_estimate = false
```

即使 execution state 变得权威，也不自动授权模型或生产策略选择。

## 8. Contracts

关键 contract：

```text
scope_lineage_complete
score_payload_unchanged
terminal_approximation_inventory_complete
raw_evidence_hashes_valid
source_tier_valid
event_schema_valid
effective_interval_valid
published_at_not_inferred
before_open_semantics_valid
intraday_vs_full_day_distinguished
st_boundary_consistent
suspension_boundary_consistent
terminal_disposition_explicit
no_synthetic_terminal_liquidation
decision_scope_coverage
valuation_scope_coverage
unknown_authoritative_state_count
authoritative_conflict_count
output_hashes_valid
```

任何 critical contract 不通过：

```text
artifact_status != pass
historical_instrument_state_v2_ready = false
```

Capability blocker 可以诚实保留，但不得被转换成 authoritative readiness。

## 9. Definition of Done

### 本轮 Scope/Canary DoD

```text
scope_frozen = true
terminal_approximation_inventory_complete = true
evidence_schema_ready = true
before_open_fail_closed_tests_pass = true
official_canary_complete = true
candidate_source_reconciliation_complete = true
source_decision_recorded = true
```

### Instrument State v2 最终 DoD

```text
historical_instrument_state_v2_ready = true
full_day_suspension_ready = true
historical_st_ready = true
terminal_disposition_ready = true
decision_scope_coverage = 1
valuation_scope_coverage = 1
unknown_authoritative_state_count = 0
authoritative_conflict_count = 0
synthetic_terminal_liquidation_count = 0
```

仍保持：

```text
historical_test_already_observed = true
unbiased_final_estimate = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
model_entry_hard_stop_active = true
production_model_selected = false
```

## 10. 停止条件

以下任一情况只阻塞对应 readiness，不扩大任务：

- 官方源无法稳定重现历史查询；
- 公告发布时间无法证明；
- Tier 0 与候选源存在无法解释的冲突；
- 终止上市后资产处置没有权威现金/转板证据；
- full-scope 需要未经审阅的大规模网页爬取；
- 任何修改会触及 Matrix v4 或研究选择。

这时应提交 Decision B/C 证据并保持 hard-stop，而不是猜测、降门槛或进入 PR #5A。
