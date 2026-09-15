# C1 + C2 实施与验收

2026-09-15；基线 `main@146cb04`。用户授权“实现并验收 C1 + C2，不再扩展 E2 scope”。
本轮按 [既定阶段合同](STAGE_BOUNDARY_REVIEW.md) 实施，不重新设计策略或全库治理。

**C2 已实现并通过 synthetic 集成验收；C1 已实现输入适配，但固定真实 canary 未通过普通 PIT 路径验收。
E2 STILL BLOCKED，仅剩 C1 的真实来源可得性验收；不宣布 E2 CORE READY。**

## C1：实现与真实验收分开

[economic_core_inputs.py](../../../qlib_integration/economic_core_inputs.py) 接收绑定 instrument、
field、phase、Fact/source/hash 的 Evidence，复用原 PIT Fact 和 execution_state。
A 只接盘前数据，B 只接开盘价格/证据，C 只接日终身份、权益覆盖及估值。
未来版本在校验其业务条款前过滤，避免未来错误事件反向拒绝过去入场。
同时间冲突不选赢家；event clearance 必须显式带覆盖区间、五类事件范围、事件 ID 和依据。
空事件表不产生 events_clear=True。无效未持有候选被拒绝，不删除研究证券。

`market_phase_records` 直接消费已封存 semantic overlay 的有界切片，复用 causal_adv20。
旧 overlay 的 raw_open 曾受当日 high/low/量价质量诊断筛选，**不能直接拿它作开盘输入**；
新 B 入口固定使用单独原始 BaoStock open 字段，不根据收盘/全日量或事后质量挑价格源。
普通 prepared row 仅在 A 资格已通过且 B 到达后生成，raw_close 留空；C 尚未传入。

沿用既有 daily-data MVP 近似：前一交易日量价用 prior-session EOD，日线 open 作开盘参考，
日终估值在收盘后使用。模型阶段时钟与 source_known_at=null 分开标注；它不是历史发布时间证明。
这些近似不允许重构普通状态、ST/停牌、身份迁移或 events_clear 的盘前发布时间。

真实样本在读取值前固定于 [CORE_CANARY_SCOPE](CORE_CANARY_SCOPE.json)：
SH600000，2020-08-24，历史量窗口 2020-07-27 至 2020-08-21。复用该证券原已固定探针，
没有按分数、表现或本次成功率选择样本；失败后未换证券、日期或扩大采集。

| 检查 | 结果 |
|---|---|
| 封存源、既有 overlay、独立涨跌停表绑定 | PASS；14 个输入 hash，21 个证券日 |
| 精确 20 个此前交易日 ADV | PASS；adapter 与原始源独立求和均为 50,322,888.6 股 |
| 单独原始 open 与既有独立价格/涨跌停表 | PASS；正价格且位于已有上下限内 |
| 盘前 ordinary state / identity availability / complete event coverage 证明 | 固定输入未提供这些可得性证明；日终状态 known_at 为空、ordinary_regime_certified=false |
| 事件切片为空 | 0 条匹配行；不能据此证明完整无事件或 rights/terminal coverage |
| 非空普通 PIT 准入路径 | **NOT ACCEPTED**；实际返回 NO_NEW_ENTRY，不能以全拒买认证 Core |

这不是新增三个 blocker，而是既定 **C1 source-bound input** 尚未满足的字段。
adapter 的量价接入和拒绝分支已经落地；synthetic 显式来源可通过普通分支，真实来源不能补造证据。
既有日终原始数据不能直接变成盘前完整证明。该 canary 不覆盖九年可交易范围，
也没有把少量匹配事件数量当成完整 corporate-action inventory。

最终输出 `outputs/economic_translation_mvp/e2_core_acceptance_v4`，前三版同一固定样本的实现核验
保留；最后一版包含未来未可得事件先过滤、日终新增未知权益拒绝提交的修正及 code hashes，样本/验收标准未变。
[独立核验器](../../../scripts/verify_e2_core_canary.py) 不导入 production adapter，
逐 hash 验证、从原始量源单独求均值，并复核缺证不能取得普通准入的结论。
机器证据汇总见 [CORE_ACCEPTANCE](CORE_ACCEPTANCE.json)。

## C2：日级执行与会计接线

[economic_core_session.py](../../../qlib_integration/economic_core_session.py) 的 CoreSession
复用 Qlib Account、EventPosition、EconomicOpenExchange，不新建 backtester/策略框架。
既有实现和 receipts 未改写；新入口是独立 opt-in 层，要求 metrics/benchmark-return 关闭。

顺序固定为 A → 事件应用 → Entry/Holding 门控 → 已给定意图的允许/拒绝 → B → 普通成交 →
C → 全部股数/权利估值 → 收盘登记 → 整日提交。意图在读取 B 前复制，
不向 A 暴露 C 的 close，也不允许跨阶段或跨日替代。登记日至除权之间尚未入账的已取得权利
也纳入 exposure，不能只检查已上市股数或已生成应收。

被拒绝未持有候选不进入旧的全候选 continuity 检查；CARRY_ONLY / CASH_CLAIM 不构造普通
prepared rows，不伪造限价/ADV/factor。普通订单继续经过原 open、方向限价、lot、T+1、
容量、母单费及现金预算检查。未知权益、terminal、遗漏事件条款仍 HALT_RETAIN。
现有 scope 不支持的持仓加仓意图仍拒绝，本轮不借机定义 E3 加仓规则。

每个账户日先在完整工作副本执行，所有事件、成交和收盘检查通过后才提交。
失败丢弃工作副本及当天 exchange 的 T+1/费用/容量状态，保留上一完整日；
没有留下可继续使用的半日账本。重复成功日和跳过日历会拒绝，失败日可重放。
账户内部维护现金/股数/权利及当日估值一致性，未调用 Qlib 收益报告、benchmark、历史 NAV 输出。
这是研究模拟的事务边界，不是对真实券商已执行订单的撤销机制。

验收覆盖：多日买入/卖出、登记→除权→支付→红股上市、原股卖出后现金/股票权利持续存在、
cash-only 无旧股行情、特殊 carry 与另一只普通证券成交共存、未知新候选不阻塞、未知持仓停机、
零碎权益拒绝交割、部分成交/容量/T+1、母单最低费、missing open 不使用 close。
事件后、成交后、收盘后、提交前故障注入均不改持久账本；从相同检查点重放与干净执行一致。
普通分配和现金余额用独立标量算式验证，而非仅比较两个生产函数。

旧 dated fee 引擎的默认费率没有在本轮冒充用户万2.5。个人费用配置/早期费基等继续按原计划
留在 E3 字段冻结与接入事项，不扩展本次 C1/C2 验收范围。

## 当前结论与停止点

**C2 CLOSED / ACCEPTED WITHIN CORE SCOPE；C1 IMPLEMENTED / REAL-SOURCE ACCEPTANCE BLOCKED。**
剩余仅是本次固定输入没有支持 ordinary PIT 路径所需的 C1 证据；不重新展开 148/528/921 个案例。
没有引入 C3、扩大模拟器、放宽未知状态或事件标准。R1–R3 保持冻结实际 exposure 的条件事项。

本轮未重采 Quotes/States/Dividends、未重跑 E1、未访问 B494 分数或 2024+；
没有真实账户路径、K/AUM/buffer 选择、收益评价或 E3/E4。
不提供重跑长扫描命令。完成代码/文档核验后提交推送，停止等待人工审核。
