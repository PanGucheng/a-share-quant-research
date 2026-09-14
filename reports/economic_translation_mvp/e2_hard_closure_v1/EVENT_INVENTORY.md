# Event inventory and Qlib accounting bridge

2026-09-15：当前 scope 与优先级以 [MVP Scope Review](MVP_SCOPE_SIMPLIFICATION_REVIEW.md) 和 [Matrix](MATRIX.md) 为准；下文保留原语义审计方法与证据，不是事后准入黑名单或全库修复前置清单。

此前有界样本固定每年 7 月 16 日查询 ex_date；周末空表未另挑高频日替换。共 264 条实施记录，现金正值 261、stk_div 正值 29，两者可重叠。record_date 与 imp_ann_date 样本均有值；现金字段 3 条为 NaN，不能解释为无现金。逐年切片见 [event_inventory_slices.csv](event_inventory_slices.csv)。这些是 ex-date 样本，不是年度事件数量或按候选身份过滤后的全集。

[Tushare 分红送股接口](https://tushare.pro/document/2?doc_id=103)支持 ex_date 查询，单次上限 2,000 行。用户长扫描按 2015–2023 的 2,189 个交易日查询并保留每块响应；达到 2,000 行立即拒绝完整性声明。历史 ID 必须单独映射；无 ex-date、撤销/待实施、边界前登记和边界后结算等还需公告反向核对。该接口不覆盖全部 rights issue、conversion 或 delisting cash，当前没有它们的可信总数，不能写成零。

新增 EventPosition 直接接入现有 Qlib Account.current_position，复用 Position 和 CorporateActionBook。Distribution 要求明确 source、公告/登记/除权/到账/可上市日期及明确现金税口径、送股比例。没有把 cash_div_tax（税前）自动当成税后到账，也没有 NaN→0 的真实记录适配捷径。

已用真实 Qlib Account、关闭 portfolio metrics 的 synthetic 验证：

- 登记日交易结束捕获原始股数；除权日现金形成应收、红股形成未上市权利。
- 应收计入账面价值，不能作为下单现金；红股在上市日前不进入可卖量。
- 到账和上市分别更新 cash / shares，raw price 不再重复乘复权因子。
- 登记后卖出原股，现金和送股权益仍保留；延迟上市可重新创建仅有新股的持仓。
- 原始股数、现金、权利与除权参考的手算守恒；T+1 用原有 RawSellableLedger。
- 非整数分配、漏登记、漏事件日、重叠未上市权益、未知税或 terminal 权利直接失败。

事件会话处理只接收当时已知的除权参考估值；不得用当天晚些时候的 close 影响开盘订单。现金税的持有期/后扣税、复杂换股、配股认购/弃权、跨边界待结算事件仍需实现和实际覆盖验证。最小桥已可测，完整真实事件账户尚未 READY，也未运行。

2026-09-14：三项采集完成后的离线语义表保留全部 28,681 条原始版本。原 682 个不同内容重复组中 674 个可按等价权益合并、8 个未决；非实施版本 36 条仍保留 provenance。现金缺值补证 36 条，候选内 34 条；没有直接填零。候选经济资产内 23,488 个键满足普通税前条款，602 个键/533 个资产未决；[未决事件表](semantic_unresolved_events.csv)列明原因。6 个上市日缺失为 SZ000155、SZ000912、SZ300116、SZ002260、SZ300362、SZ002219，不能假设 ex-date 即可卖。

Distribution 现支持显式 before_dividend_income_tax：cash_div_tax 进入独立 gross_cash_per_share，原 net 字段不得混用；适配函数拒绝未决事件和未选择税前口径。现有 Qlib 应收/到账/红股桥已通过合成守恒测试，但仍拒绝需要未知零碎股分配的记录。191 个已解析事件对 100 股产生非整数红股权益，涉及 166 个资产。225 次除权参考不符、89 个无匹配事件的参考价重置日都只作为待查证据，不反推权益。配股/一般换股/终止现金的可信总数仍 unknown；这些既有输入不支持声称事件全集完成。详见[当前报告](REPORT.md)。

事件桥允许实施公告元数据早于账户起点，但登记/除权仍限制于批准窗口。SH600016（2014-12-31 公告、2015-01-08 登记）和 SZ000511（2014-12-25 公告、2015-01-05 登记）的既有封存记录已通过纯适配验证；没有读取额外 2014 市场数据。
