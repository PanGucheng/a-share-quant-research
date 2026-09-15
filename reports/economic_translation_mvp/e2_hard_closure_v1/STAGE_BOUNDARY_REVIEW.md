# E2 Core 与冻结策略路径：阶段边界评审

2026-09-15；审查基线 `main@6656a42`，已核对与 origin/main 一致。参考用户提供的
《E2 Core Readiness 与 Strategy-Specific Path Verification 调整计划》，附件 SHA256：
`d72bc39736906247b06aa4cc7ea32ff24dca7fca9cefd7413df441b1d1db2e85`。
本文与 [Matrix](MATRIX.md) 是当前阶段定义；原采集、语义和 scope receipts 保持不变。

**结论：采用 Core / Strategy Path 双层验收，停止以全库异常清零为前提的 E2 治理工作流。
当前为 E2 CORE PARTIAL / GENERIC INTEGRATION GAPS；STRATEGY PATH NOT STARTED。**
尚不能写 E2 CORE READY，理由只有下述 C1、C2 两项通用接线缺口，
不再引用 148/528/921 个条件案例阻止 Core 验收。整体仍为 **E2 STILL BLOCKED**。

## 1. 接受与更正

接受先冻结规则、再发现实际 exposure、再处理触发事件的顺序。通用基础设施不必预先证明
任何可能策略都能无异常连续跑完九年；它必须能正确处理受支持路径，并在不支持的敞口处
保留账本、停止、准确报告。安全停止可以满足 Core 的故障处理要求，不能冒充路径完成。

附件将“具有安全原语”近似成“基础设施已经安全接通”，目前证据不足。
`scope_account` 是纯函数，`require_scope_order` 是 opt-in guard；现有交易入口没有调用它们。
普通成交、股息、估值分别有 synthetic 证据，尚无把新 scope 与旧 Qlib 执行链合起来的验收。
这是通用实现问题，与未来会不会买到某个困难股票无关。

另须区分 target membership、订单意图与实际 exposure。限价、停牌、lot、部分成交、可用现金、
T+1、股息和未结权利都会改变后续持仓。不能先把目标名单当作实际持仓，做一次名单交集就宣布
Account Path Verified。真实账户路径必须按被冻结的规则和实际模拟成交逐日推进。

## 2. Core 能力证据与最小缺口

| 能力 | 现有证据 | Core 结论 |
|---|---|---|
| PIT 版本过滤、未知拒买、别名防双持 | [scope 原语](../../../qlib_integration/economic_mvp_scope.py)及定向测试 | 原语 VERIFIED；无未来黑名单 |
| 股数/现金应收/待上市红股完整 exposure；未知 HALT_RETAIN | 同上；原股卖出后权利仍保留 | 原语 VERIFIED；不是整段账户验证 |
| 普通 raw open、无 close fallback、T+1、lot、容量、母单费 | [EconomicOpenExchange](../../../qlib_integration/economic_exchange.py)及 Qlib synthetic tests | 普通执行组件 VERIFIED；个人费用配置尚待 E3 明确接入 |
| 普通现金分红、整数红股、登记/除权/支付/上市、同股数迁移 | [EventPosition](../../../qlib_integration/economic_event_position.py)及独立会计断言 | 支持范围内 VERIFIED；不是一般换股/退市处理器 |
| 非空、来源绑定的历史执行输入 | sealed daily 的 known_at 为空、ordinary_regime_certified=false；尚无合格到 Fact/prepared 的真实适配交付 | **C1：通用 input adapter 与有界来源验收缺失** |
| Entry/Holding 与日级执行生命周期一致接通 | 旧 require_continuity 仍检查全部候选；旧 prepared 要求普通上下限；scope 不能启动/提交账户日 | **C2：统一 session 接线与组合验收缺失** |

### C1 的有限验收范围

复用现有 quote/state/event/identity overlay，给每个字段绑定证券、来源、有效区间、可用阶段、
版本和证据等级。`events_clear` 必须说明当前已知事件及覆盖范围，不能由空表或“未来没出问题”生成。
盘前 A、开盘确认 B、收盘估值 C 分阶段提供；来源缺失、相互冲突、越界在入口 fail closed。
不得把整行日终状态的 known_at 统一伪造为昨日，或凭昨日普通状态认定今日没有新停牌/ST/特殊事项。

允许沿用明确的 date-PIT 和 open-reference MVP 假设，但它们必须成为适配输出的显式依据，
不能把假设标记成真实历史 timestamp。普通规则、上市制度、状态生效日期仍需来源支持；
日内 high/low 检查只能用于事后成交/估值核验，不能筛掉早盘候选。

Core 不要求全池每天可买，也不要求重建所有原始 vintage。关闭 C1 只需一个预先指定、
与分数/收益无关的有界来源 canary，包含非空普通路径和缺失/冲突拒绝路径，
证明适配机制可以消费现有证据。样本、窗口、字段和通过条件须在读取研究值前固定；
失败样本保留，不能不断换样本直到出现通过结果。该 canary 不证明策略路径或全池覆盖。
本轮未运行该真实 canary、未补造 facts，C1 保持 OPEN。

### C2 的有限验收范围

复用 Qlib Account / EventPosition / EconomicOpenExchange，增加一个 opt-in 日级接入点，
使被拒绝的未持有候选不再传到旧的全候选 continuity 检查；持仓、应收和待上市权利仍必须全检。
普通订单走既有 guards；CARRY_ONLY/CARRY_CASH_CLAIM 走独立无交易分支，
不得给特殊持仓编造普通限价来通过 prepared schema。

明确并验证：前一日登记快照 → 当日已知事件与盘前参考估值 → Entry/持仓交易权限 →
开盘成交确认 → 当日收盘估值与登记快照。盘前不能要求或消费当日未来 close；
遇到登记/权益/估值失败时，恢复到最后一个完整阶段检查点，禁止留下半笔事件或半日可继续账本。
恢复须覆盖现金、股数、应收、红股、事件已应用标记、T+1、母单费用与容量状态。

最低验收是跨多日的 synthetic 普通买卖及 dividend/bonus 路径、坏的未持有候选共存、
特殊持仓 carry、cash-only claim、各阶段注入失败后的账本不变、同一输入恢复重放一致。
这属于 Core 集成，不需要 B494 分数、K 或正式策略。全特殊制度模拟仍不需要。
本轮审查未实现该接入点，C2 保持 OPEN；不将逐组件测试冒充组合验收。

## 3. R1–R3 的新分类

| 方向 | conditional handler available | strategy-specific unresolved case | 通用依赖 |
|---|---|---|---|
| R1 估值 | 有来源及时点的正有限 mark 检查；未知保留并停；禁止交易不等于禁止估值 | 实际持有时的 3 个 close 冲突，以及其他缺乏合格市场权利估值的触发 | C1 mark 来源、C2 分阶段 carry 接线 |
| R2 身份/终止结算 | 唯一经济身份检查、限定无未结事件的同股数迁移、terminal HALT_RETAIN | 实际触及的 148 起覆盖事件或带权利迁移、一般 conversion/terminal settlement | C1 身份绑定、C2 检查全部 exposure |
| R3 权益 | 普通分红/整数红股桥、现金应收保留、Decimal fractional claim 描述与停机 | 实际登记敞口命中的 528 个未决键、实际非整数分配、配股/换股/终止权利 | C1 事件覆盖语义、C2 登记及事件事务顺序 |

“handler available”须分清 **可完成普通处理** 与 **只能检测并安全停止**。
Decimal helper 尚未把零碎权益接入真实交割/估值；一般 rights/conversion/delisting cash
没有自动处理器。Core 可以因可靠检测并停机而通过，无须预先补齐这些处理器。

148/528/183/921 继续只是原 inventory/diagnostic 数量，不是实际触发数量。
目前没有 frozen path，`irrelevant to actual path` 的已认证条目数量 **unknown**。
以后只有经过完整路径核验、确认从未存在股数/登记权益/应收/待结权利的条目，才能对该策略
标记 irrelevant；原记录和 provenance 保留。路径中途 halt 后，后续未走到的日期只能是
NOT_REACHED，不得标为无影响。inventory 未列出的异常也必须由通用检测器捕获。

## 4. 新阶段及本轮停止点

| 阶段 | 通过条件 | 当前状态 / 授权 |
|---|---|---|
| E2 Core | C1/C2 通过；受支持路径正确、未知敞口检测并安全停止 | **PARTIAL；C1/C2 OPEN** |
| E3 Strategy Freeze Preparation | Core 经审查成立；填写并审议下面的冻结字段，不用收益或路径易跑程度选择 | 本轮仅交付准备合同；条件未满足，未选择/冻结参数 |
| Frozen strategy definition | 一个明确策略版本、完整参数、来源/code hash、freeze 时间 | NOT FROZEN |
| Account-Path Preflight | 从 frozen 规则顺序生成意图和实际账户事件；独立核验 exposure | NOT STARTED；须前述条件成立后才运行 |
| Triggered R1/R2/R3 resolution | 对命中案例补证/处理、保留失败版本并重放同一规则 | PENDING PATH |
| Economic Evaluation | 完整路径通过、独立验证/2023 边界对齐、口径冻结，另获结果开放授权 | **NOT AUTHORIZED；禁止自动 E4** |

`E2 CORE READY / STRATEGY PATH VERIFICATION PENDING` 是合法的未来状态，
不会被尚未触发的 R1–R3 阻止；它也不意味着 `PATH VERIFIED` 或完整经济回测已可信。
本轮不满足其 Core 条件，故不激活附件中以 Core Ready 为前提的策略参数选择或路径构造。

**可以停止全库 E2 数据治理工作流**：采集与全库异常清零均不再列下一步；仅 C1/C2 为
有限通用工程任务。后续个案补证由 frozen exposure 触发，不重新排全库人工修复队列。

## 5. Strategy-specific account-path verification contract

### 先冻结什么

直接扩展已有 MVP 执行合同，不新建另一套策略框架。冻结记录须绑定：
2015–2023 日历及终止边界、既有 B494 prediction hashes/canonical identity、code/version；
可执行新开仓 universe 与 PIT 证据规则；holding/离池/被动权利规则；调仓时刻与日历；
排名/并列顺序、组合构建、K/buffer、AUM、权重/现金保留；拒单后是否补位、订单优先级、
部分成交与未成交单有效期；benchmark 身份与是否仅学术参考；费用/税基/执行和估值近似。
策略定义需要依赖成交现金时，以被冻结的函数和状态机为权威，不要求提前写死全部未来订单。

现有事实可预填：仅 B494；用户研究假设 5万/10万元、佣金双向万2.5且母单最低5元、
印花税和过户费另计、创业板/科创板权限已开通。资金两档是既有研究范围，
并不自动生成两个正式策略。10/20、5万元 K=5、10万元 K=8 仍为未冻结候选。
早期费基/舍入、费用真实接线、benchmark/现金保留等未决字段不得默认填旧引擎值。

freeze 必须发生在首次真实 path 构造前，保存不可覆盖的参数/code/input 绑定和时间。
若一开始授权多个路径，先列明全部并逐一保留失败，不以“哪个更容易跑通”挑 winner。

### 如何构造和独立验证

1. **生成器**读取冻结 B494 分数、PIT 截面和当时已有账本，按冻结函数生成 target/intent。
   它是 prediction-aware，不能声称 score-blind；不读取 labels、收益报告或未来诊断黑名单。
2. **账户推进器**只接收本次 intent 和分阶段证据，用 Qlib 原股数/现金/事件机制顺序模拟。
   实际成交产生下一时点 holdings；未成交不是 exposure，目标退出也不代表实际清仓。
   不预支卖款/应收；当日交易、收盘登记与后续股息均保留。
3. **独立 preflight**不接收 score 数值、排名指标或未来目标；读取冻结规则 hash、日期、
   asset/instrument/event ID、订单及成交凭据、股数/现金/权利账本、source receipt。
   核对时点、唯一身份、现金/股数/权益守恒、未成交后持仓保留和逐阶段事件幂等性。
   检查器可以用当日/历史价格验证会计，不能把“score-blind”理解为禁止必要估值输入。
4. 按实际 exposure 与事件有效窗口关联 R1/R2/R3。登记日末持仓决定普通分配权，
   除权后原股卖出不消除应收/待上市红股；迁移连接经济资产，不只匹配旧 ticker。
   不只对现有 CSV 做 inner join：未识别事件、报价断档和 identity 缺失同样产生 blocker。
5. 报告只开放输入/规则绑定、日期覆盖、订单/持仓/权利覆盖计数、触发案例及 halt 原因。
   内部现金和估值计算是路径必需，称 **economic-outcome reporting closed**；
   不声称没有做任何账户算术。禁用 Qlib portfolio metrics、benchmark return reader 和自动图表，
   不输出真实 NAV、PnL、CAGR、Sharpe 或其排序。不能先生成完整收益报告再说“不查看”。

target membership 可以作为诊断证据，但不替代 fill-conditioned exposure ledger。
独立核验器的接口虽 score-blind，生成器仍须分数；两者不能共用一个可读取全部未来表的上下文。

### 触发、停机、恢复与防反向优化

任何 exposed unknown mark/identity/right 先写 halt receipt（freeze/input/code hash、阶段、
asset/event、尚未解决证据、最后完整 checkpoint），停止受影响账户推进和结果生成。
保留全部原股数/应收/红股/现金；其他未持有证券坏数据仅 NO_NEW_ENTRY。
同一账户 halt 后不得让其他证券继续跨日以产生一个不完整但看似完整的净值。

补证只修复经济事实/处理器，不改变 K、universe、buffer、AUM、排名或其他策略选择来躲避问题。
补证的历史可得时点与此次获取时点分开记录；不能用后来知道的坏消息回写此前 entry。
修复后以相同策略 hash 从可信检查点或起点重放，旧失败输出、原始 sources 与两版 receipt 均保留。
实现修复需新 code hash、变更理由、独立验证和重放影响范围；不得默默修改冻结规则。
无法可靠处理时该路径保持 HALTED，不换策略掩盖失败。

2023 边界前所有阶段需完成，未结权利仍列存量；只有条款和估值依据明确才可作为终点资产。
不强制虚构卖出、归零或访问 2024+ 付款/行情。末日产生的下一年订单不得执行；
边界截断必须按预先冻结日历处理。

### 何时允许 economic evaluation

Core 验收通过；策略先冻结；全部授权路径及失败均登记；待评价路径完整跑至批准边界，
命中事件全部解决或按事前明确且有依据的会计近似处理；独立账本/PIT/终点验证通过；
费用、benchmark 和收益口径已冻结；**用户另行授权 E4/结果开放**。
Core Ready 或无新成交本身都不够。未触发的历史事件无需为该策略修完。

## 6. 本轮验证

重跑既有 E2 范围测试，核验原语及普通 Qlib 组件；另用纯 synthetic probe 对照
scope 与旧 continuity 路径。验证详情、code hashes 与边界在
[STAGE_BOUNDARY_VERIFICATION](STAGE_BOUNDARY_VERIFICATION.json)。
本轮交付阶段定义、Core 缺口定位、path 合同和状态更新，没有实现 C1/C2 或运行真实路径。
未重采三项库存、未重跑 E1、未读取 B494 值/真实收益/2024+，未更改执行或冻结实现。
提交推送后停止等待人工审核。
