# E3 Portfolio Parameter Research Report

2026-09-16候选审核停止点：**E3 PORTFOLIO PARAMETER RESEARCH / STRATEGY V2 CANDIDATE PENDING**。
见[候选结论](CANDIDATE_DECISION.md)与[全部30候选统一对照](CANDIDATE_COMPARISON.json)。
30/30结构完成，0/30完整实际经济路径；既有执行来源、现金/费率与事件接线问题足以阻止
推荐候选成立，按用户最新允许的例外如实pending。没有新参数、新模型研究或结构重跑。
以下为原结构研究报告；其运行receipt、SUMMARY与所有V1证据不修改。

2026-09-15，基线 `main@7202dea`。**E3 PARAMETER RESEARCH / ACTUAL PATH BLOCKED**。
Phase A 搜索空间冻结、Phase B 目标结构对照与独立重放完成；Phase C–E 尚未完成。
**未选择/冻结 Strategy V2，未产生真实账户经济结果。** E1 COMPLETE、E2 CORE READY不变。

## 授权、实现与研究自由度

采纳本轮计划：2015–2023现为允许portfolio参数调优的development域；收益评价已获授权，
但仍须真实账户路径及验证。2024+保持封闭。旧“单候选/不许经济评价”是历史授权边界，
不再作为本轮拒绝研究的理由。现阶段阻塞是执行依赖，不是缺少用户调参授权。

[研究计划](../../../docs/ECONOMIC_E3_PARAMETER_RESEARCH.md)与[search.json](search.json)
预先规定30个稀疏候选，SHA256 `08e281cfa4986350aa8bddc4791c5e32ff83d793aae746ceb0104cd55201545a`。
四维为K、Hold、interval、cap；保持100k、near-EW、5%reserve、费用、open-reference和E2约束。
所有30个算术合法候选继续保留经济评价资格，没有因结果不漂亮删臂，也未追加参数。
原v1与其435/437证据不覆盖；本次控制臂的所有2,189日members/entries/exits/backlog与原版逐项一致。
Economic Candidate v1不同于原Forward Strategy V1，不改变后者的真实forward约束。

复用BoundedScores封闭B/keys reader、原排名tie-break、E2 historical phase与known-event
适配、adv20_with_warmup。新增研究层目标投影和独立标量oracle，不另造回测引擎。
实际读取4,377,824个既有B分数，30×2,189日目标结构；没有重跑E1、模型或三项数据采集。
研究已知V1结构与D3-A历史结果；以后经济选择只能称development tuning，不能称fresh OOS。

## 目标结构结果

以下均为**理想目标成员**，假设目标转换成功；没有E2可成交性、股数、现金、费用或公司行动。
“有变化决策”指有目标新增/退出，不能称实际订单率。
cap binding定义为决策前待退出数>cap；queue是本次允许退出后仍未退出者。
日均churn=(新增+退出)/(2K)，剔除初建，无价格权重，不能解释为真实金额换手。
持有期为已结束目标段中位数，单位交易日。队列age从首次被cap延迟起日0计，
只在决策日更新；表中max是尚排队观察的最大age，完整episode年龄另保存在SUMMARY。

| 候选 | 目标退出 | cap积压频率 | 有变化的后续决策 | 日均目标churn | 中位持有期 | max queue age |
|---|---:|---:|---:|---:|---:|---:|
| k8_h16_d1_c1 | 1921 | 66.39% | 87.84% | 10.98% | 7 | 21 |
| k8_h16_d1_c2 | 2930 | 26.02% | 81.80% | 16.75% | 4 | 7 |
| k8_h16_d1_c4 | 3472 | 2.42% | 79.97% | 19.84% | 3 | 2 |
| k8_h16_d1_cnone | 3526 | 0.00% | 79.74% | 20.15% | 3 | — |
| k8_h16_d3_c1 | 727 | 96.30% | 99.73% | 4.16% | 21 | 66 |
| k8_h16_d3_c2 | 1356 | 73.25% | 97.67% | 7.75% | 9 | 30 |
| k8_h16_d3_c4 | 2029 | 19.07% | 96.16% | 11.60% | 6 | 12 |
| k8_h16_d3_cnone | 2200 | 0.00% | 95.47% | 12.57% | 6 | — |
| k8_h16_d5_c1 | 437 | 99.54% | 100.00% | 2.50% | 30 | 125 |
| k8_h16_d5_c2 | 857 | 90.16% | 99.77% | 4.90% | 15 | 55 |
| k8_h16_d5_c4 | 1462 | 40.27% | 99.08% | 8.36% | 10 | 15 |
| k8_h16_d5_cnone | 1711 | 0.00% | 98.40% | 9.78% | 5 | — |
| k8_h16_d10_c1 | 218 | 100.00% | 100.00% | 1.25% | 60 | 430 |
| k8_h16_d10_c2 | 436 | 100.00% | 100.00% | 2.49% | 30 | 120 |
| k8_h16_d10_c4 | 833 | 72.48% | 100.00% | 4.76% | 20 | 40 |
| k8_h16_d10_cnone | 1130 | 0.00% | 100.00% | 6.46% | 10 | — |
| k8_h8_d1_c4 | 5855 | 11.39% | 98.03% | 33.46% | 2 | 2 |
| k8_h8_d1_cnone | 6180 | 0.00% | 98.03% | 35.32% | 1 | — |
| k8_h12_d1_c4 | 4255 | 4.30% | 87.38% | 24.32% | 2 | 2 |
| k8_h12_d1_cnone | 4370 | 0.00% | 87.29% | 24.98% | 2 | — |
| k8_h20_d1_c4 | 2978 | 1.83% | 73.85% | 17.02% | 4 | 2 |
| k8_h20_d1_cnone | 3021 | 0.00% | 73.71% | 17.27% | 3 | — |
| k5_h8_d1_c3 | 2782 | 2.97% | 75.49% | 25.44% | 2 | 1 |
| k5_h8_d1_cnone | 2847 | 0.00% | 75.35% | 26.04% | 2 | — |
| k5_h10_d1_c3 | 2387 | 2.15% | 68.13% | 21.83% | 3 | 1 |
| k5_h10_d1_cnone | 2440 | 0.00% | 68.31% | 22.31% | 3 | — |
| k10_h15_d1_c5 | 5118 | 3.29% | 91.36% | 23.40% | 2 | 2 |
| k10_h15_d1_cnone | 5203 | 0.00% | 91.31% | 23.79% | 2 | — |
| k10_h20_d1_c5 | 4157 | 1.78% | 84.18% | 19.01% | 3 | 2 |
| k10_h20_d1_cnone | 4198 | 0.00% | 84.00% | 19.20% | 3 | — |

全部候选、年度数据、queue depth/age分布、缺席与有限stale rank、延迟后恢复分段及
持有段汇总见[SUMMARY.json](SUMMARY.json)。完整逐日/逐事件原始诊断与输入访问日志保留于
`outputs/economic_translation_mvp/e3_parameter_research_v2`，hash在[ACCEPTANCE.json](ACCEPTANCE.json)。
目标欠配为0只说明理想转换可填满，不能用于推断现金利用率或真实slot deadlock。

## 对研究问题的当前回答

1. **Daily decision在成员算式上可行，真实可执行性未证。** K8/H16/无cap时79.74%的后续决策
   有成员变化。每日决策不等于每日全换仓，但当前buffer也没有吸收大多数日期的成员变化。
2. **buffer有明确结构作用。** 日频K8无cap时，Hold8→12→16→20的目标退出数依次
   6180→4370→3526→3021，有变化决策98.03%→87.29%→79.74%→73.71%。这不是收益改善证明。
3. **频率不能脱离cap讨论。** K8/H16无cap在1/3/5/10日下退出数3526/2200/1711/1130；
   成本、真实金额换手与经济表现尚unknown，不能以目标退出少直接选10日。
4. **drop1的约束强度依赖周期。** 日频积压66.39%，3日96.30%，5日99.54%，10日100%。
   5日控制臂排队观察max age125交易日；10日cap1可达430日。这支持研究cap，而非证明有收益损失。
5. **日频cap4与无cap是相近的结构区域。** 目标退出3472与3526，中位目标持有期均3日，
   cap4积压仅2.42%。不能把这种成员结构接近称为经济稳定平台或最终建议。
6. **cap既有延迟退出，也有恢复。** 日频cap1已结束deferred episodes中42.52%下次观察时恢复
   ≤Hold；5日cap1为31.86%。分母排除右删失，按episode计而非独立股票；不是盈利/机会成本统计。
7. **K与Hold的局部对照保留，但尚不能判定实际分散度/可负担性。** K5/H10日频无cap的
   目标日均slot churn22.31%，K8/H16为20.15%，K10/H20为19.20%；单个slot预算不同，
   不能比较未算的最低佣金负担、现金或真实成交数。
8. **transaction cost对参数排名影响：未测。** 未产生NAV、收益或净/毛比较，也未用目标退出
   数乘固定费用冒充实际成本。缺口关闭后所有候选须使用同一冻结费用与现金合同。
9. **年度/分段经济稳定性、尖锐单点最优：未测。** SUMMARY的年度表只是结构年表；预定义
   邻接边已列入search，不允许看到收益后新增点寻找平台。
10. **最终V2选择理由：尚无。** 不能从当前结构结果宣布development tuning complete。
11. **实际路径完整性：NOT_STARTED。** 既没有完整路径，也不是已运行后HALT的路径。
12. **实际R1/R2/R3：均null/unknown。** 无账户启动就不能报告“0次命中”或从目标池推断未持有。

## 首决策来源闭环取得的进展

按所有候选共同的首次signal2015-01-05→execution2015-01-06，固定原Top10（K5/8为其前缀）：
SZ300246、SZ300245、SZ002196、SZ300331、SH600070、SZ300354、SZ002401、SZ300220、SZ002382、SZ300076。
不为找到可执行样本替换起点，不扩入Top10之外，也不以未来问题筛股票。

- 10/10有两日一致identity、当日States（active=1、ST=0）、前一日cross-source quote quality
  和正的原始BaoStock open；正open仅支持既有daily-open-reference近似，不是竞价成交量证明。
- 复用sealed warmup volume overlay，严格取2014-12-05—2015-01-05共20先前交易日。
  8/10得到ADV；SZ300220、SZ002382为unknown，真实准入应NO_ENTRY，不能NaN→0或缩短窗口。
  本次只完成首日接入验证，不宣称整个2015早期逐日runner的warmup接线完成。
- 这10只在首日record/ex-date的已知distribution metadata审查均0条；这是flat-start窄范围
  观察，不是五类事件全集为空，也不能替代后续持仓registered rights/付款/上市检查。
- 现有C1采用的独立stk_limit receipt中，10/10对该日没有匹配。该结论仅覆盖已接线inventory，
  不声称所有供应商不存在数据。原始ST=0和active=1不能升级为ordinary制度证据。
- 相比上轮identity-only包，8只的A gate diagnostic已缩小到ordinary_execution_not_certified；
  2只另有adv_not_ready。不是运行了10个真实失败订单，更不是全空仓回测验收。
- SH600070的早期沪市面值尚未组装，不能默认1元；它位于K5首批之内，不能通过改变K绕开。

## 真正剩余依赖与继续执行顺序

| 依赖 | 当前证据与处理 |
|---|---|
| touched-entry ordinary state / independent limits | 首批现有receipt缺失；复用既有来源接入范围内日期的独立限价并与States/reference核对。不能把semantic provisional限价改标认证，不能扩大成重采Quotes/States/Dividends |
| conditional multi-sale / cash / fee接线 | 旧CoreSession仍为预给工程intents，批初buy budget和旧万三默认；需接冻结的多退出尝试、实际卖款、万2.5、母单最低5和10bps，保留原Core日事务与失败回滚。该部分尚未实现，不能声称只差跑命令 |
| daily actual exposure / events / R1–R3 | 第一笔真实交易前先做bounded非空账户canary及独立股数/现金验证；之后用户运行长路径，逐日处理实际命中的估值、identity和rights，无法解释则HALT_RETAIN并记录NOT_REACHED |

经济评价权限已经开放，但没有可信输入/账户路径时不应执行。两个ADV未知只是局部准入拒绝，
不重新升级为全局E2 blocker；精确历史时刻、完整特殊制度模拟和全148/528/921案例清理不再扩scope。
日级historical有效性、known-event review、open-reference、税前股息和既有费用近似继续明确沿用；
不增加“所有未知事件视为无事”的新近似来启动研究。

## 验证、失败保留与交付

- 30候选×2,189日的members/entries/exits/queue/stale字段、spells、deferred episodes由独立
  scalar oracle重新排序原分数后逐项匹配。另用独立聚合实现逐字段复算全部30份summary，
  包括年度表、分布与null边界，见[补充汇总验证](SUMMARY_VERIFICATION.json)；没有修改原receipt。
  这仍不构成经济验证。所有原始访问文件、冻结合同、结果和代码LF hash已复核。
- v1控制臂逐日对原封存target证据一致。所有候选年度不重置，无2024强平。
- 183项相关测试（含37项新增）、fast46项、Qlib6项通过，合计235；新Python文件Ruff通过。
  Qlib有4条既有synthetic Mean-of-empty-slice warning。未跑包含本轮未授权recent/Forward值
  检查的legacy full tier，以这些定向测试替代，未伪称全仓full通过。
- 首次`e3_parameter_research_v1`的target计算完成，输入审计因通用适配器拒绝2014而失败。
  修复为已有adv20_with_warmup专用首日bridge；旧Core日期边界没有改。新结果目录为
  `e3_parameter_research_v2`（运行attempt编号，不是Strategy V2）。失败文件保留，30份target
  及summary与首轮字节完全相同；没有修改候选、参数或对照样本。
- 未运行真实NAV/回报/风险指标、长程账户回测或数据采集，没有访问2024+项目值。
  本轮已有结果无需重跑；独占写入脚本对既有目录会拒绝覆盖。尚无可诚实交付的正式经济运行
  命令，不能把结构脚本包装成实际回测入口。

当前未达到`E3 STRATEGY V2 FROZEN / DEVELOPMENT TUNING COMPLETE`。
提交推送本轮搜索合同、结构证据与输入进展后停止审核；下一步是上述策略专属执行依赖，
不是继续增大搜索空间或重新设计E2。
