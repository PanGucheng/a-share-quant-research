# Replace / Adapt / Keep

Replace 表示后续接受迁移时的目标职责，不代表现在删代码。源码固定在
[官方 a5fb4e4](https://github.com/ricequant/rqalpha/tree/a5fb4e43879c381e61131399dcc094d495c7080a)，
下表路径均相对其仓库；实现与安装包 20 个核心文件 LF hash 一致，见 [environment receipt](ENVIRONMENT.json)。

| 当前能力 / 项目模块 | RQAlpha 实现及实际发现 | 决策 | 本轮证据 / 剩余责任 |
|---|---|---|---|
| CoreSession account/cash | `portfolio/account.py`、`portfolio/__init__.py`；原生冻结、释放、应用成交 | Replace 通用记账 / Keep 事务外层 | A/B/C 真实引擎；全 checkpoint 仍待接线 |
| RawSellableLedger / T+1 | `mod/rqalpha_mod_sys_accounts/position_model.py`、`position_validator.py` | Replace | B 当日拒卖、次日释放；instrument.market_tplus 必须显式为1 |
| lot_quantity | `model/instrument.py`、`mod/utils.py`、stock API | Replace/Adapt | B 150→100；STAR 最小200/步长1 等须真实 board master，未做全板历史验收 |
| EconomicOpenExchange | `sys_simulation/matcher/base.py`、`bar_matcher.py` | Replace/Adapt | A/C 原生撮合；保留原始价格/状态 gate |
| t close → t+1 open | 日频 `next_bar` 自动降为 close；原生 open_auction 可用 | Adapt 跨夜意图 | A 已验隔夜顺序；禁止仅设置 next_bar 即宣布成功 |
| ADV / volume caps | matcher 支持 volume_percent、partial fill；Market 残量取消 | Adapt | C 容量/现金部分成交；代理容量不是真实 auction；跨日重下单不能误当同一母单 |
| 多卖后买/现金释放 | broker 同步事件和 Account 原生更新 | Replace | 两卖单后买入通过；这是最小顺序探针，不是完整 target executor |
| MotherOrderFees 最低佣金 | native CommissionMixin 按 order_id 累计；浮点不按分舍入 | Adapt | C 原生成交两次佣金5/0，独立费用序列5/0/2.5；保留项目 ledger |
| dated fees/个人费用 | `interface.py` TransactionCost.other_fees 可表达过户费 | Adapt/Keep schedule | 万2.5/min5、2022过户费/2023印花税变点通过；早2015仍 fail closed |
| EventPosition cash receivable | StockPosition 应收计 equity、payable 入 cash | Replace 受支持子集 | D 真事件条款+合成价格；非相邻登记和多支付日批次不能直接映射 |
| 红利税 | StockPosition 持仓队列按月/年期限，默认开关独立 | Adapt/Verify | 20%短期事件探针；不是完整2015制度/税务验收；主MVP仍明确gross口径 |
| split/bonus | 同一 position 即时数量/成本调整；ROUND_HALF_UP | Adapt/Keep pending rights | E 整数即时机制通过；真实延迟上市直接映射不兼容、fractional需证据 |
| rename_identity / R2 | `get_share_transformation` + settlement 比例转换 | Adapt/Verify | F 简单比例、成本、mark、cash守恒；旧pending entitlement迁移/真实条款未验 |
| terminal_unknown | 默认按市值返现；关闭返现仍清数量 | Keep gate | F 反例；缺终止条款必须在 settlement 前 HALT_RETAIN |
| rights / restructuring | 没有本轮验证的通用事件会计路径 | Keep targeted evidence | 不将未知折算为0、不因退出候选池丢权利 |
| suspension/ST/limit/IPO | DataSource供状态，risk拒停牌，PriceBoard供限价 | Adapt/Keep rules | suspension/upper limit通过；NaN限价native不阻塞，adapter必须拒绝 |
| raw units / factor / precision | 框架消费价格/量，不认证源单位或异常 | Keep existing overlays | A复用C1封存输入；不乘复权factor重复记权益 |
| historical PIT / live freshness | 框架没有项目source receipts/可得性契约 | Keep | historical_session_effective≠精确发布时间；不升级为live资格 |
| held-continuity / signal exit | Account持仓与策略universe可分离 | Adapt/Keep | D原股卖尽后应收仍保留；所有证券/权利行情覆盖仍由R1–R3检查 |
| persistence/order lifecycle | Account/Position/Order/Broker get_state/set_state + PersistHelper | Replace mechanism / Keep integrity | 应收与fee手动restore通过；完整broker+fee+guard原子恢复尚未验收 |
| canonical/B494/训练/预测 | 不属于 RQAlpha execution 职责 | Keep Qlib | 零改动，LightGBM合同25文件复核通过 |

整体状态：**FEASIBLE WITH ADAPTERS**。真实数据字段缺口与完整事件路径未因替换框架消失。
保留现有 [E2 Matrix](../economic_translation_mvp/e2_hard_closure_v1/MATRIX.md) 的 authority；本矩阵不改写 Core Ready。
