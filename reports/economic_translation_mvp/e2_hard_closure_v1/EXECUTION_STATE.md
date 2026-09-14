# Historical execution state

新增执行状态检查复用已有发布时间分类与 dated_limit_rule / price_bounds。明确 instrument/date、board、上市/ST/停牌、ordinary/special、IPO session、核准/注册制度、限价参考及上下限、有效区间、known_at、日期精度、来源与证据等级。

输出区分 ordinary_known、known_suspension、known_special_blocked、terminal_requires_event、unresolved。未知布尔值、同日只有日期精度的公告、未验证 special regime、占位上下限和 NaN 都不能变成普通可交易日。状态与 prepared quote 的订单时点、普通日 board/上下限必须一致。

EvidenceCheckedOpenExchange 是已有 Qlib EconomicOpenExchange 的 opt-in 扩展。验证候选与持仓的并集后才能初始化账户当日会话；普通 begin_session 不能绕过检查。没有新增真实策略 runner。特殊日的拒绝成交只解决入口安全，持仓估值与应收权利仍需单独提供。所需 prepared 字段未知时继续阻塞，不能靠 fabricated bounds 让特殊日过关。

此前有限样本：原 48 个缺行情日均有 BaoStock tradestatus=0 且 Tushare suspend_type=S、suspend_timing 为空的全日停牌记录。日终历史记录不是盘前公告时间证明。当时该样本没有证明九年覆盖；当前进展以下段及 REPORT 为准。

2026-09-14：已封存 States 全量结果现已和 quote/event/identity 合并为逐股逐日观察表。7,429,962 个证券日保留 ordinary/ST/suspended/special_or_rule_conflict/unresolved，80,754 个未知状态日全部处于 148 个代码尾部覆盖缺口；不能推定为退市。观察表用于审计与有来源估值，尚不能替代上文的严格执行入口。

70 个证券日超出已有普通 dated rule 的候选上下限，详见[特殊日期](semantic_special_days.csv)。regular-family 诊断调用的 IPO session=6 是占位询问，不是真实上市天数；上下限均为 provisional。所有行 known_at 为空、ordinary_regime_certified=false、can_buy/sell_preopen=false，因此不会让未知日变为可交易日。可消费的日终观察层已完成，历史 IPO/relisting/terminal 及盘前可得证据仍属 H4；不得把“观察值存在”当成有效状态已完整。见[语义合同](SEMANTIC_RECONCILIATION.md)。
