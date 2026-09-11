# E2 A 股执行合同与数据就绪评估

日期：2026-09-11。计划修订提交：`6464937`。
状态：**E2 BLOCKED BY EXECUTION / DATA GAP**；工程语义验证通过不等于数据可执行。
本文件为 E3 审议材料，不是 E3 freeze 或 E4 运行许可。

## 1. 权威、访问与复用

canonical identity 沿用 `canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`。
E1 仅用已冻结的 B494，见 [固定输入](e1_inputs.json)；E2 不导入 E1 reader，不读 prediction/label，不形成真实投资组合。
真实行情访问仅为 [有限 canary](quote_unit_canary.csv) 的 4 证券、6 个预先固定窗口、7 个字段，读取前按日历定位二进制 offset。
[访问记录](quote_access.json) 包含全部请求、精确日期、字段和被批准字节的 hash；没有对包含 recent 的整个二进制父文件求 hash。
Parquet 只读 footer/schema，见 [来源清单](market_source_inventory.json)；不能把含 recent 的 row group 先解码再过滤。
来源日期/文件名等元数据不是个股研究值。没有读取 2024+ 的数值页、标签、B score、旧策略 NAV 或 benchmark returns。

新增 [EconomicOpenExchange](../../qlib_integration/economic_exchange.py) 是已有 `PreparedQuoteExchange` 的专用子类；
继续由 Qlib `Exchange.deal_order`、`Account.update_order`、`Position` 更新账户，由既有父类记录成交、拒绝和 T+1。
不修改 legacy adapter/config，也不连接旧 `runner` 或历史回测入口。新 production backtester、两条真实 selector 和指标引擎均未建设。
Qlib 源码 commit 仍为 `d5379c520f66a39953bad76234a7019a72796fd0`；实际使用文件的 hashes 见 [交付证据](DELIVERY_VERIFICATION.json)。

## 2. Data Readiness Matrix

| Required field | Source / date coverage | PIT / availability | Unit / missingness | Authority | Blocker status |
|---|---|---|---|---|---|
| B score、keys、开发日历 | sealed 9 folds，2015–2023 | 当日 score 的计算语义已冻结；所有 494 输入能否在次日盘前发布，仍缺逐字段小时级证据 | score float64；本轮 E1 真实扫描待用户运行 | D1/D2/D3 metadata 与 fixed input hashes | **score 信息时点待核实**，不能把事后计算时间当历史 known_at |
| provider OHLC、factor | canonical 使用的 community derived provider；canary 覆盖 2015/2020/2022/2023 | 日 OHLC 是日终数据；open 单独用于成交确认，不作为事前排名 | adjusted price / factor → raw CNY/share；523 有效配对全部通过量额隐含均价落在 OHLC 的宽容差检查 | 现代码换算＋有限值核验，非独立原始供应商认证 | **全池/全期覆盖及源语义未认证** |
| volume、amount | 同一 provider，596 个请求证券日 | 当日完整 volume/amount 属 C；ADV 只用过去 20 完整交易日 | volume × factor ×100 = shares；amount ×1000 = CNY；73 缺 volume：59 属 STAR 2015 上市前窗口，14 属 SZ300001 2015 窗口 | 内部单位一致性支持，不能证明真实竞价容量 | **14 个缺值不能自动视为停牌零量**，须 dated suspension 证据 |
| independent raw quote cross-check | 已有 Baostock/community normalized snapshot | footer 显示仅覆盖 2024-08 至 2026-02，本轮没有读取数值 | 只有 schema 可见，没有开发期可核验样本 | [metadata inventory](market_source_inventory.json) | **不能用于本阶段独立 raw-source 对照** |
| ST / risk warning / suspension / termination | `historical_instrument_state_v2.yaml` scope/canary；readiness false | 必须有 published_at/effective_from 与冲突解决；当前名称不能倒推历史 | unknown 不可转 false；现代码能力不等于九年覆盖 | 既有 instrument_state_evidence 可复用 | **九年逐日状态包未认证** |
| board、listing regime、IPO session、par value | prefix 仅辅助；需 dated listing/ref-data | 盘前已知、可追溯至原公告；注册制按发行制度而非仅交易日期判断 | lot 用 raw shares；early2015 沪市须真实面额 | 交易所规则可核查，个股历史字段尚缺 | **特殊日及早期面额数据未齐** |
| upper/lower limit、ex-reference、特殊日 | [规则表](dated_price_limits.csv) 与官方条文 | 盘前价格约束，不能从次日 close/change 推算 | raw CNY/share，分币 half-up；special session 不套通用 ±10% | 普通 regime 有规则支持；逐股逐日限价源未认证 | **当前严格 adapter 仅接受有可靠双边价格界限的普通日** |
| dividend / bonus / split / rights / conversion | 定向代码/config 搜索仅找到待采集 dividend API 规划；没有完整 dated event bundle | record / ex / credit / pay / listability 时点不同；事后复权因子不是事件账本 | raw shares、CNY cash、receivable；不能重复计息/分红/调股数 | 事件会计原语与手算 oracle | **真实事件包、配股/转换/终止及 Qlib receivable 估值桥未完成** |
| held-stock continuation | 当前输入 keys 是候选池，不是持仓全集 | 离池后仍须行情、状态、公司行为；future label finite mask 禁止参与 | 缺 held quote 时 begin_session 直接失败 | adapter 合成测试验证 | **全池 union holdings 后的九年覆盖未证明** |
| opening trade evidence / auction capacity | 当前 canary 只有 daily bar | raw open 可能是当日首笔而非 09:25 集合竞价；日后是否有交易不能倒推开盘有成交 | open_evidence 需来源；目前未认证 | 日线开盘参考近似，不能称真实 auction fill | **开盘证据/近似准入仍待解决**；队列重建延期 |
| ADV20 warmup | 代码强制前20完整开发交易日 | 不取当日量；停牌已证实零量纳入分母，缺值停算；新上市不足20日不可用 | shares 为唯一候选，1% 只是工程 cap | 合成因果性测试 | **2015 起始 warmup 尚未批准/准备**；本轮未读2014 |
| benchmark / AUM | 仅 [24 个合成可执行性场景](synthetic_aum_feasibility.csv) | 没有真实 benchmark 路径或 B 排名 | 100万/500万/1000万 ×200/2000名 ×固定合成价格 | 工程算例，不是收益优化/容量估计 | **真实全池 EW lot/费用/ADV 覆盖待核验** |

523/523 的检查仅说明：当前选定样本与这组单位换算相容；它不证明 event accounting、PIT 或所有股票/年份均正确。
其中量额隐含均价与 high/low 比较，`ohlc_order_pass` 仅检查 high≥low 及 open 落在该区间；不包含 close 的独立一致性认证。
未为了提高 coverage 把 14 个未知缺值改为零，也没有删除这只股票或其年份。完整市场数据不足时，本阶段按阻塞收尾。

## 3. Timing Contract：A/B/C 物理分离

默认时区 Asia/Shanghai；机器 schema 使用已明确约定的本地 naive timestamps，拒绝混合时区。

| 类别/字段 | signal_time / known_at | order_time | executable_at | valuation_time |
|---|---|---|---|---|
| A：frozen t score、membership、昨收 | signal_time 为 t 日收盘之后；known_at 为输入实际发布后，须早于次日盘前订单 | 候选、排序和固定订单数量只使用 A | 不能事后用 open 重新排序/扩大候选 | 不适用 |
| A：board/listing/ST、公司行为通知、上下限 | state_known_at < order_time；effective date 单独满足；future E4 每字段须有 provenance | next-open 安全检查与最坏价格现金预留 | 已下单意图只能按成交约束被拒/部分成交 | 不适用 |
| A：ADV20 | adv_asof < order_time，窗口为过去20完整交易日；当天量无路径进入 | 唯一候选 cap=1%×ADV20 shares | 同股同日累计已成交买卖股数扣减 cap | 当前 volume/amount 只在日终用于后续窗口 |
| B：raw open / open_evidence | 不用于事前候选排名/目标预算 | 订单应已确定 | 仅判断 NO FILL、方向限制与实际成交价；缺失不回退 close | 不适用 |
| C：raw close、high/low、全日量额、change、收盘推断限价 | 只能日终知道 | **不能影响当日开盘订单** | **不能使用**；本实现连 full-day zero-volume veto 也没有 | 合法 close 用于日终估值；缺估值需独立停止/审核，不能变成交价 |

本次进一步收紧初版：不利用全日零量在事后决定开盘成交，要求单独的 open_evidence。
若数据仅 daily open 而无竞价证据，必须先明确可接受的 open-reference 近似及失败条件；不能自动把正数 open 标为认证竞价。
现 schema 只有一个聚合 source_id/known_at；真正 market dataset 必须额外提供逐字段 provenance/timing companion 表，这也是 readiness 缺口。

`EconomicOpenExchange` 不调用父类 `get_deal_price`，直接取该日 approved raw open；没有 execution→close fallback。
Qlib daily bar 的 end_time 可能延伸到下一个交易日前的周末，适配层验证区间只包含一个批准的交易 session；不是读取周末或未来行情。
预演恢复所有可变 T+1、费用、cap、现金预算、audit 状态。调用者复制的 Position 可改变，正式 Account 不变。
交易日必须显式 `begin_session` 且严格向前；同日再次开始会失败，防止当天买入重新变为可卖。
同一开盘批次买入额度只来自 batch-start cash；当批卖出所得不补充额度，属于保守实现选择，不是声称法规禁止资金当日复用。

## 4. T+1 / 股数 / 持仓连续性

Qlib 内部在此专用 adapter 采用 `$factor=1`，amount 就是 raw shares；避免 adjusted amount 与显式公司行为重叠。
监管可卖量为 `opening_sellable - sold_today`。买入只增加 bought_today 与真实总股数，不提高当天可卖量。
下一交易日已完成交收的普通买入才进入 opening_sellable；跨周末以交易日推进。未知冻结、司法限制、延迟公司行为到账不能当作普通买入到期。

已测试：老100＋新100、同日再买、多次卖出/部分卖出、次日解锁、跨周末、proportional split 后可卖/不可卖子账同步。
hold_thresh 仅偏好门槛；原生 Topk 合成测试保留两者区别。应卖但跌停/停牌/T+1 未可卖时，股数继续存在，pending sale 占用槽位。
quote universe = signal candidates ∪ actual positive holdings；缺 held quote 立即失败；不引用 score 是否有成熟标签。
模型换年不会清仓。2023-12-29 保留真实库存，不发跨年清仓单；需要2024执行的信号标 `out_of_execution_boundary`。

普通主板/创业板买入100整数倍；科创板限价委托200起、1股递增，余股一次处置。
当前 partial fill proxy 对截断后的买量再次执行最低股数/lot 检查，是保守日线近似，不声称真实撮合的每笔 partial fill 必须满足下单最小量。
特殊证券、订单上限、碎股公司行为及 broker 可卖明细均须在真实适配前验证；当前没有 general-purpose 经纪订单模拟。

## 5. CORPORATE_ACTION_ACCOUNTING_CONTRACT

唯一方向为 **raw prices + raw shares + explicit dated events**。不使用 adjusted price 计算收益后再加 dividend，也不把 factor 变化当成送股。

| 事件 | 权益/会计处理 | 当前支持与未就绪部分 |
|---|---|---|
| Cash dividend | record-date 持股确定 entitlement；ex-date 增 receivable，pay-date receivable→cash；日期可不同 | 原语实现与手算通过；真实 record holdings、税项、Qlib receivable 估值桥未集成 |
| 10送X / bonus | record entitlement × X/10 得新增 raw shares；credit/listable 日期分别控制总股数与可卖股数 | 已测同日、全体 entitlement 的比例样例；**不能将持仓全量比例乘法用于不同 record-date 或延迟到账真实 bonus** |
| Proportional split / consolidation | 总股数与旧可卖、新不可卖子账按同一倍数换算；raw quote 自己反映除权 | split 原语通过；真实股数 rounding/碎股现金仍需事件合同 |
| Pure adjustment-factor rebase | 不产生现金/股数变化 | 因子变化不调用任何事件；synthetic 价格单位变换单独测试 |
| Rights issue | 先冻结认购/不认购、权利价值、cash outflow、credited/listable time；未知时阻断 | **未实现，明确 unsupported**，不能把除权损失静默忽略 |
| Share conversion / delisting cash | 旧证券到新证券数量比、补价、现金或权利应收须有真实公告/生效与到账 | **未实现，明确 unsupported**；不做零价清算或无限期可实现 ffill |
| Suspension during event | 停牌不阻止已知事件的应收/到账处理；无交易与有事件分别记录 | cash-dividend synthetic 覆盖；真实 suspended inventory quote/event reconciliation 待准备 |

手算：100股×10元 → 除息后100股×9元＋100元应收＝1000；支付只把应收转现金。
200股（老100/新100）拆为400股时，老可卖200/新不可卖200；价格10→5保持2000元证券价值。
同日已认证 entitlement 的10送2合成例：400→480股，价格5→5/1.2保持2000元；这不授权按任意 factor 推断分红或送股。
事件 ID 防重复支付/应用。股息所得税本阶段未实现，未来若沿用须明确 before dividend-income-tax，不能称全税后净收益。

**CorporateActionBook 是小型事件原语与 oracle 接口，不是已经完成的真实账户 corporate-action engine。**
因此即使本节测试全过，E2 仍 BLOCKED，不能进入 E4。

## 6. 历史费用与母单

逐项期间、side、basis、最低费、来源与信心见 [Dated Fee Schedule](dated_fee_schedule.csv)。
2015 沪市按成交面额、深市按成交金额的制度事实现补强为上交所官方三方答问；但个股面额、历史券商留存/最低费/舍入仍未完整验证。
来源是 [2015 官方答问](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20150912_3988866.shtml)，不是套用当前过户费。

2022 调整使用[上海政府网站转载](https://jrj.sh.gov.cn/SCDT197/20220429/f715759a877b4158812eb6df70ccb49e.html)，
页面注明来源新民晚报，因此证据等级是 **政府托管新闻转载**，不是中国结算原件。
2023 卖出印花税切换依据[税务总局公告](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html)。

佣金候选万三、最低5元；[2002联合通知原文](https://www.chinatax.gov.cn/chinatax/n810341/n810765/n812203/200202/c1209808/content.html)
支持最低标准以及佣金包含经手/监管费的结构，但不证明用户券商实际费率是万三。
本阶段不把各种经手、监管费再次加到已含这些项目的佣金之上。早期深市历史费用打包方式仍需核对，不能 double count。

MVP 近似：同一交易日、证券、方向预先合并为一个母单；子 fill 按累计成交额重算母单总费，仅扣差额。
不同日期不合并；若未来产生独立母单，应加入 mother_order_id，不得任意把全日独立委托都折成一笔收费。
目前没有拿到用户指定 broker 的历史成交单；常见口径不能升级为统一法定“每个撮合成交/母单”的定义。
券商系统可配置分笔/合笔的现象提示必须明确近似，最终仍以 broker 历史费表/交割单为准。

合成例：一张10000元买单先4000再6000，佣金第一次5、第二次0，总计5元；2023-08-28后过户费总计0.10元。
采用母单每组件累计 half-up 到分的近似；这不是已确认的所有历史收费 rounding。
无成交无费。买卖印花税分侧；implicit cost 在 raw open 成交后另扣现金，成交价不虚构越过限价，不重复增加 spread/impact。
explicit dated fee 是 base 合同的候选；10bps/side implicit 是未冻结工程假设，20/40bps 留未来 stress，绝不是法定费率。
默认 adapter 的 implicit_bps=0 表示 E2 单元验证显式费用；它不是新的零滑点 E3 推荐或任何真实回测默认授权。

## 7. Dated limits 与制度边界

[Dated Price-Limit / Board Table](dated_price_limits.csv) 覆盖 ordinary main/ST、改革前后创业板、科创板、IPO 与特殊日的处理方式。
开发期内恢复上市/重新上市、退市整理首日、新旧创业板退市过渡等不能仅凭 board/ST 计算。
未知/特殊状态的 resolver 报错；strict adapter 当前只接受有明确普通日价格边界的 rows，不能把特殊日排除后宣称完成整个历史组合。

本轮实际取得并读取上交所2023正式附件：3.1.4 交收前卖出限制、3.3.8 股数、3.3.13 普通限幅与例外、4.4.10风险警示、6.1.6/6.1.7 科创板。
[发布通知](https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/c_20250612_10824490.shtml)
的正文规定生效锚点为注册制首只主板上市日；结合[2023-08官方回顾](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20230810_5725020.shtml)确认2023-04-10，不能用页面元数据02-17替代。
这只证明当时条文，不能把2023条文逐条无条件回填2015。

创业板2020-08-24切换及既有退市整理例外由[正式答问](https://www.szse.cn/aboutus/trends/news/t20200821_580924.html)
和[风险警示过渡通知](https://www.szse.cn/disclosure/notice/general/t20200710_579459.html)支持；网页通过直接HTTP获取并检查正文，web工具超时不被写成原文不存在。
科创板 lot 与限幅见[2019上交所投教](https://edu.sse.com.cn/tib/ysptj/c/4869120.shtml)。
旧 IPO 开盘集合竞价控制与日内控制是两种界限，见[历史机制说明](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20150912_3988762.shtml)；不把日内44%范围用于开盘订单。
另记录2016市场级熔断制度缺口：[正式实施通知](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20151204_4019218.shtml)、
[暂停通知](https://english.sse.com.cn/news/newsrelease/c/4947693.shtml)。日内熔断不能事前决定开盘是否下单，需独立 dated market-session metadata。

深交所2023正式附件初版URL本轮直接HTTP为404，另一个通知镜像也404；没有用2026规则替代，仍列 source gap。
所有已获取原件的字节 hash 与失败记录见 [source receipts](rule_source_receipts.json)；raw HTML/docx 留在 ignored outputs，报告只保留归纳和来源。

## 8. Synthetic oracle / Qlib validation

测试以临时 synthetic provider calendar 和内存 quotes 为输入，D.features 被 monkeypatch 为一调用即失败，保护真实项目值。
Qlib `Account(benchmark_config={'benchmark': None}, port_metr_enabled=False)` 显式禁用基准查询和组合报表。
不使用旧 `create_account_instance(..., benchmark=None)`：它传空 dict 时会触发默认 CSI300 查询，已由测试拦截发现。

独立手算检查 raw shares、cash、partial fills、母单费用、T+1、direction-aware limits、单位及事件守恒；没有以同一函数调用两次冒充 oracle。
原生 Topk 真正调用 `generate_trade_decision`，使用合成 2持仓/1候选：验证 n_drop 不强制换出更强 incumbent、hold_thresh、卖买序列以及预模拟纯性。
这是 Topk 工程检查，没有真实 B 输入、没有50/5参数，没有第三策略 NAV。
还确认原生 Topk 在 hold_thresh 阻止应卖仓位时，仍可能生成按计划卖出数量预选的买单；
因此不能把它直接接作 pending-sale占槽的正式 selector。E2 的 vacant_slots 原语按 actual holdings 计算，未来E3 selector必须使用实际槽位；本轮未实现真实策略selector。

| 高风险 case | 证据 |
|---|---|
| same-close禁止、next-close不影响open、missing/open_evidence/suspension拒绝 | `test_economic_qlib_runtime.py` timing/price cases |
| limit-up买拒/卖可、limit-down卖拒/买可 | 实际 Qlib direction tests；明确队列近似 |
| T+1 old/new、多次加仓、partial、周末、split | `test_economic_execution_contract.py` 与实际 Account cases |
| minimum lot、minimum commission、partial aggregation、shared ADV cap | 纯函数与实际 Qlib cash/share conservation |
| 2015/2022/2023费用、创业板切换/ST/IPO特殊日 | 手算 dated fixtures；unresolved 特殊日断言抛错 |
| dividend、bonus、split、停牌事件、price/factor变化不重复入账 | 事件原语手算；不冒充完整真实 corporate-action bridge |
| pending sale占槽、held universe exit、跨年不断仓、terminal/no2024 | membership helper、begin_session、boundary tests |
| no label / score join / NAV output | exact schema、binary reader pre-open deny、合成输出schema断言 |
| 独立源/真实全池数据就绪 | **尚未通过，不以 synthetic 代替** |

## 9. 唯一建议与待决策缺口

这些是 E3 建议，均未冻结：

- Signal：B494；10/20候选等 E1真实结构与独立重放后再判断，目前 `inconclusive / awaiting user run`。Monthly top-decile、EW保持待审议。
- AUM：保留**1000万元**这一唯一工程候选，不声称有真实全池 feasibility 证明。
  同为2000股全池、95%资本分配，每股预算分别475/2375/4750元；最低佣金会影响小权重。
  合成均价5元时，100万方案连一手也不足；1000万仍无法在每股100元的合成全池中逐票建仓。不能由这个算例推断真实多少股票不合格。
- ADV：候选 **过去20完整交易日 shares 均值，1% cap**；missing暂停准入、已认证停牌零量纳入、新股不足20日不可用。不是竞价容量估计。
- Fee：万三/最低5元＋dated税费；implicit10bps/side仅建议，20/40留stress。early2015面额/收取口径先解决。
- Execution：next-open raw-price reference、无fallback、方向限制、盘前现金预算；opening evidence/日线近似须明确后才有资格冻结。
- Benchmark：全池 monthly EW reference仍为候选，**当前未证明可执行**。先用认证的全池 quote 做一次纯lot/fee/ADV feasibility，再决定是否提出替代方案；不按收益换基准。

**Blocker**：九年PIT状态/特殊限价；完整公司行为与raw账户桥；独立源/全池quote覆盖与单位；score盘前可得性；early2015费用面额；2015 warmup；开盘证据；真实全池benchmark feasibility。
**Acceptable approximation（待E3审议）**：日线open-reference、方向保守拒绝、合并母单收费、批初cash、ADV代理容量、partial lot保守处理、佣金/implicit假设。
**Deferred improvement**：竞价/逐笔队列与冲击模型、优化器风险数据、真实broker对账接口。延期不等于忽略持仓终止或公司行为损失。

本轮没有生成 executable market dataset，也不声称已经完成全部 production corporate-action/state integration。
完成了可运行的受限原语、实际 Qlib 验证与足以判定阻塞的数据证据；继续大规模行情补采或策略冻结之前，需先审阅上述研究定义缺口。
E3 NOT AUTHORIZED；E4 NOT AUTHORIZED；2024+ NOT AUTHORIZED。
