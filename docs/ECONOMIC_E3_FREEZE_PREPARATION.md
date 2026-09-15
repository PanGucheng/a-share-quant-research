# E3 单一策略冻结与结构预验收

2026-09-15，基线 `main@33c43bd`。用户授权按《E3 Strategy Freeze Preparation 与
Outcome-Blind 结构预验收》推进。当前阶段允许单一策略定义、B494 排名/成员结构预检、
限定执行输入核验；不允许经济评价、参数搜索、2024+ 项目值或重启通用 E2 治理。

## 采纳与更正

采用 100,000 元、K8、Hold16、每五个交易日、最多一次正常替换、near-EW。
这些是人工预指定的研究定义，不是从多个候选中选出的赢家。
E1 的 Top10/Hold20 实际是 **10%/20%（约 200/400 只）**。其 63.3% 换手代理下降不能
移植到 8/16 只；lag5 排名相关也不能证明五日是最优频率或 alpha 半衰期。
不再保留 Monthly 第二策略臂，不叠加二十日 minimum holding，不以原配置默认值决定规则。
整个研究已有 D3-A 历史揭封背景；本轮 outcome-blind 仅指本轮不读标签及经济结果。

## 冻结定义

机器权威为 [freeze.json](../reports/economic_translation_mvp/e3_freeze_v1/freeze.json)。
每个顶层规则组均记录来源、研究/工程/用户假设分类和 approximation；它在真实分数读取前写入，
SHA256 与本轮代码、输入、运行状态另由不可覆盖 receipt 绑定。修改需要新版本，旧版不改写。

| 字段 | 唯一定义及理由 |
|---|---|
| signal/universe | 冻结 B494 annual scores 与同日 sealed keys；只对完整研究池按 score 降序、原 instrument 升序排名。E2 eligibility 在排名后执行，不能先删股再 Top8。SH/SZ 普通 A 股，STAR/ChiNext 权限视为开通；已持有离池证券/权利每日保留 |
| schedule | 全局封存 2,189 日历从第 0 个 signal session 开始，每五日决策；下一日 open-reference 执行。首日无之前分数所以空仓；末日无范围内下一交易日则不下单；年界不重置相位 |
| entry/hold | 未持有仅 rank≤8；持有 rank≤16 保留，rank>16 或缺席 signal pool 进入普通退出队列。E2 暂停/ST/special 不等于自动清仓 |
| replacement | 按最差排名优先（缺席最差、同类 instrument 升序），每决策最多选一个正常退出、最多一个新身份进入。卖出失败也消耗本次尝试，不试第二个；不累积次数。允许卖出后买入失败留现金 |
| initialization | 唯一第一次 scheduled decision 可尝试 Top8 全部初建；从第二次起即使首日未成交，最多补一个空位。无隐藏重复 cold-start；这可能导致缓慢建仓，需描述 |
| entry band | 只在原 Top8 内依排名尝试通过 A gate 的候选；A gate 拒绝可继续 band 内下一个。B 阶段买入失败后当日不重新选择，不扩到 rank9+ |
| slots | 股票、未上市红股、未结登记权益或现金应收按 economic identity 占一个 slot；pending rights 不因卖光普通股释放。别名冲突拒绝新买，已持有冲突 HALT_RETAIN；最多八个身份 |
| sell/buy | 先卖后买；仅实际全额卖出且无剩余权利才释放 slot。被阻止或部分卖出的仓位仍占 slot，该次决策不新增替代仓位。卖出阻塞也阻止本次其它空位新买，取保守单一路径 |
| cash/weight | near-EW：每个新增身份以决策前 A 阶段经认证账面资产的 95%/8 为含费预算上限，扣除应收/未上市权利后确定可配置基数；当前实际现金须另保留该基数的5%。只以实收可用现金下单，不预支计划卖款。数量以 t close 参考与整手向下取整，B 仅检查/缩量，不因 open 重新选股或增加数量 |
| drift/failure | 老仓不等权重置，不补部分成交余量、不借款、不把剩余预算再分给其它名额。open缺失/涨停/资金不足等依 E2 拒绝或合法缩量，余款留现金；当日母单过期，下次决策重新生成 |
| daily system | 非决策日仍调用 E2 daily state、公司行动、权利、估值和事务检查；C 层不能反向影响 A/B。未知已暴露权益或身份/估值问题立即 HALT_RETAIN，后续 NOT_REACHED，不能改策略绕行 |
| persistence | 相位、真实股数、economic ID、登记权利、未结事件、现金、当日 intent/confirmation、最后 COMMITTED session 一起持久化；仅完整日提交；恢复不能重放成交或最低佣金。年度模型切换不清仓、不撤权利、不重置持有期 |
| fees | 双向0.00025佣金、每证券/日/方向母单最低5元，包含交易所经手/监管成本，印花与过户另列；分币 HALF_UP、部分成交累计母单收费。沿用 dated stamp/transfer 来源；2015-08前沪市面值缺证禁止真实费用执行，不把1元面值假设说成上界 |
| early fee approximation | 明确选择 early transfer 最低0元、单列 pass-through（沪市按已证面值×股数×0.0003；深市金额×0.0000255），是经纪商细节未知下的记账近似，不宣称普适费单。缺面值仍 PENDING，不能默认为1元 |
| liquidity/impact | 严格前20交易日 ADV，未知量拒绝新买；母单容量≤1% ADV20。独立现金支出 implicit proxy 单侧10bps（既有候选），不改变 open 参考价、不模拟冲击优化；不是测得的市场冲击 |
| events/end | 沿用税前股息近似及 E2 整数事件桥；rights/conversion/terminal 未支持则停机；2023-12-29保持开放权利与右删失，不强平、不用2024价格结算 |
| benchmarks | 外部身份中证全指价格指数000985；非可投资复制，不含股息，不作净总收益的同口径 alpha 判定。内部仅保留 PIT executable-universe EW research reference 的用途，构造/收益另行授权；不新增其它主 benchmark |

中证全指名称和代码核对自[中证指数2023编制方案](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208175438-000985_Index_Methodology_cn.pdf)。
只用身份/方法元数据，不下载行情、成分、权重或指数收益；历史方法变动不以当前成分回填。
内部 reference 尚未形成可执行比较臂，不能在 E4 临时挑选最有利比较口径。

## 本轮验收与责任边界

先冻结，再实现小型纯成员计划函数：输入全池排序、真实 slot 与显式 E2 gate；输出退出尝试与
Top8候选列表。确认函数只按外部已核验的成交/权利结果改变 membership，不能把 intent 当成交。
复用既有 E2 Decisions、fee/lot 原语；不新建回测引擎、不改冻结 Core canary 源码。

允许短时九年单候选 **target-only projection**：只读 B494 分数/keys，假设目标转换立即完成，
报告 schedule、目标退出、目标 churn、buffer 保留、cap backlog、目标持有段及年界。
它是规划层诊断；不带 E2 来源认证，也不产生实际股数/现金或可用来声明 R1–R3 无暴露。
再对预先固定的 **第一个 signal session / next session 的原 Top8** 做只读执行输入核验。
不能换到 Core 已成功的 SH600000/2020 样本以代替真实策略起点。

actual path 只有在 E2 历史来源适配覆盖该路径、个人费用/母单现金接线及逐日事件 ledger 接好后，
经 Qlib CoreSession 和独立验证才可能 PASSED。现有 CoreSession 固定工程订单不能直接作为
按实际卖款条件买入的策略 runner。此次不为全量 generic 输入库重开采集。
若首批实际路径依赖未就绪，输出具体 PENDING、actual metrics=null、R1/R2/R3=null；
不跑一个全 NO_ENTRY 账户再声称已证明无风险。

测试必须覆盖：排序 tie、越界和额外 outcome 列拒绝；缺席、buffer、replacement cap；
冷启动/失败补位；卖出阻塞、部分成交、pending rights、alias 重复；年界/恢复相位；
现金/整手/个人佣金和早期面值缺失。独立 target oracle 不调用生产成员函数。
任何 target pathology 只作描述，不设事后阈值改参数；独立验证失败保留原输出。

最终更新 [E2 Matrix](../reports/economic_translation_mvp/e2_hard_closure_v1/MATRIX.md)、
pipeline 与本轮报告；提交推送，停止人工审核。E4/正式策略经济评价继续关闭。
