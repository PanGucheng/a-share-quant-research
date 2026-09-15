# E3 Portfolio Parameter Research

2026-09-15，基线 main@7202dea。用户要求参考《E3 Portfolio Parameter Research 与
Strategy V2 冻结》实施，采纳其 development tuning 授权。本文在本轮分数/结构结果读取前制定。
2015-01-05—2023-12-29 可以用于有限 portfolio 参数研究及真实路径经济评价；不再称该区间
fresh OOS。2024+、模型重训、B494/canonical 修改、回溯排除困难证券仍禁止。
Economic Translation Candidate v1 与原 Forward Strategy V1 是不同对象，均保留原证据。

## 采纳与限制

V1 的 435/437 积压足以支持重新研究 cap，但不能单凭它证明损失收益或决定新 cap。
每日决策值得纳入，且不强制每日恢复 TopK 或等权。使用一组稀疏、预指定的对照，
不执行全笛卡尔积，不依据结果追加候选。E2 Core Ready 不等于任何真实策略路径完整。
若真实来源/账户接线未就绪，Phase C–E 必须明确 pending，不能以 target proxy 冻结赢家。

## A：预先固定 30 个候选

所有账户100k、5%reserve、near-EW、仅新增时分配95%/K、原TopK内准入，不重排gate后的池。
沿用V1的费用、10bps单侧隐含成本、日级open-reference、严格ADV20、已持仓权益规则和benchmark身份。
唯一开放的参数为 interval、K、Hold、cap。比例cap为ceil(K/2)，无cap表示一次最多处理K个slot。

| 组 | K / Hold | interval | cap | 数量 |
|---|---|---|---|---:|
| 周期×cap主对照 | 8 / 16 | 1、3、5、10 | 1、2、ceil(K/2)、无cap | 16 |
| buffer对照 | 8 / 8、12、20 | 1 | ceil(K/2)、无cap | 6 |
| K局部对照 | 5 / 8、10；10 / 15、20 | 1 | ceil(K/2)、无cap | 8 |

Hold≈1.5K采用向上取整。V1的5日/K8/H16/cap1为保留控制。
此设计不能辨识所有高阶交互，也不能声称覆盖整个参数空间。机器列表在
`reports/economic_translation_mvp/e3_parameter_research_v1/search.json` 中逐项列明并hash。
后续独立oracle及代码hash另绑receipt，研究合同与最终Strategy V2 freeze严格分开。

多退出沿用V1的保守语义：最差rank/缺席优先，最多cap次退出尝试，失败不改选；
任一选定卖单未全额成交，则当日全部新买阻止。已完成卖出仍留现金；pending rights仍占slot。
唯一首决策允许最多K个新增，其后最多cap个新增；无cap仍受K空位限制。卖出收入只按实收使用。
目标投影假设所有转换完成，不能检验上述真实成交/现金限制。

## B：结构预筛

先完整读取一次既有封闭B494 reader并排序，30候选共享相同日历/排名，不运行E1原study。
报告逐日目标集合、逐次决策、已结束/右删失持有段、退出数、slot churn、buffer保留、
cap binding（待退出数>cap）、退出后queue depth、queue age、stale rank与年度指标。
queue只在决策时更新；age是从首次被cap延迟到当前的交易日数，起日0，不是天数。
记录每段cap-deferred episode最终sold/recovered/right_censored；恢复仅指下次决策观察时
rank重新≤Hold，不推断两次决策之间的恢复或收益。缺席rank=null并单列，不能以0表示。
buffer留存分母为决策前目标持仓人次；目标churn=(entries+exits)/(2K)，不是真实金额换手。

硬筛仅拒绝算术/日历/身份错误：超K、重复slot、未来/缺日、无效排名、非法进入band、
cap违约。错误保留且停止，不通过改参数绕过。cap积压频率≥80%仅预先标注
`PERSISTENT_CAP_BACKLOG`，不把主观结构偏好包装成收益结论或自动删除候选。
所有30个合法候选都保留经济评价资格，以便保留反例；成本和实际欠配不能从target阶段筛掉。
独立标量oracle重排原分数并核对每个候选每日members/exits/entries/queue/spells及汇总。

## C–E：实际路径、经济比较与最终冻结

必须使用同一E2 Core、同源版本、同一费用合同和逐日事件事务，先补strategy-specific接线，
再由用户执行长程路径。真实路径中断记录HALT及NOT_REACHED，不补零收益，不缩短共同年份
比较，也不把较少R1–R3命中作为挑选依据。全NO_ENTRY不算通过。R1–R3只处理实际暴露。
来源缺口发生在账户启动前则写NOT_STARTED，不能伪造actual HALT或实际命中数。

评价输出保留全部候选：年化收益/波动、Sharpe、Sortino、回撤/Calmar、逐年和
2015–17/2018–20/2021–23分段；买卖、真实金额换手、显性费用/最低佣金/隐含成本、
现金闲置、持仓数、欠配时长、失败订单、queue与实际权利问题。指标零分母返回null。
完成前不创建Strategy V2 freeze，不将不完整路径参与经济排名。

预定义邻接：候选仅一个参数维度不同且该维度无已列中间值者构成边；cap按1/2/ceil(K/2)/无cap。
经济结果全展示，不自动按最高Sharpe/CAGR选。邻域收益/风险/成本取舍、各年和三个分段的一致性
由最终报告逐项解释；没有稳定区域则不硬选。简洁/较低成本为同等证据下偏好，不能称显著性。
研究自由度为30候选、4维稀疏设计、已观察V1结构及D3-A历史结果、development人工选择；
不宣称独立验证集。若有必要修改运行语义，先版本化并对所有受影响候选等同重放。

## 停止点

本轮尽可能完成A/B、核实首决策原Top10的来源依赖并推进可独立验证的代码。
没有真实路径证据时，交付状态必须是`E3 PARAMETER RESEARCH / ACTUAL PATH BLOCKED`，
不能声称`E3 STRATEGY V2 FROZEN / DEVELOPMENT TUNING COMPLETE`。
完整V2 freeze后或遇到确证执行来源blocker时更新现有Matrix/pipeline/report、commit、push，
停止审核；不自动访问2024+、不重采三项已封存全扫描。
