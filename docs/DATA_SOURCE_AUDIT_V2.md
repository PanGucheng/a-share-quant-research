# Data Source Audit V2

> 状态：已完成
> 决策：Decision B
> 边界：保留 Community 作为冻结研究基准；不替换 provider，不重算 Matrix v4，不解锁模型训练。

## 1. 样本与数据源

审计冻结 150 只股票，覆盖主板 67、创业板 53、科创板 30，日期为 2024-08-01 至 2026-02-04。原始下载、标准化数据、查询参数、时间戳、状态与哈希均保存在：

```text
outputs/data_source_audit_v2/current/
```

数据量与端点结果：

```text
Community              52,224 rows
BaoStock               52,593 rows / 150 of 150 instruments
AKShare Eastmoney       1,104 rows / 3 of 150 instruments
AKShare failures          147 ProxyError
```

AKShare Eastmoney 在当前网络代理环境中不稳定，只保留为审计证据，不作为生产依赖。BaoStock 具备完整样本覆盖，但字段名称本身不能证明 PIT 可用时间。

## 2. 基础行情与单位结论

Community 与 BaoStock 有 52,224 个共同 key。完成单位还原后：

```text
close tolerance match rate   = 1.0
volume tolerance match rate  = 1.0
amount tolerance match rate  = 1.0
max close relative diff      = 1.520178e-07
```

冻结语义为：

```text
raw_price     = provider_price / factor
volume_shares = provider_volume × factor × 100
amount_cny    = provider_amount × 1000
raw_vwap      = amount_cny / volume_shares
```

VWAP 重建最大误差约 `1.53e-05` CNY。核心 raw OHLC 未发现系统性错误；发现的问题位于 derived/unit semantics，而不是 Matrix v4 的价格输入。因此选择 Decision B，不启动 Matrix v5。

## 3. 复权与公司事件

审计列出了 factor 变化候选及事件窗口，但当前没有用官方公告对所有候选完成机器解析。现有证据支持 Community 与外部源的数值复权结果高度一致，但不足以把 adjustment event 的公告时点声明为权威 PIT。

结论：

- 不因当前 canary 重算 Matrix v4；
- factor-change candidates 保留在 `adjustment_event_audit.csv`；
- 在用于权威 historical state 前，需要针对真实持仓相关事件做 SSE/SZSE/BSE/巨潮专项核验；
- 不建设无边界的全市场网页爬虫。

## 4. Historical ST 与 tradability

样本观测到 13 只有历史 ST 状态的股票、30 只有 non-trading 记录的股票。BaoStock `isST` 边界和 `tradestatus` 可作为候选来源，但：

```text
available_before_open = unknown
usable_as_historical_execution_state = false
```

原因是当前 receipt 证明了“返回什么”，没有证明每个字段在对应交易日开盘前已公开可得。AKShare 覆盖不足，也不能补足该证据。

因此：

- BaoStock 可用于生成候选边界和抽样清单；
- 不能仅凭字段名把 `isST` / `tradestatus` 提升为 authoritative PIT；
- 全天停牌、盘中临停、长期停牌、行情缺失和生命周期结束必须分开建模；
- `available_before_open` 无法证明时必须为 `unknown`，执行链 fail closed。

## 5. 决策与影响

最终决策：

```text
Decision B:
Community core raw OHLC reliable
derived unit semantics required correction
Matrix v4 remains frozen
Historical Instrument State V2 remains blocked
```

单位问题已由 Execution Unit Semantics Correction V1.2 修正：

- Market Cache v2 永久 superseded；
- Market Cache v3 将 volume 转换为 shares、amount 转换为 CNY；
- corrected execution 已重新物化；
- 研究选择和 score 业务载荷未变化。

仍未解决：

- 历史 ST 的 before-open 权威性；
- 停复牌状态及其发布时间；
- 真实每日涨跌停价的权威 PIT 源；
- 实际持仓相关 terminal event 的处置证据。

在这些能力关闭前：

```text
historical_instrument_state_v2_ready = false
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
model_entry_hard_stop_active = true
```
