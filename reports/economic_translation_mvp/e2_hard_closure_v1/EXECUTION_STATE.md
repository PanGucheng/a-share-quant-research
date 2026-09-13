# Historical execution state

新增执行状态检查复用已有发布时间分类与 dated_limit_rule / price_bounds。明确 instrument/date、board、上市/ST/停牌、ordinary/special、IPO session、核准/注册制度、限价参考及上下限、有效区间、known_at、日期精度、来源与证据等级。

输出区分 ordinary_known、known_suspension、known_special_blocked、terminal_requires_event、unresolved。未知布尔值、同日只有日期精度的公告、未验证 special regime、占位上下限和 NaN 都不能变成普通可交易日。状态与 prepared quote 的订单时点、普通日 board/上下限必须一致。

EvidenceCheckedOpenExchange 是已有 Qlib EconomicOpenExchange 的 opt-in 扩展。验证候选与持仓的并集后才能初始化账户当日会话；普通 begin_session 不能绕过检查。没有新增真实策略 runner。特殊日的拒绝成交只解决入口安全，持仓估值与应收权利仍需单独提供。所需 prepared 字段未知时继续阻塞，不能靠 fabricated bounds 让特殊日过关。

实际有限样本：原 48 个缺行情日均有 BaoStock tradestatus=0 且 Tushare suspend_type=S、suspend_timing 为空的全日停牌记录。日终历史记录不是盘前公告时间证明。九年逐股状态、IPO/relisting/终止交易、除权参考价以及 ordinary/ST/改革边界上的上下限覆盖尚未取得。

States 长扫描复用现有 BaoStock collect_one，保留 4,416 个历史代码从首次候选日至 2023 年末的原始 OHLCV、tradestatus、isST。它只采集历史日终证据，不自动生成盘前状态表；空响应、缺行、代码回映与实际公告的冲突仍需事后审计。普通限价规则代码存在，不等于所有逐日输入都已具备。
