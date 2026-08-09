# Accuracy Correction V1.1 与 Data Source Audit V2 实施计划

> ARCHIVED / CLOSED：实施已完成，仅保留为历史研究证据。

> 文档状态：正式实施基线  
> 制定日期：2026-07-24  
> 基线提交：`a7e6e6c453ef0e3ce989885c090b0829b268af16`  
> 固定边界：不进入 PR #5A，不训练模型，不改变因子选择，不重算 Matrix v4

> 2026-07-24 实施回执：Phase A 已完成，当前链 22 个 artifact / 61 条 edge 的传递校验问题数为 0；score 1,471,764 行 runtime SHA 保持 `beb4e4ad...` 不变，Universe 已闭合到 v2，`SZ302132` 的 124 行 unknown board 已清零。Phase B 已完成 150 股 canary：Community 与 BaoStock 在 52,224 个共同 key 上 price/volume/amount 容差匹配率均为 100%，形成 Decision B；AKShare Eastmoney 仅 3/150 成功、147 次为 ProxyError。审计确认 Market Cache v2 漏乘成交量整手单位 `×100`，故 execution/market-cache readiness 已立即撤回，下一阶段改为 `EXECUTION_UNIT_SEMANTICS_CORRECTION_V1_2_PLAN.md`。

## 1. 阶段目标与不可突破边界

本阶段连续完成两个任务：

```text
Phase A — Accuracy Correction V1.1: Lineage & Gate Closure
    ↓ Phase A DoD 全部通过
Phase B — Data Source Audit V2 Canary
    ↓ 只形成数据源决策，不替换生产 provider
STOP before PR #5A
```

固定禁止事项：

- 不实现或训练 Ridge、Elastic Net、LightGBM 或其他模型；
- 不修改 FDR、stability、clustering、allowlist、weights 或 score policy；
- 不读取 historical outer-test 结果来重新选因子或调参；
- 不覆盖 Community Qlib provider；
- 不重算 669 因子、Matrix v4、Labels v2、Pairwise IC、FDR 或选择链；
- 不把 corrected historical OOS 声称为 authoritative 或 unbiased；
- 不因数据源名称、字段名或第三方文档声称而默认字段具有 PIT 权威性。

任何看似需要越过上述边界的问题只能形成后续计划和 blocker，不在本阶段自动扩大范围。

## 2. 实现前核验结论

### 2.1 Corrected score lineage 的真实根因

`split_transparent_score_v2/current` 当前为：

```text
artifact_status = pass
lineage_status = inconsistent
universe_artifact_id = null
```

冲突来自多个层次：

1. Matrix v4 正确绑定 `Universe v2`；
2. 历史 `purged_walk_forward_v1` 同时绑定旧 Matrix/Labels/Universe v1，虽然 score 实际只消费其日期切分；
3. `transparent_score_policy_v1` 同时消费 Matrix v4 与旧 split manifest，继承出 Universe 冲突；
4. `selection_mutation_contract_v2` 同时包含 v2 研究链、旧 date split 和旧 raw snapshot，继承出 Universe/factor-catalog 冲突；
5. corrected score 又直接消费上述 inconsistent parents 和 inconsistent canary；
6. 当前 writer 即使调用者显式传入 `lineage_status="complete"`，仍会发现字段冲突并改为 inconsistent；但下游 preflight 只检查 output hash 和 artifact status，未要求 parent lineage complete。

因此不能通过给 score 手工填入 Universe v2 解决。修复必须同时完成：

- 明确每类 artifact 对哪些 lineage 维度具有权威性；
- 日期切分只传播 split identity，不传播 universe/factor identity；
- raw snapshot 传播 source snapshot identity，不替代 research universe；
- policy/mutation 重新发布时必须由权威 v2 parent 推导 identity；
- corrected score 的所有直接父 artifact 对其消费维度均 complete；
- transitive validator 能发现 inconsistent parent 和 lineage washing。

### 2.2 Unknown board 的真实范围

当前 124 行 unknown board 全部为：

```text
instrument = SZ302132
outer_split_id = split_003
date = 2025-08-05 ... 2026-02-04
```

这是合法 A 股“中航成飞”。公司原代码 `300114`，于 2025-02-17 变更为 `302132`，仍属于创业板。当前 board inference 仅识别 `300`、`301`，漏掉 `302` 号段。

处理原则：

- 将 `SZ302xxx` 识别为创业板，不得映射为主板；
- 输出逐行 unknown-board 审计和证券代码变更证据；
- 保留 code-change/corporate-identity 风险说明：本次只修复 board/lot/limit 分类，不在研究矩阵中合并 `300114` 与 `302132` 的历史特征；
- 修复后要求 unknown board=0、lot rule 全部 resolved；
- 若未来出现无法证明的其他 code range，继续 fail closed，不使用默认 board。

### 2.3 外部数据源的预期能力边界

- BaoStock 日线接口公开字段包含 OHLC、preclose、volume、amount、adjustflag、tradestatus、isST，但字段存在不等于其可作为“开盘前可知的历史权威状态”；必须逐事件核验。
- AKShare 当前版本提供东方财富 A 股历史行情和按日期停复牌接口，但 AKShare 官方明确说明其接口持续变化，公开网站上游也可能限流、改变或移除；只能作为有 snapshot/hash 的验证源。
- `SZ302132` 的证券代码变更由深交所公告支持，说明 board inference 不能仅靠旧静态号段表。
- 果仁只登记为人工导出交叉验证源，不开发网页爬虫。
- 交易所和巨潮仅用于关键事件样本确认，不在本阶段构建全市场公告爬虫。

参考入口：

- BaoStock：`https://www.baostock.com/`
- BaoStock 复权说明：`https://www.baostock.com/helpdocs/pdf/BaoStock复权因子简介.pdf`
- AKShare 官方文档：`https://akshare.akfamily.xyz/data/stock/stock.html`
- AKShare 官方仓库：`https://github.com/akfamily/akshare`
- 深交所 `302132` 公告证据：`https://disc.static.szse.cn/`

## 3. Phase A — Lineage & Gate Closure

### A0. 分支、硬停止与审计快照

从最新 main 创建：

```text
fix/accuracy-correction-v1-1-lineage-gates
```

首个业务提交保持：

```text
model_entry_hard_stop_active = true
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
historical_test_already_observed = true
unbiased_final_estimate = false
```

先输出：

```text
outputs/accuracy_correction_v1_1/current/
    lineage_conflict_inventory.csv
    parent_gate_inventory.csv
    unknown_board_audit.csv
    contract_status.csv
    readiness_summary.csv
    audit_report.md
```

### A1. 定义维度化 lineage 语义

新增版本化 registry，例如：

```text
configs/artifact_lineage_semantics_v1.yaml
```

至少定义四个 lineage 维度：

```text
universe
split
factor_catalog
factor_frame
```

并定义 stage authority：

- universe stage：权威传播 universe；
- Matrix/Labels/IC/selection stage：传播其真实消费的 research lineage；
- calendar/date split：只传播 split，不能把旧 universe 注入新研究链；
- raw snapshot：传播 source artifact ID，但不作为 research universe authority；
- score policy：绑定 Matrix v4、development split、weights 和 policy payload；
- mutation proof：绑定被证明不变的 v2 research payload，不把旧 supporting receipt 的 lineage 当作当前 authority；
- score：必须绑定唯一 Universe v2、Matrix v4 factor frame、split definition、policy 与 mutation proof。

registry 不是豁免清单。每个被忽略的 lineage 维度必须有：

```text
stage_id
field
semantic_reason
supporting_output_hash
replacement_authority_artifact_id
```

未知 stage 或未知字段一律 fail closed。

### A2. 通用 artifact publication gate

在 `research_validation.lineage` 中新增统一门禁：

```text
critical contract status != pass
    => requested artifact_status=pass 被降为 blocked

direct parent artifact_status != pass
    => downstream blocked

direct parent effective lineage incomplete/inconsistent
    => downstream blocked

direct parent code_dirty = true
    => downstream blocked

direct parent output freshness invalid
    => downstream blocked
```

实现要求：

- writer 自动发现发布文件中的 `contract_status.csv` 或显式 contract paths；
- `severity=critical` 的非 pass 行必须进入 blocked reason；
- severity 缺失时按 critical 处理，不能默认忽略；
- capability blocker 不自动阻止“非权威操作证据”，但必须阻止对应 authoritative readiness；
- blocked artifact 必须有非空 blocked reason；
- parent gate 结果写入 manifest 或独立 machine-readable receipt；
- 不能由调用脚本通过再次传入 `lineage_status="complete"` 覆盖 gate 结果。

### A3. Direct-parent 与 transitive validator

新增通用函数和 validator：

```text
validate_direct_parent_gate(...)
validate_transitive_lineage(...)
scripts/validate_accuracy_correction_v1_1.py
```

transitive walk 要求：

- 从当前 score、instrument state、market cache、freeze、execution 向上遍历；
- 每个 input artifact ID 必须能在 repository artifact index 中唯一解析；
- 检查 output hash、artifact status、code dirty、effective lineage；
- 检查每条 lineage edge 的字段兼容性；
- 检查 child 不得从多个冲突 authority 中洗出 complete；
- legacy/reference-only evidence 必须显式标记，不能成为 authoritative child 的直接 authority。

### A4. 精确 metadata/revalidation 重发

不重跑因子或研究数值。只对因 lineage 语义错误而受影响的 compact artifacts 做确定性 revalidation/reissue：

1. 为 date assignments 创建“日期切分语义 receipt”，证明其 business payload hash 与历史 split 完全一致，只传播 split identity；
2. 对 score policy 做 payload/hash/contract revalidation，不改变任何阈值；
3. 对 mutation proof 做 payload/hash/contract revalidation，不重新选择因子；
4. canary 使用上述新 direct parents 重发；
5. full corrected score 使用上述新 direct parents 重发；
6. 验证 score runtime 的 key、row、value SHA 与修复前完全一致。

如果任何 business payload 改变，立即阻塞并审计；不得把 metadata closure 变成静默重算。

### A5. Unknown-board 审计与修复

新增：

```text
unknown_board_audit.csv
instrument_code_change_evidence.csv
```

修复 `infer_board`：

```text
SZ300 / SZ301 / SZ302 -> chinext
```

测试覆盖：

- `SZ302132 -> chinext`；
- B 股、ETF、基金、债券和未知号段仍为 unknown；
- unknown 不得默认 main；
- unknown 进入 lot/limit rule 时必须抛错或 blocked；
- code-change 证券保留独立代码身份，不在本阶段拼接特征历史。

### A6. Instrument-state 发布判定

`build_instrument_state_v1.py` 必须由 contract 决定 artifact status：

```text
critical pass all
    => artifact_status=pass
otherwise
    => artifact_status=blocked
```

修复 `SZ302132` 后：

```text
unknown_board_row_count = 0
lot_rule_resolved = pass
```

ST、盘前停牌和 terminal event 缺失仍为 capability blockers，不把 operational artifact 错误降为研究计算失败，但 authoritative readiness 必须保持 false。

### A7. 最小 downstream 重发

严格按以下顺序：

```text
lineage semantics / gate unit tests
→ lineage closure receipts
→ corrected score canary
→ corrected score full（必须数值无损）
→ instrument state canary/full
→ market cache canary/full
→ bugfix freeze
→ corrected execution canary/full
→ execution/readiness/governance receipts
```

不触碰：

```text
Matrix v4
Labels v2
Pairwise IC v2
FDR
stability
clustering
allowlist
weights
```

只有 board/lot 修复可能改变 corrected OOS：`SZ302132` 原先因 lot unresolved 被拒绝，修复后可能产生新订单或成交。必须输出 old/new execution delta 和单证券 attribution，不得宣称研究信号变化。

### Phase A 测试

至少新增：

- critical blocked contract 不能发布 pass artifact；
- capability blocked 不得误解锁 authoritative readiness；
- inconsistent parent 不能生成 complete child；
- dirty parent 不能生成 pass child；
- unknown parent artifact ID fail closed；
- date-only lineage 不传播 Universe；
- conflicting authoritative Universe IDs fail closed；
- `SZ302132` 精确识别为创业板；
- unknown board 不映射 main；
- corrected score 修复前后 key/value hash 一致；
- transitive lineage mutation 能被发现。

### Phase A DoD

```text
corrected_score_lineage_complete = true
corrected_score_universe_artifact_id = authoritative Universe v2
corrected_score_business_payload_unchanged = true
unknown_board_row_count = 0
instrument_state_critical_contracts_pass = true
all_consumed_direct_parent_lineage_complete = true
transitive_lineage_validation_ready = true
execution_semantics_accuracy_ready = true
market_cache_v2_ready = true
future_market_field_count = 0
```

同时保持：

```text
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
model_entry_hard_stop_active = true
historical_test_already_observed = true
unbiased_final_estimate = false
```

Phase A 形成独立提交和审计报告，通过后才能开始 Phase B。

## 4. Phase B — Data Source Audit V2 Canary

### B0. 性质与数据隔离

本阶段只做下载、标准化、对账和决策。目录分离：

```text
outputs/data_source_audit_v2/current/
    raw/
        baostock/
        akshare/
        official_samples/
    normalized/
    comparisons/
    artifact_manifest.json
    source_query_receipts.csv
    raw_snapshot_manifest.csv
    sample_manifest.csv
    contract_status.csv
    readiness_summary.csv
    data_source_audit_report.md
```

原始响应不可被标准化文件覆盖。每次 query 记录：

```text
source
library_version
endpoint
query_parameters
retrieval_time_utc
http_or_api_status
row_count
raw_snapshot_sha256
normalizer_version
```

网络失败、限流或 endpoint 变化属于结果，不用空表伪装成功。

### B1. Canary 样本冻结

目标去重后 100–200 只，推荐约 150：

- 60 只按 Universe v2 分层随机抽样，固定 seed 和 sample hash；
- 20 只覆盖主板/创业板/科创板及代码变更；
- 25 只覆盖 ST、`*ST`、开始和撤销边界；
- 20 只覆盖全天/长期停牌和复牌；
- 15 只覆盖 IPO 或 lifecycle termination；
- 20 只覆盖现金分红、送转、配股等复权事件。

允许重叠。每个 purposive sample 必须有 selection reason 和事件证据；不能只选择接口容易返回的股票。

### B2. Source adapters

建立只读 audit adapters：

```text
data_source_audit/
    schemas.py
    normalizers.py
    alignment.py
    missing_spans.py
    st_boundaries.py
    tradability.py
    snapshot.py
    sources/
        community.py
        baostock.py
        akshare.py
```

不把 BaoStock/AKShare 加入生产 provider。若 BaoStock 仅为 canary 安装，则记录版本和环境，不强制成为核心仓库运行依赖；validator 对缺少可选依赖应返回明确 unavailable，而不是导入崩溃。

### B3. Canonical schema 与单位

统一为：

```text
instrument
date
price_raw_open/high/low/close/preclose
volume_shares
amount_cny
is_trading
is_st
suspension_type
available_before_open
adjustment_mode
source
source_row_id
```

单位规则必须由受控 fixture 验证：

- volume 手/股换算；
- amount 元/千元换算；
- 百分比与小数换算；
- raw/qfq/hfq 不得混在同一 comparison family。

无法证明单位时标记 unknown，不自动选择最接近的缩放倍数。

### B4. OHLCVA 对账

按 source、instrument、date 对齐，输出：

```text
exact_match_rate
tolerance_match_rate
missing_rows
extra_rows
continuous_missing_spans
unit_normalized_difference
```

容差在运行前冻结，至少分别处理价格、volume、amount。missing-span 报告必须区分 source 缺失和全部 source 均无交易。

### B5. Community 字段语义

审计：

```text
volume
amount
vwap
factor
adjclose
change
```

重点验证：

- `amount / volume_shares` 是否能重建 raw VWAP；
- provider volume 的原始单位；
- factor 的方向、基准日和生效日；
- adjusted close 与 factor 的关系；
- change 来自 raw 还是 adjusted price；
- derived field 是否可能读取当日收盘后信息。

只形成重建建议，不重建 provider。

### B6. 复权事件 Canary

对现金分红、送股、转增、配股和明显除权事件执行事件窗检查：

```text
event_date ± 5 trading days
```

比较 raw/qfq/hfq 或等价 adjustment semantics，检查：

- 因子是否在正确日期生效；
- 除权日是否产生不合理跳变；
- 是否有未来 corporate action 提前写入历史；
- code change/资产重组是否被误当普通复权。

发现系统性错误只标 P0 和 Decision C candidate，不自动 Matrix v5。

### B7. Historical ST

BaoStock `isST` 只作为候选标签。对 ST 开始/撤销事件窗：

```text
effective_date ± 5 trading days
```

与 AKShare 可用信息、人工导出和官方公告抽样交叉验证，输出：

```text
usable_as_historical_execution_state
verified_with_caveats
not_reliable
```

必须单独验证 `available_before_open`；事件日之后才发布的标签不能倒填为开盘前状态。

### B8. Historical tradability

对 BaoStock `tradestatus`、AKShare 停复牌表和 Community OHLCVA 缺失做三方审计。状态模型：

```text
instrument
date
is_trading
suspension_type
available_before_open
source
confidence
evidence
```

至少区分：

```text
full_day_suspension
intraday_halt
long_suspension
source_missing
lifecycle_end
unknown
```

`available_before_open` 无证据时必须为 unknown。

### B9. 涨跌停与 terminal event

- 检查免费源是否稳定提供真实 daily up/down limit；
- 真实限价只有在字段时点可靠时才能作为未来 primary candidate；
- 当前规则引擎保留为 cross-check；
- terminal-event 只扫描 corrected OOS 中实际持仓且 lifecycle termination 的证券；
- 输出 holding period、last trading day、lifecycle end、当前 approximation、潜在事件类型和最大 NAV 影响范围；
- 需要公告解析的仅列入人工/AI 专项队列。

### B10. Phase B contracts

至少覆盖：

- raw snapshot hash；
- source query receipt 完整；
- unit normalization fixtures；
- duplicate key；
- row alignment；
- missing-span detection；
- ST boundary window；
- tradability unknown available-before-open fail closed；
- adjustment event timing；
- endpoint unavailable 明确披露；
- provider 未被修改；
- Matrix v4 hash 未变化；
- factor-selection artifacts hash 未变化。

### B11. 决策规则

只允许三类结论：

```text
Decision A
Community core OHLC/adjustment reliable
→ 保留 Matrix v4，只规划 historical instrument state v2

Decision B
derived fields 有问题但 core raw OHLC 可靠
→ 后续修 derived fields，不重算全部因子

Decision C
core OHLC 或 adjustment 存在系统性错误
→ 仅提出 Canonical Data Store → new provider → Matrix v5 计划
```

Decision C 也不得在本阶段自动执行全量重建。

## 5. 提交与验证顺序

建议拆分：

1. document Accuracy Correction V1.1 and Data Source Audit V2 baseline
2. add fail-closed contract and parent-lineage gates
3. close corrected score lineage without business-payload changes
4. resolve SZ302132 board semantics and instrument-state contracts
5. rematerialize minimal corrected execution chain and receipts
6. add data-source audit schemas, normalizers, fixtures and sample freeze
7. run BaoStock/AKShare/Community canary and publish source decision
8. finalize governance, validators and documentation

每个阶段运行 targeted tests；Phase A、Phase B 各自完成后运行完整 pytest 和所有相关 validators。长下载不得高并发轰击公开 endpoint，失败重试必须有限且有退避。

## 6. 最终停止状态

本计划全部完成后：

```text
accuracy_correction_v1_1_ready = true
data_source_audit_v2_ready = true 或 blocked_with_evidence
model_entry_hard_stop_active = true
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
historical_oos_comparison_complete = false
production_model_selected = false
unbiased_final_estimate = false
```

随后停止并提交：

- Cleanup 根因与修复；
- unknown-board 证券和处理；
- corrected OOS 数值变化；
- canary 样本；
- Community/BaoStock/AKShare 差异；
- ST/tradestatus 是否可用于 Instrument State v2；
- core OHLC/复权是否存在系统性问题；
- 是否需要 Matrix v5；
- 当前 readiness 和下一步建议。
