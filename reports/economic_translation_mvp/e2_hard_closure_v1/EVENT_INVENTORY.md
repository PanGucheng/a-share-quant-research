# Event inventory and Qlib accounting bridge

固定每年 7 月 16 日查询 ex_date；周末空表未另挑高频日替换。共 264 条实施记录，现金正值 261、stk_div 正值 29，两者可重叠。record_date 与 imp_ann_date 样本均有值；现金字段 3 条为 NaN，不能解释为无现金。逐年切片见 [event_inventory_slices.csv](event_inventory_slices.csv)。这些是 ex-date 样本，不是年度事件数量或按候选身份过滤后的全集。

[Tushare 分红送股接口](https://tushare.pro/document/2?doc_id=103)支持 ex_date 查询，单次上限 2,000 行。用户长扫描按 2015–2023 的 2,189 个交易日查询并保留每块响应；达到 2,000 行立即拒绝完整性声明。历史 ID 必须单独映射；无 ex-date、撤销/待实施、边界前登记和边界后结算等还需公告反向核对。该接口不覆盖全部 rights issue、conversion 或 delisting cash，当前没有它们的可信总数，不能写成零。

新增 EventPosition 直接接入现有 Qlib Account.current_position，复用 Position 和 CorporateActionBook。Distribution 要求明确 source、公告/登记/除权/到账/可上市日期及现金税后权益、送股比例。没有把 cash_div_tax（税前）自动当成税后到账，也没有 NaN→0 的真实记录适配捷径。

已用真实 Qlib Account、关闭 portfolio metrics 的 synthetic 验证：

- 登记日交易结束捕获原始股数；除权日现金形成应收、红股形成未上市权利。
- 应收计入账面价值，不能作为下单现金；红股在上市日前不进入可卖量。
- 到账和上市分别更新 cash / shares，raw price 不再重复乘复权因子。
- 登记后卖出原股，现金和送股权益仍保留；延迟上市可重新创建仅有新股的持仓。
- 原始股数、现金、权利与除权参考的手算守恒；T+1 用原有 RawSellableLedger。
- 非整数分配、漏登记、漏事件日、重叠未上市权益、未知税或 terminal 权利直接失败。

事件会话处理只接收当时已知的除权参考估值；不得用当天晚些时候的 close 影响开盘订单。现金税的持有期/后扣税、复杂换股、配股认购/弃权、跨边界待结算事件仍需实现和实际覆盖验证。最小桥已可测，完整真实事件账户尚未 READY，也未运行。
