# E3 Strategy Freeze Preparation 与结构预验收

2026-09-15，实施基线 `main@33c43bd`。
**E3 STRATEGY FROZEN / PATH PREFLIGHT PENDING。TARGET STRUCTURE REQUIRES HUMAN REVIEW。**

已冻结一个可解释、可复现的研究定义，尚不能宣布 actual path 或结构设计通过。
本轮最重要的发现是：单次最多替换一只几乎持续成为约束，目标低换手主要受到这一上限限制。
不因发现积压修改 K、buffer、周期或 replacement cap，不运行第二候选。

## 冻结与实现

唯一候选：**100,000 CNY / K8 / Hold16 / 5 trading days / max-drop1 / near-EW**。
[freeze.json](freeze.json) 的 SHA256 为
`6dcd4bbe70f21d615d2d28659c629bd1543825dc940e65c3593980652691e8c2`，
在真实 B494 分数访问前生成。完整字段、来源、近似及边界见[冻结计划](../../../docs/ECONOMIC_E3_FREEZE_PREPARATION.md)。

复用 BoundedScores 的封闭 B494/keys reader、E2 Decision/eligibility、dated_fees、lot_quantity、
MotherOrderFees；新增小型成员 intent/confirmation 函数与独立个人预算函数。
已有 CoreSession/EconomicOpenExchange、canonical、B494、E1 和 E2 receipts 没有修改。
新费用预算已验证万2.5、最低5元与10bps单侧现金费用代理，**尚未接入真实策略 CoreSession**；
旧引擎的万三和批初 buy budget 不能被误报为本次策略的执行参数。

只在原 Top8 内入选；保留完整 pool 排名，gate 后不重排研究池。
正常退出选择最差排名，仅一次尝试；失败不试第二只、不允许新增替代仓位。
pending rights/应收继续占 economic identity slot；成交确认前不释放 slot。
第一次 scheduled decision 可初建八名，此后每次最多补一名；保留现金、不重置老仓等权。
年度模型切换不重置 phase、持有段或权利，2023边界不强平。

附件的 E1 Top10/Hold20 更正为 **百分位10%/20%，约200/400只**。E1 的63.3%下降不是
8/16只的预期降幅；五日相关0.788只是排名稳定性，不是最优频率或收益衰减证据。
本轮不读经济结果；既有 D3-A 已揭封的研究历史仍保留，不能称整个项目重新 outcome-blind。

## 单候选 target-only 结果

2015–2023固定2,189日、4,377,824个B分数/keys。没有运行 E1 原 study 或价格长扫描。
仅理想目标成员状态转换：每个目标变更假设立即实现，**没有执行 eligibility、整手、现金、费用、
公司行动或可成交性认证**；不计算/保存股数、现金、NAV或回报。

| 结构量 | 结果 |
|---|---|
| scheduled decisions | 438；以首个 signal 日为相位，次日改变目标，年度不重置 |
| 初建后目标退出 | 437，等于所有后续决策次数 |
| 仍有退出积压的决策 | 435 / 437（99.54%）；口径为本次选定一只后仍有 rank>16/缺席的目标成员 |
| 目标持有段 | 437个已结束，8个边界右删失 |
| 已结束目标持有期 | 平均39.36个交易日，中位30日；不是实际持仓周期 |
| buffer保留比例 | 7.41%，分母为scheduled decision前的目标持仓人次，分子rank9–16人次 |
| 日均目标churn，剔除初建 | 2.498%；固定八名额口径为(新增+退出)/16，无价格加权 |
| 目标欠配 | 初建后始终8名；目标空位最长0日；不能据此断言实际现金无闲置 |
| 年界 | 8次，目标状态/持有期/五日相位连续 |

| 年份 | 决策数 | 目标退出 | 目标新增 | 有退出积压的决策 |
|---|---:|---:|---:|---:|
| 2015 | 49 | 48 | 56（含初建8） | 48 |
| 2016 | 49 | 49 | 49 | 48 |
| 2017 | 49 | 49 | 49 | 49 |
| 2018 | 48 | 48 | 48 | 48 |
| 2019 | 49 | 49 | 49 | 49 |
| 2020 | 49 | 49 | 49 | 48 |
| 2021 | 48 | 48 | 48 | 48 |
| 2022 | 49 | 49 | 49 | 49 |
| 2023 | 48 | 48 | 48 | 48 |

这个候选在名额和转换逻辑上没有发现算术矛盾，但有明显的退出积压，需要人工判断其研究含义。
不能说已验证“适度 buffer 减少 boundary noise”：这里 replacement cap 几乎持续饱和，
实际结果不支持把低换手主要归因于 buffer。未运行无cap/另一K或另一周期，因此不能分离因果贡献，
也不能与 E1 不同宽度、频率、成员口径直接量比后判定改善。
没有因为该现象自动增加cap；若人工决定修改，必须另立v2，不把v2伪装成v1验收。

## 实际路径依赖检查

按事先固定的真实策略起点：**2015-01-05 signal → 2015-01-06 session**，Top8依次为
SZ300246、SZ300245、SZ002196、SZ300331、SH600070、SZ300354、SZ002401、SZ300220。
只检查这八个ID的两日身份/质量元数据及一个session的原始ST/停牌字段；没有打开行情价量列。

八只均有两行既有semantic identity元数据和一行当日States；本次范围内asset ID无重复。
但现有被C1采用的独立stk_limit探针receipt中，该八只当日的匹配数均为0。
这限定为**已有C1接线的来源库存**，不声称其它未调查供应商没有数据，也不要求全库补采。
不能将日终special诊断或provisional限价改标为普通盘前证据。

部分输入包传入E2后得到8个NO_NEW_ENTRY，分类为 `INPUT_ASSEMBLY_PENDING_NOT_EXCHANGE_REJECTION`。
该包只装身份事实，质量/ADV/事件尚未装入，所以这些reasons是**未接线**，不能解释为八只股票
真实没有质量、量或公司行动数据。原数据扫描已完成，不能再次列为待采事项。
本轮主动停在输入依赖检查，不运行空仓九年，再以零暴露宣告成功。

| 剩余责任 | 已知状态与后续范围 |
|---|---|
| strategy-specific A assembly | 将真实触达候选/持仓的日级状态、独立限价、prior20/warmup、identity及已知当期事件接成显式historical输入；先复用既有源，仅必要触达缺口定向补证 |
| order/cash/fee integration | 本次纯intent/confirmation和预算通过synthetic；尚缺与CoreSession同日实际卖款、部分成交、母单费用及整日提交的真实策略接线；early沪市已证面值缺失时仍拒绝费用计算 |
| E2 held/event path | 按逐日真实股数与登记权益触发检查；不是用目标成员名单筛全库R1–R3，也不能把未来事件作历史entry黑名单 |

因此 actual scheduled执行、membership churn、持有期、cash/空位持续、blocked exit、slot deadlock、
实际alias拒绝数均为 **未测得**。R1/R2/R3实际触发数 **null / unknown，不是0**；
实际路径未启动，后续日期NOT_REACHED，没有“已证无影响”的异常集合，也尚无已验证triggered case。
这不撤销E2 Core机制就绪，也不重启148/528/921全库清理。

## 验证、证据与停止点

[机器验收记录](ACCEPTANCE.json)绑定freeze、代码、封闭输入访问、目标输出与独立复核。
最终输出在 `outputs/economic_translation_mvp/e3_preflight_v2`。
v1第一次执行因把续采的`data.parquet`误认成初采`<instrument>.parquet`而失败；
失败输出完整保留，按receipt文件清单修复定位，v2与v1目标输出逐字节一致，未换参数/样本。
独立程序重新从原B分数排序、逐日重建目标状态与全部持有段，验证2,189日、445段通过。
独立复核不调用生产E3成员/投影函数；输入来源27个文件hash另核对。

新结构/预算与旧E2/E1相关定向套件174项通过；另运行fast/qlib质量检查，结果见机器记录。
full旧全库验证涉及本轮禁止的历史经济/recent证据，使用outcome-isolated定向套件替代，未放宽边界。

**结论：单一研究版本已冻结；actual path preflight PENDING，target结构需人工审议。**
参数未作任何结果后调整。没有正式Monthly/Buffer回测、NAV/PnL、收益比较、E1重跑、
Quotes/States/Dividends重采、B494/canonical改动或2024+项目值读取。
没有运行benchmark收益；中证全指仅冻结外部身份，内部EW仍为后续research reference用途。
提交推送，停止等待人工审核；不自动进入E4或第二候选。
