# Economic Translation MVP — 当前 E2 状态

2026-09-15；基线 main@bbaae7e。**E2 STILL BLOCKED；未达到 E2 READY FOR E3 FREEZE。**

已按用户的 Scope Simplification 计划调整并实现：Model/Research Universe 保持冻结，新增独立 PIT 新开仓门控，将 Entry 与 Holding/未结权利检查拆开。当前不再要求先补齐所有 4,416 个历史代码的特殊事件，也不把“某只股票不能安全新买”本身作为 E2 hard blocker。

完整交付见 [Scope Simplification Review](MVP_SCOPE_SIMPLIFICATION_REVIEW.md)、[新 E2 Matrix](MATRIX.md)、[SCOPE_VERIFICATION](SCOPE_VERIFICATION.json)。bbaae7e 的完整语义证据仍保留于 [SEMANTIC_RECONCILIATION](SEMANTIC_RECONCILIATION.md) 和 [SEMANTIC_VERIFICATION](SEMANTIC_VERIFICATION.json)；原 3 项采集和 E1 均不重跑。

## 本轮推进

- PIT 门控只读取决策前可得且有效的证据，未知/冲突返回 NO_NEW_ENTRY；未来不良事件不反向排除历史股票。没有将事后异常表当作准入黑名单。
- 未持有候选不合格，不再阻断其他持仓；已有股数、现金应收、待上市红股始终纳入检查。特殊/未认证制度可 CARRY_ONLY，不需要完整特殊撮合模拟器；估值明确也不自动允许交易。
- 固定现金应收可独立保留，不因旧股票没有行情而阻塞；仍按原事件桥处理付款，不能提前用于下单。
- Fractional bonus 统一为精确 Decimal 权利拆分，残余权利不得丢失或虚构现金。实际分配证据未知仍停止；没有声称已完成真实零碎股交割。
- 7 个剩余报价案例中，3 个有双源一致收盘、1 个可保留单源临时估值，改按不主动交易处理；已有持仓的 close 冲突剩 3 个，见[清单](scope_quote_incidents.csv)。
- 80,754 个尾部缺失日整理为[148 起资产覆盖事件](scope_lifecycle_incidents.csv)。147 起最后状态为停牌、60 起此前 20 日有特殊观察，这些不能当作退市或长期停牌的原因证明。

## 简化后仍须面对什么

当前残余是 **3 个条件处理方向**：R1 已有市场敞口的估值冲突，R2 已有敞口的身份/生命周期/结算，R3 已有登记权利的公司行动语义。它们不是要求全库每条先修完的总清单，只有实际 exposure 触发时才需要解决或停止。

528 个条件事件键已分为 514 个现金条款未知、6 个权益条款冲突、6 个现金与上市条款问题、2 个历史登记快照问题；另有 183 个潜在零碎股键、225 次除权参考诊断与 89 个未分类参考重置日。前三组去重共 921 个事件键。配股、一般换股和终止现金的可信总数仍 unknown，已知同股数代码迁移关系为 1 组。

本轮没有策略或持仓重放，因此不能宣称这些问题仅涉及“从未持有”的股票，也不能宣称真实问题已只剩几个案例。已封存日终状态缺乏盘前 known_at，真实非空 PIT 可执行范围仍未认证；不能通过全体 NO_NEW_ENTRY 得到一个表面 READY。

现有 warmup 缺值门槛、日期级 PIT、日线 open-reference、税前股息、用户佣金与小额成交额精度等分级保留。特殊状态完整模拟已从 E2 必须条件移除，但实际持仓的未知估值与权益不能用不交易来消除。

## 验证与停止点

22 项新 scope 测试、71 项既有 E2 回归、46 项 fast 和 6 项 Qlib synthetic runtime 通过；独立验证核对 210 个输入绑定、6 个输出及事件计数。只对已封存的 148 起覆盖事件和 7 日报价作有界离线复核，没有重新采集、计算真实 NAV/收益或访问 2024+。

新层是 opt-in 前置 contract 和持仓/权利适配；旧 Exchange 及其准备数据要求没有被绕过，未新增真实策略 runner。详细能力边界和最小后续工作见 [Review](MVP_SCOPE_SIMPLIFICATION_REVIEW.md)。

**E2 STILL BLOCKED。提交、推送后停止等待人工审核；不修改 B494/canonical/E1/旧 receipts，不选择 K/AUM/benchmark，不自动进入 E3/E4。**
