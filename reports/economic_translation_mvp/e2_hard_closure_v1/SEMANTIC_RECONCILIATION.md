# E2 离线语义闭环与消费边界

本轮基线 `main@2776029`。当前结论和数量以 [REPORT](REPORT.md)、[MATRIX](MATRIX.md) 和 [SEMANTIC_VERIFICATION.json](SEMANTIC_VERIFICATION.json) 为准；本文说明实际实现及限制，不另立策略计划。

输入只来自已经封存的 Quotes、States、Dividends。`scripts/reconcile_e2_semantics.py` 在每个 parquet 打开前核对分块 receipt、文件 hash、白名单和日期；进程禁用网络连接。输出单独位于 `outputs/economic_translation_mvp/e2_semantic_v1`，已有目录拒绝覆盖。逐股从首次候选日延续到 2023-12-29，不读取分数、收益或 2024+ 值。

## 行情、身份和状态

- `daily/<research ID>.parquet` 保留原 ID，另列 economic asset 与 dated execution-code reference。SH601313 与 SH601360 属于同一资产；2018-02-28 的代码参考沿用已有发行人/券商证据。旧代码有效报价只应用已证明的 volume /100、amount /1000 修正；离池后使用已采集的新代码原始报价，保留 source hash。该关系不是复杂换股或全部登记结算的认证。
- 两源均有效且一致才标记 `cross_source_agreed`。有效性包含有限正量价、OHLC 包络、amount/volume 的 VWAP 包络以及本地 factor。两源均有效但冲突时不选赢家，原始可用报价留空；一源有效则明确记录单源 overlay，不能冒充跨源证实。没有按异常比例小而删除证券。
- 日终 `tradestatus`/`isST` 被整理为 ordinary、ST、suspended、special_or_rule_conflict 或 unresolved。尾部失联单列 `terminal_candidate_gap`，不把供应商缺行推定为真实退市。
- 复用已有 board、dated_limit_rule、price_bounds。`provisional_lower/upper` 只是普通制度族的诊断限价：占位 IPO session=6 用于询问“若为普通日，其上下限是什么”，不是上市天数证据。IPO、重新上市和其他特殊日未认证，所有行 `ordinary_regime_certified=false`、`can_buy/sell_preopen=false`、`known_at=null`。不能把这张观察表直接传作已通过的盘前 execution state。
- 停牌日只能使用供应商当天明确给出的正有限 close 作带来源、带陈旧期的临时估值；不作为成交报价。没有以无限前填解释失联、重组或终止权利。

## 事件与账户桥

`event_source_versions.parquet` 保留全部原记录，`events.parquet` 以 economic asset / record_date / ex_date 聚合，保留每条源行的 hash:index。只从实施记录提取权益；非实施记录留在 provenance 中。字段不同不必然等于权益冲突：公告版本不同但现金、送股和结算条款一致的记录可以合并。

只有兼容的实施版本提供唯一非缺失值时才补证缺字段。不同非缺失现金/比例/到账日/上市日均保留为冲突，不按第一条、最后一条、平均数或价格反推选择。选用实施公告日期的最晚值作为保守可得日；登记日之后才公告的历史权利需要单独的登记与公告证据，不能直接套普通分红流程。

`resolved_gross_entitlement` 表示已有字段满足税前普通权益合同，**不表示公司行动全集完整或可以运行真实账户**。沿用计划的显式 `before_dividend_income_tax` 口径，适配器把 `cash_div_tax` 写入独立 gross 字段，禁止冒充 net。Qlib EventPosition 仍区分登记、应收、到账、未上市红股和可卖股；真实未知/冲突事件拒绝适配。合成手算覆盖除权前后账面守恒、应收不能下单、到账与上市时序。

逐事件另做 `(前一可用源 close - 每股税前现金)/(1+送转比例)` 与源除权参考价的核对。偏差超过 0.015 元列为需核查，并不根据偏差调整现金。非流通股/差异化分红、配股、其他参考价调整与供应商错误均可能导致偏差，需要事件证据区别。factor 的小幅变化只作诊断，不能当作配股/换股计数；该 factor 存在普通日数值抖动。

## 潜在持仓连续性

每个历史候选都视为可能持有，审计到窗口末端；不按真实模型选择持仓，也不宣称有人实际遭遇这些缺口。保留同资产的两个 research ID，账户入口继续禁止重复经济身份。未解释估值、未知状态、有效双源冲突、事件缺口、无事件的参考价重置都会标记 account gap。已取得登记权益的未决事件从登记日持续阻塞，后面恢复行情不抹掉权利问题。

`segments.parquet` 保留连续区间及内部断点；`terminal_candidates.csv` 保留所有尾部覆盖候选；`event_reference_bridges.parquet` 留下每次比对。account_gap 是数据连续性必要条件的失败标记：即使该标记为 false，也不表示盘前可交易、未观测事件不存在或未来账户可运行。任何失败日期足以使完整路径未通过；未模拟平仓、末价套现或归零。

仅按 ex_date 封存的分红接口不能证明无 ex-date 的配股、换股、终止权利或 2023 边界尚未除权的已登记义务全部齐全。这些数量未被可靠识别时必须为 unknown，而非零。后续只能针对具体缺口取得当时公告/结算证据；不能因此重跑已完成的三项采集，也不能读取 2024+ 结果补算。

## 独立验证和停止点

`scripts/verify_e2_semantics.py` 不导入生产 reconciliation 函数，独立检查全量输入/输出 hash、全部逐日索引、区间分割、状态拒绝、汇总计数、源版本完整分区、原 682 个不同内容重复组和报价抽样直接算术。独立验证另存 receipt，避免改写生产 receipt。代码和 hash 记录的是本轮封闭数据审计，不是 E3 冻结。

三项原采集及完成复核文件不变。首个 canary 因测试名单中的 SZ000033 不属于授权候选而在打开该股行情前拒绝；失败目录保留。修正名单后的六股 canary 完成，随后执行全量离线审计。未知数和失败证据不通过重建旧 receipt 消失。

最终停在 **E2 STILL BLOCKED**，等待人工审核；不运行 E1、固定 K 搜索、Monthly/Buffer、真实账户或收益指标，不选择 K/AUM/benchmark，不进入 E3/E4。

独立精度裁定另存 `precision_adjudication/daily_patches.parquet`，按 instrument/date 覆盖基础观察行时须同时保留其 receipt 与基础 receipt。只有原 9 个双源冲突中的 4 日满足所有价/股数差异 ≤0.001、成交额差异 ≤1 元的精度预算；采用较低成交额，其他字段按一致源值，保留全部盘前拒绝标记。这是显式 MVP 近似，不证明供应商舍入规则，且不会消除该行可能存在的事件缺口。原始基础计数和未决证据不改。
