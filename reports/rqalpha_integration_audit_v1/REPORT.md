# RQAlpha 迁移审计结论

2026-09-16，基线 `e06f9d1`；官方 RQAlpha **6.4.0**，源码锁定
`a5fb4e43879c381e61131399dcc094d495c7080a`（2026-09-07）。

**RQALPHA INTEGRATION FEASIBLE WITH ADAPTERS。** 建议采用 `Qlib Research + RQAlpha Execution`
的职责方向，停止继续扩建通用自研撮合/账户引擎。当前 PoC 不足以切换 authoritative backend，
没有任何现有模块可在本轮直接删除；旧实现及证据仍是回归 oracle。

[Matrix](MATRIX.md)、[Canaries](CANARIES.md)、[环境及 Skills](ENVIRONMENT_SKILLS.md)是本报告的组成部分。
[机器结果](CANARY_RESULTS.json)包含原生运行的 trades、cash、positions、orders 与 source access；
没有策略收益、NAV 时间序列或参数排序。

## 对原方案的修正

1. **日频 next-bar 不是开箱即用的次日开盘。** 官方 SimulationMod 将日频 `next_bar` 改成
   `current_bar`；测试确认当日 close=12、open=10 时在当日 12 成交。采用策略意图跨夜保存，
   次日 `open_auction` 原生入口成交，已在两日 canary 验证。日级事件时钟默认为 00:00，不能
   把它宣传为真实 09:25/09:30 时间戳。[官方配置处理](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/rqalpha/mod/rqalpha_mod_sys_simulation/mod.py)
2. **分红有应收功能，但不等于本项目全部登记语义。** 原生实现按 ex-date 当时 quantity 建立应收；
   非相邻 record/ex 场景缺少独立 record-close entitlement。相同 ex-date 多事件还隐含同一 payable-date
   假设。此类输入必须拦截或单独适配，不能简单填入接口。[StockPosition](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/rqalpha/mod/rqalpha_mod_sys_accounts/position_model.py)
3. **bonus 不普遍等于 split。** 原生 split 在 ex-date 立即更新数量、可卖量并 ROUND_HALF_UP；
   真实 SH600000 2016/2017 红股次日才上市，直接映射会提前释放股份。延迟上市、零碎权益继续受控。
4. **关闭退市返现也不等于保留持仓。** 原生 settlement 遇到无转换条款的退市证券，默认按市值返现，
   关闭返现仍会清空 quantity。必须在原生 settlement 前拦截未知 terminal，并保留最后完整账户。
5. **默认 fees 有部分历史语义。** 它支持最低佣金和 2023-08-28 印花税切换；不足在过户费、项目舍入、
   early-2015 面值计费、母单 checkpoint 等，不能笼统写“完全不支持历史费用”。本 PoC 复用项目
   `dated_fees` / `MotherOrderFees`，只通过官方费用接口接入。[费用实现](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/rqalpha/mod/rqalpha_mod_sys_transaction_cost/deciders.py)
6. **未知限价不能交给默认行为。** 原生限价 helper 遇 NaN 返回未触限；bar volume 为 NaN 的默认分支
   也可能不施加容量限制。adapter 必须先验证状态、限价、价格、容量。[限价实现](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/rqalpha/utils/price_limits.py)

## 十五项问题的答复

| 问题 | 结论 |
|---|---|
| 1. 能否成为 authoritative historical execution/account backend？ | 通用 A 股交易和原生账户路径可行；正式 authority 尚未验收。需要完成下述迁移接线与 actual exposure gates。 |
| 2. 哪些自研模块停止扩展？ | 通用 EconomicOpenExchange 撮合、T+1、现金冻结释放、通用 order/position lifecycle。保留已有代码做 oracle，新的通用能力优先官方接口。 |
| 3. 哪些可直接删除？ | **目前没有。** 没有全路径等价和回退验收，不弃用 CoreSession / EventPosition，不删除 E2 evidence。 |
| 4. 哪些保留为 adapter？ | raw normalization、identity/lifecycle、historical inputs、state/limit mapping、dated fees、母单 rounding、跨夜意图、开盘容量约束。 |
| 5. E2/R1/R2/R3 保留哪些？ | 全部 provenance、历史/实盘可得性区分、R1 估值连续性、R2 身份/终止连续性、R3 权益连续性及 HALT_RETAIN。RQAlpha 不认证数据。 |
| 6. 自定义 DataSource 工作量？ | 普通日级只需 calendar/instruments/raw bars/state/limits/event arrays 的窄接口；本 PoC 已可运行。生产难点在生命周期、phase visibility、未知状态和历史权益，不在写一套新回测引擎。不能把 fixture adapter 行数当生产报价。 |
| 7. 已有三项数据是否够？ | 足够支撑固定普通 canary 和若干可信现金事件。**不足以认证完整 2015–2023 任意实际持仓路径**；完整 inventory 不等于语义闭合，不需重采长扫描。 |
| 8. 缺哪些字段/证据？ | 逐资产真实 listing/delisting/代码有效期；普通/特殊 session 独立限价覆盖；实际开盘流动性；rights/转换/terminal 条款；record entitlement、延期红股可卖日期及 fractional allocation；明确税口径。详见 Matrix。 |
| 9. 费用接口能完整表达个人与历史费用？ | `TransactionCost(commission,tax,other_fees)` 足以承载；万2.5/min5及已有税费变点已验。早期2015证据仍拒绝，完整日期资格与 broker-specific rounding 不因框架迁移自动获得。 |
| 10. dividend/split/identity 是否一致？ | 相邻 record/ex 普通现金分红、整数即时 split、简单比例转换通过；非相邻登记、延迟上市和复杂身份迁移不一致。F 是 synthetic，不是真实 R2 验收。 |
| 11. fractional/rights/terminal 缺口？ | fractional 默认四舍五入、rights 无通用原生认购路径、terminal 默认行为不符合 retain；先 gate，再只处理 actual path 命中案例。 |
| 12. 与自研相比的成本？ | 迁移增加一次 API 映射、冻结版本和对账成本，但可减少长期维护撮合、T+1、cash/order/position 状态机的工作。事件证据成本不会消失。无完整周期性能或工期测量，不给虚假精确节省比例。 |
| 13. 是否建议采用推荐架构？ | **有条件建议。** 先接受职责拆分和停止通用重复建设；后续单独授权最小生产接线与等价验收。当前不切换 backend。 |
| 14. 是否值得安装 basic Skill？ | 可作可选文档导航，优先级低于锁定版本源码；面向 Claude、偏 AlphaPlus，需限制触发范围和调整 shell/agent 指示；许可证引用文件缺失，暂不自动安装。 |
| 15. 是否需要 RQData 等商业组件？ | 本轮不需要；使用自有 DataSource 的 PoC 完全离线运行。未来个人实盘/商业用途的 RQAlpha 授权问题须单独确认，不能由“没用 RQData”推断许可。 |

## 数据与接口边界

已有 `SH/SZ + code` 必须经经济资产 ID / alias 有效期映射后转为 `code.XSHG/XSHE`；单纯改后缀
不足以处理 SH601313 等身份问题。Instruments 需真实 board、market_tplus=1、最小手数、上市与退市日期。
源码的 `market_tplus` 缺失默认 0，不能漏填后再宣称 T+1。

raw OHLC 以元/原始股，volume 以股，amount 对应 total_turnover 元；复权 factor 保留审计信息，
不能再乘入已由 corporate actions 更新的 raw shares。已有 normalization/precision overlay 继续作为
唯一输入适配来源，canonical/B494 不动。fixture 只包含测试所需记录，instrument 上市日等周边属性明确为
synthetic；不能把 A canary 解释为完整真实证券 master 的认证。

流动性 PoC 将严格 prior ADV 的一小部分作为明确标注的容量代理，经开盘接口提供；没有真实 auction volume。
这是验证容量约束接线的工程假设，不是新增策略参数，也不认证开盘成交可得性。真实容量语义应在已授权 MVP
近似框架中明示并冻结；日频当日总量不得倒灌为盘前可见容量。

现有事件库 23,488 个普通税前条款键、602 个未决键/533 个资产，以及 rights/conversion/terminal 可信总数
unknown 的结论沿用[已封存事件审计](../economic_translation_mvp/e2_hard_closure_v1/EVENT_INVENTORY.md)。
本轮只核验三条 SH600000 事件投影，不重新统计或清理全集，不从空表推断无事件。

## 正式切换之前的剩余条件

这些是 **migration acceptance gaps**，不重开 E2 全库 scope，也不要求清理全部特殊股票：

- 将既有 source-bound phase/state/identity/limit adapters 接到 DataSource，禁止 PoC synthetic master 进入生产。
- 将跨夜意图、日内现金顺序、保守容量和 fees 接线为冻结执行合同；缺 open/limit/state 必须拒绝执行。
- 将 event_guard 放在持仓变化及 settlement **之前**，把原生账户、未结权益、跨夜意图、fee ledger、broker
  和访问 receipts 作为同一事务 checkpoint；证明异常日 rollback/replay 不丢现金、旧证券或应收。
  当前 guard 仅独立 refusal probe，**没有**完成生产 HALT_RETAIN 外层接线。
- 按实际 exposure 判定普通现金事件可原生处理，延迟 bonus/record gap/复杂转换/terminal 则保留 targeted adapter
  或停机。当前 synthetic restore 不等于全量崩溃恢复证明。
- 冻结版本和接口回归，审核授权条件后，才考虑一次独立授权的策略 actual-path 验收。

现有 CoreSession 的 whole-day rollback 不能因框架有 get_state/set_state 就直接删除。官方默认 persistence
注册 portfolio、broker、context 和 Persistable mods，不自动保存本 PoC fee decider；restore helper 还会记录部分
restore 异常后继续返回。项目必须维持完整性校验，不接受部分恢复为成功。
[官方 persistence](https://github.com/ricequant/rqalpha/blob/a5fb4e43879c381e61131399dcc094d495c7080a/rqalpha/utils/persisit_helper.py)

## 验证与停止点

27 项本地 PoC + 26 项官方 synthetic unit tests 通过；仓库fast层46项、新代码 Ruff、pip check、文档链接和主运行绑定校验通过（共99项测试）。
27 项 PoC 的 PASS 包含“成功识别不兼容并拒绝”测试，不意味着 A–F 的真实路径全部 READY。
完整仓库 full tier 未运行：本轮独立实验不修改既有执行/研究代码，使用 outcome-isolated 套件，
避免长训练资源竞争与旧实值验证。官方 bundle integration tests 未运行；其中有 2024+ 样本，仅读源码未取行情。

主 run contract 及 25 个绑定文件逐 hash 保持不变；没有读取正在生成的模型/predictions，没有干预训练进程。
软件依赖仅安装进独立 venv。没有长期采集、候选经济回测、收益评价、Strategy V2 选择或正式迁移。
只 commit/push `audit/rqalpha-poc-20260916`，保留 main 与 E1/E2/E3/LightGBM 状态；停止等待人工审核。
