# Execution-only quote normalization

两个供应源在 SH601360 的 2,065 个有效日上 OHLC、成交量和成交额均一致（比较容差 rtol=2e-5、atol=0.02）。BaoStock 历史新代码还返回停牌日，旧代码查询为空；空表不能解释为旧证券从未存在。

本地 SH601313 有 654 个有限 close 日，全部落在上述一致配对日期中；最晚为 2018-02-14。既有 community 转换对该代码多乘 volume 100、amount 1000，价格换算正确。新隔离规则采用 native volume × factor、native amount × 1；SH601360 保留 native volume × factor × 100、native amount × 1000，OHLC 均除 factor。两个规则只证明列出的证券和观测日期，不向其他代码推广，也不把缺失日补成有效报价。

实际另存 2,719 条规范化报价及逐规则源 hash、有效日列表。独立检查用未修改的旧配方输出还原 native 值，再由新函数转换，逐字段对照双源；拒绝非有限量价、不合理 OHLC/VWAP、未知 factor 和越界日期。原 provider、canonical、冻结模型未修改。2014 warmup 使用独立 20 日双源证据，不从 2015 倍率外推。

发行人 [2018-02-13 停牌公告](https://static.cninfo.com.cn/finalpage/2018-02-13/1204419027.PDF)及券商 [2018-02-27 操作通知](https://3g.zszq.com/ywgg/bulletin?id=99671)支持 601313→601360 和 2 月 28 日启用关系。拟变更与券商通知不能代替完整登记结算迁移包。链接的上交所实施 PDF 本次返回 HTML（已保留失败下载 hash），未冒充读到最终 PDF。

候选键的身份碰撞：2015 年 244 日、2016 年 200 日，两代码同时存在；2017–2023 未见同时存在。只读 datetime/instrument 投影并检查冻结键 hash，没有读取分数或 outcome。normalize 后保留 research ID；账户入口要求显式 economic asset mapping，重复经济身份直接拒绝，不能静默选择代码或重复分配资金。

全体 4,416 历史候选的有效值、单位异常及离池延续未完成九年全扫描。用户 Quotes 模式从首次候选日至 2023 年末逐值审计，故意保留旧配方的异常，输出逐股日期原因；不会暗中应用本次 overlay，更不会自动认证所有单位。单位已修正不意味着身份、状态或事件已全部 READY。
