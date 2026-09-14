# E2 MVP Scope Simplification Review

2026-09-15；基线 main@bbaae7e。参考用户提供的调整计划，采纳 Entry/Holding 分离、按经济事件归类与条件触发补证；不采纳“工程范围缩小就已经证明历史影响很小”的隐含推断。附件 hash 和实际验证见 [SCOPE_VERIFICATION](SCOPE_VERIFICATION.json)。

**E2 STILL BLOCKED；不自动进入 E3/E4。** 原全体候选审计作为潜在风险 inventory 保留，不再作为“每条记录修完才允许研究”的清单。本文调整 E2 的验收范围，不冻结 E3 资格、策略或参数。

## 调整后的两个 universe

Model/Research Universe 继续使用 frozen B494、canonical、预测和 E1。Executable Universe 是每次决策前按可得证据计算的新开仓集合，不是事后导出的静态股票名单。没有删除历史证券、重训模型、改分数或读取收益。

最小 Entry 条件复用现有 execution_state/dated rules、ADV20 及身份语义：身份唯一；已有信息支持普通、非 ST、非停牌状态；此前交易日的 raw quote quality 和严格 ADV20 就绪；必要事件有明确可得的已处理/无待处理证据。否则返回 NO_NEW_ENTRY。没有增设上市天数/流动性数值搜索，也没有修改既有普通限价规则。

PIT Fact 携带 observed_on、effective_from/to、known_at、source 和时间精度，由 facts_by_id 绑定证券；调用方必须保证来源与证券正确绑定。门控只取决策前已知且在有效期内的版本；同时间的相互矛盾版本拒绝。仅日期精度的同日信息不能用于盘前；当日 OHLC 的事后质量检查不能反向用于当天新开仓。未来版本不会覆盖此前可见版本；空事件表不自动等于 events_clear=True。

现有全期日终观察表 known_at 为空，不能直接改写成盘前 Fact。风险 inventory 只用于选择补证/会计处理工作，绝不传入 entry 作为未来黑名单。之前的日期级 PIT 近似仍需明确范围及来源，不虚构历史发布时间。

## Entry 与 Holding 的 contract

新增 opt-in [economic_mvp_scope.py](../../../qlib_integration/economic_mvp_scope.py)：

- entry_eligibility：ALLOW_ENTRY / NO_NEW_ENTRY；坏的未持有候选不再让别的持仓一起失败。
- position_exposures：从现有 Qlib EventPosition 读取股数、未上市红股、现金应收。即使原股已经卖出，剩余权利仍在 exposure 中。
- holding_continuity：身份/权益/估值明确时可 CARRY_ONLY；未知交易制度、缺乏自愿交易许可本身只禁止交易。事件或身份未知、必要估值无依据、已经确认终止但股权尚未结算时 HALT_RETAIN。固定币值的现金应收单独 CARRY_CASH_CLAIM，不要求继续取得旧股票行情，也不提前变成可下单现金。
- scope_account：纯检查，不修改现金、股数、价格或权利；返回完整保留对象和阻塞原因。持仓身份碰撞会阻塞账户；未持有别名碰撞则双方拒绝，不挑一个分数。
- require_scope_order：HALT_RETAIN 账户不能下单；CARRY_ONLY 不能主动退出；没有 ALLOW_ENTRY 就不能新买。通过该门控后仍须原 Exchange 的订单、价格、容量、T+1 和费用检查。

本轮交付的是分离后的前置层和 Qlib 持仓/权利读取适配，不是策略 runner，也没有改写旧 Exchange 的 prepared schema。后续实际交易接入须落实独立的 carry 分支；不得为迁就旧 schema 给特殊持仓伪造限价或行情。PREFLIGHT_PASSED 仅表示本次输入检查通过，不是成交许可、E2 readiness 或整段真实账户可运行的认证。

已知停牌/特殊日可以保留有来源、在对应时点可用的估值与权利并禁止交易。停在旧检查点能保护账本，但未知持仓价值仍不能据此宣称已经连续到 2023 年末，更不能输出完整真实 NAV。新范围没有允许强制末价退出、归零或回溯删股。

## H1–H4 重新分级

| 原问题 | 本轮处理 | 仍须解决的条件 |
|---|---|---|
| H1 新开仓的量价质量不明 | 当时已知则 NO_NEW_ENTRY；不要求无限补第三源 | 当日才发现的异常不得回写此前资格；后续成交/估值校验独立进行 |
| H1 已持有、收盘估值有来源但交易量/其他报价不可靠 | NO_VOLUNTARY_TRADE + 对应时点估值；仅成交量或 high 差异不自动破坏持仓价值 | 源与时点可追溯，不能把盘后 close 用在盘前 |
| H1 已持有、收盘估值本身冲突 | 保留股数和账本，HALT_RETAIN | 实际遇到时解释估值；本轮剩 3 个已识别案例 |
| H4 IPO/relisting/特殊/未认证 regime | NO_NEW_ENTRY / NO_VOLUNTARY_TRADE；不需要完整 special-session simulator | 原持仓的身份、估值、权益仍适用 Holding contract |
| H2 尾部断档与迁移 | 按资产覆盖事件维护，一起保留旧/新身份与未结权利 | 仅有实际 exposure 时必须查明连续身份或结算，不能推定“这些股不会买到” |
| H3 ordinary dividend/bonus、等价版本、税基 | 沿用 bbaae7e 的合并与税前桥 | 非实施版本与真正冲突不混合，现金缺值不填零 |
| H3 fractional bonus | Decimal 精确拆分整数部分与残余权利，统一 PENDING_ALLOCATION 类 | 整数分配用旧桥；实际出现零碎权利需分配凭据，未自动接入真实 Account 估值/交割 |
| H3 rights/conversion/terminal/ambiguous claim | 条件触发的专项处理，不预先逐条人工清洗全库 | 已持仓/应收/红股权利受影响时必须处理或停止，不以“不成交”代替结算 |

## 简化后的数量与真实工作量

[报价案例](scope_quote_incidents.csv)：原尚未完成的 7 日中，3 日双源收盘一致、1 日有单源正有限收盘，可按不主动交易分别保留估值/临时估值。剩余 3 个估值冲突为 SH600822 2016-12-01、SH603117 2016-12-01、SZ001872 2017-10-24。原先 4 个 amount-only 精度近似保持不变。上述分级不改变旧 sealed quote 表，也不是当日盘前可得性证明。

[生命周期事件](scope_lifecycle_incidents.csv)：把 80,754 个缺失证券日压缩为 148 起资产覆盖事件。147 起在缺口前最后一个日终状态为停牌，1 起为 ordinary；其中 60 起在此前 20 个交易日有 special/rule-conflict 观察。它们都是诊断事实，不能据此认定 true delisting、long suspension、merger 或数据源断档。经济类型仍为 unknown。已有另 1 组同股数代码迁移关系 601313→601360，普通迁移原语保留；有登记/未结权利时仍需要明确映射。

[未决权益](scope_conditional_event_cases.csv)：528 个潜在登记范围事件键改列条件案例，统一分为 **514 个现金条款未知、6 个权益条款冲突、6 个现金与红股上市条款不全、2 个历史登记快照问题**。这不是 528 项必须立刻人工完成的任务，也不是已经证明不影响实际持仓。

[零碎股候选](scope_fractional_cases.csv)：183 个键对 100 股构成非整数红股权益，归到同一个分配处理类别。实际数量取决于真实登记股数；不能从该样本量推断 183 次实际触发。无证据时不向下舍弃权利、不凭空兑换现金，不用未知红股参与交易。

225 次除权参考诊断和 89 个无匹配事件的参考价重置日仍保留，不能直接计为 rights 或 conversion。528 个未决、183 个零碎股候选与 225 个参考诊断合并去重后涉及 **921 个事件键**，不是三者之和，也不是 921 个已证明需要专项开发的事件。配股、一般换股、终止现金的可信实际总数仍 unknown；本轮不虚构“已经缩减为几个低频个股”。

因此，剩余工程应按 **3 个账户处理方向**组织，而不按全部缺失日排队：

1. 有 exposure 的估值冲突与合格的 carry mark；当前具体冲突仅 3 日。
2. 有 exposure 的生命周期/身份/结算；148 起条件覆盖事件与 1 组已有迁移关系是待按需定位的入口。
3. 有 exposure 的权益；先实现可复用的条款补证、登记快照、零碎股分配证据接口，再处理实际触发的 rights/conversion/terminal。

本轮不做 K/AUM/benchmark 选择或真实持仓重放，故“从未持有、不需继续”的证券/事件数量目前**无法认定**。已核验无 exposure 的对象可以不处理，这是 contract 的一般分支，不能替代真实历史路径证据。不能利用所有日终数据缺 known_at 而全部 NO_NEW_ENTRY，再宣布 E2 READY。

## 验收与停止点

实现层已验证：PIT 版本过滤、拒绝不合格新买、持仓/现金应收/红股不消失、现金应收不依赖股票价格、无交易许可不能成交、未知权益不被会计近似抹除。非整数分配的权利清单统一了处理方式，但不是实际分配规则已获得。

数据与研究验收仍不足：尚未认证非空的真实 PIT 普通可执行路径；实际持仓可达性未测量；3 类账户问题在遇到 exposure 时仍可能无法连续结算。scope 缩小不使这些事实自动消失。后续应优先用已有数据做最小普通路径来源接入，并按受影响 exposure 接入处理器；不要回到全库逐股人工清洗，也不先开放收益或偷偷运行路径选择。

22 项新测试与 71 项既有 E2 回归合计 93 项通过，另有 46 项 fast 和 6 项 Qlib synthetic runtime 通过。未运行可能触及真实冻结收益或 2024+ 的 legacy 全量验证；使用本轮范围内的定向检查。独立程序核验 210 个输入文件绑定、6 个输出文件、148 起事件的唯一性、7 个报价的独立估值分类及 528 个键无丢失。全部为离线已封存数据；仅对 148 起覆盖事件和 7 日报价作有界复核，未重跑三项采集。完整结果在 `outputs/economic_translation_mvp/e2_mvp_scope_v5`，摘要和 hash 见 [SCOPE_VERIFICATION](SCOPE_VERIFICATION.json)。

**E2 STILL BLOCKED。当前只保留真正可能破坏已有股数/权利/估值连续性的条件问题。提交、推送后停止等待人工审核；E1、B494/canonical/旧 receipts 不变，E3/E4、真实 NAV/收益和 2024+ 仍未授权。**
