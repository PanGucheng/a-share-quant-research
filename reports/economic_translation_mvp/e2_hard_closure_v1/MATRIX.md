# E2 Data Readiness Matrix

2026-09-15；基于 main@bbaae7e 的 MVP scope 调整。**E2 STILL BLOCKED；E2 READY FOR E3 FREEZE = false。** [范围评审](MVP_SCOPE_SIMPLIFICATION_REVIEW.md)、[当前报告](REPORT.md)、[验证](SCOPE_VERIFICATION.json)。原全库语义审计仍保留，当前不再要求先修完所有历史候选异常。

| 范围 | 当前分类 | 本轮结论 | 残余条件 |
|---|---|---|---|
| Model universe / B494 / canonical / E1 | FROZEN / UNCHANGED | 执行层门控独立，不回溯删股、不改预测 | 不用执行异常重训/选分数 |
| PIT Entry gate | IMPLEMENTED / VERIFIED | 唯一身份、普通非 ST 状态、此前 quote/ADV、必要事件证据；不满足则 NO_NEW_ENTRY | 当日事后异常不可回写；未知单股不再是 E2 必须修复项目 |
| 真实 Entry coverage | NOT CERTIFIED | 已封存日终观察不能直接当盘前证据；未读分数或重放策略 | 不以全体 NO_NEW_ENTRY 证明 E2 就绪，不宣称未持有名单 |
| H4 完整特殊交易制度模拟 | REMOVED FROM E2 REQUIREMENTS | special/uncertified → 禁止新买/主动交易；已有持仓按独立 contract 检查 | 有估值与权益则 CARRY_ONLY；否则归下方账户问题，不另建完整 simulator |
| H1 非估值冲突部分 | NO TRADE / CARRY WITH EVIDENCE | 3 日双源 close 一致，1 日单源 close 临时估值；此前 4 日 amount 精度近似保留 | 仅对应信息可得之后使用，不授权盘前读取当日 close |
| 残余 R1：已有市场敞口的估值 | CONDITIONAL HARD BLOCKER | 3 个 close 冲突案例，见[报价清单](scope_quote_incidents.csv) | 仅有股数/股票权利时须解决，未知保留账本并停止，不随意选价 |
| 残余 R2：已有敞口的身份/终止结算 | CONDITIONAL HARD BLOCKER | 80,754 个缺失日归并为[148 起资产覆盖事件](scope_lifecycle_incidents.csv)；另 1 组已知同股数迁移关系 | 148 起经济原因尚未确认；不是 148 个已确认现金退市，不预设绝不会持有 |
| 普通权益、现金应收、版本与税基 | READY WITHIN EXISTING CONTRACT | 旧 gross bridge/等价版本保留；仅现金应收仍留在 exposure 中，无须旧股票行情 | 应收不是可花现金；原股卖出不删除权利 |
| 残余 R3：已有登记权利的未知会计语义 | CONDITIONAL HARD BLOCKER | [528 个条件事件键](scope_conditional_event_cases.csv)分 514/6/6/2 四类；225 个参考诊断、89 个未分类重置保留 | 不要求预先人工修完 528 条；遇到实际权益时按类处理，不能 NaN→0 |
| Fractional bonus | UNIFIED CLAIM HANDLER / ALLOCATION CONDITIONAL | [183 个潜在键](scope_fractional_cases.csv)归同一类；Decimal 保留整数及残余权利 | 不舍弃、不虚构现金；实际触发取决于登记股数，分配证据未齐时仍阻塞交割 |
| 无持仓且无待结权利对象 | NO ACCOUNT BLOCKER | 准入失败只拒绝新买，不能中断其他合格持仓 | 本轮未证明哪些历史对象确实从未持有，数量 unknown |
| Date-PIT / warmup / open / fees / benchmark | PRIOR MVP GRADING RETAINED | 沿用严格 ADV 不足不新买、open-reference、税前口径、用户佣金等已有分级 | 本轮不选择 K/AUM/benchmark，不冻结 E3；早期费用假设及真实交易接线留待授权 |

当前只保留 R1–R3 三个**已有 exposure 条件下**的处理方向；不是三个已确认低频案例。权益相关 inventory 去重为 921 个键，不能宣称它们均实际触发，也不能宣称已排除。rights/general conversion/terminal cash 的可信总数仍 unknown。

**未达到 E2 READY FOR E3 FREEZE。拒绝新买的安全性已验证，持仓遇到未知后停止也已验证；停止不等于整段连续结算成功。提交后停止等待人工审核。**
