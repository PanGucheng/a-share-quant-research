# E2 Hard-Blocker Closure

2026-09-14 更新：[用户运行/中断复核](USER_RUN_20260914.md)。Quotes 全部完成并验 hash，States 完成118只、Dividends完成5日；使用新版[续跑命令](RUNBOOK.md)。以下为本轮原始就绪评估，E2仍BLOCKED。

2026-09-13；基线 main@8501456。**E2 STILL BLOCKED；E2 READY FOR E3 FREEZE = false。**

本轮采纳附件的隔离执行数据修正、事件实际盘点、持仓连续覆盖、有限 warmup 和务实隔夜时点；不把“遇到 unknown 会报错”当成数据已经完整。E1 未重跑，冻结模型、分数、canonical dataset 和旧证据均未修改。没有真实账户、收益评价或 2024+ 研究值访问。

已推进的部分：

- SH601313 的全部 654 个有效历史行情日都能与独立双源配对；原换算后的 volume 约多 100 倍、amount 约多 1000 倍。执行层另存修正结果，未改模型输入。SH601360 的 2,065 个有效日原换算成立。
- 两代码在候选键中同时出现 444 日：2015 年 244 日、2016 年 200 日。这是证券身份冲突，不能把两条正确行情当作两个独立经济资产。尚未修改冻结池或选择保留哪个分数。
- 前轮 held-continuity 的 48 个缺行情日，全部得到 BaoStock 停牌标记和 Tushare 全日停牌记录支持。缺行情原因已解释；盘前可得时间、持仓估值和九年连续性仍须验收。
- 2015 首日 2,000 候选的 20 日 warmup 已读 40,000 个证券日；另行双源核对并修正旧代码 20 日量单位后，1,706 只具备完整有限非负量输入，294 只仍有未知量。前者不是全池单位认证。
- 9 个预定 ex-date 切片取得 264 条实施分配记录，其中 261 条现金为正、29 条送转为正。不是全九年事件总数。现金字段另有 3 条缺值，不能填成零。
- 最小 Qlib Position 扩展已通过登记权益、现金应收/到账、红股待上市/可卖、登记后卖出等 synthetic 守恒检查。税、配股、终止权利及完整真实事件接入仍未完成。

关于“难处理的个股是否干脆不考虑”：可以在未来收益打开前审议统一的新开仓资格规则，例如身份、单位、普通交易状态和必要事件未解决时不买入。但资格必须在当时可得，不能利用后来发生的退市、重组或事后发现的困难全历史删股。已经持有的股票不能消失，必须保留到可核对的退出或权利结清。当前没有排除任何证券，也没有证据支持“影响几乎为零”。身份碰撞对已冻结训练的实际影响未评价，修正模型不在本轮授权内。

专题与后续入口：

- [Quote Normalization](QUOTE_NORMALIZATION.md)
- [Execution State](EXECUTION_STATE.md)
- [Event Inventory / Qlib Bridge](EVENT_INVENTORY.md)
- [Held Continuity](HELD_CONTINUITY.md)
- [Timing / Warmup / Fees](TIMING_WARMUP_FEES.md)
- [更新后的 E2 Matrix](MATRIX.md)
- [用户长扫描命令](RUNBOOK.md)

已完成 61 项有界执行/数据/会计测试和 fast 46 项检查；最终检查与本地证据哈希见 [VERIFICATION.json](VERIFICATION.json)。长扫描入口已做 synthetic 分块与封存校验，完整 Quotes / States / Dividends 扫描由用户执行，尚未运行。扫描完成后仍需异常闭环和真实事件覆盖核验；不会自动转为 E3。
