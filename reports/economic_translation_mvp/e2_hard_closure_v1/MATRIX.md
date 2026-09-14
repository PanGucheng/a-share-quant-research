# E2 Data Readiness Matrix

2026-09-14；基于 main@2776029 的已封存数据语义审计。**E2 STILL BLOCKED；E2 READY FOR E3 FREEZE = false。** 当前报告见 [REPORT](REPORT.md)，方法与消费边界见 [SEMANTIC_RECONCILIATION](SEMANTIC_RECONCILIATION.md)。旧矩阵由 Git 历史保留；三项采集均完成，不再列为待执行事项。

READY 只代表该行限定范围；单个数据层通过不等于真实账户可运行。下表只有 H1–H4 是当前 E2 hard blockers。近似不允许填补未知行情、登记权益或终止结算。

| 项目 | 分类 | 本轮验收与明确边界 | 当前处置 |
|---|---|---|---|
| 封存数据与连续索引 | READY | 4,416 个历史代码，7,429,962 个证券日，首次候选至 2023-12-29；全部输入 hash 和输出索引复核 | 已完成，不重采 |
| 通常量价单位与旧代码修正 | READY（限定有效配对） | 7,105,530 日两源六字段一致；旧 SH601313 654 个有效日保留隔离单位修正；本地 factor 不进入 raw 会计 | 不外推为所有未决日正确 |
| 旧代码行情延续 | READY（报价关系） | 新代码已采集源补足旧 ID 的 1,411 个有效日；research ID 不改，economic asset 相同 | 444 日候选身份并存仍拒绝双算；登记权益迁移归 H2 |
| H1 原始报价冲突与未解释报价 | BLOCKING / UNRESOLVED | 原 9 个有效双源冲突日中 4 个 amount-only 日已按明确 1 元预算降级近似，5 日实质冲突未决；1 个非尾部 unresolved 日；SZ001872 另有 1 日只本地整组报价有效但源字段冲突；其他单源 overlay 明确留出处 | 按证券/日期核对，不选源赢家或放宽容差掩盖差异 |
| 日终停牌/ST观察层 | READY（观察层） | 逐日 observed_status、ST、停牌、来源及临时估值已接入；241,912 个停牌观察日；unknown 从不默认 ordinary | 不是盘前状态许可；实际数值表可供诊断/估值适配 |
| H2 身份、尾部失联与终止权利 | BLOCKING / UNRESOLVED | 148 个代码、80,754 个尾部缺失证券日；同股数改代码关系已有证据，完整待结权益/登记迁移未齐 | 逐资产解释 terminal、换股、代码或源覆盖；保留库存与权益，不末价卖出/归零 |
| 事件版本与普通税前桥 | READY（限定已解析条款） | 28,681 个源版本完整保留；原 682 个不同内容重复组中 674 个已合并、8 个保留；36 条现金缺值获得兼容实施版本补证（候选内 34 条）；候选资产 23,488 个键满足普通税前条款合同 | 事件解析不等于公司行动全集或所有持仓数量可结算 |
| H3 事件条款、除权与会计连续性 | BLOCKING / UNRESOLVED | 候选历史 inventory 602 个未决键/533 个资产，其中潜在持仓登记范围 528 键/470 个 ID；含 600 个现金缺值或冲突键、6 个上市日缺失及 2 个公告登记顺序问题；225 次除权参考不符/171 个代码；89 个无匹配事件参考价重置日/84 个代码；191 个已解析事件对 100 股产生非整数红股权益（潜在登记范围 183 键/158 个 ID） | 以公告/登记结算补证，含差异化分红、零碎股与复杂事件；配股/一般换股/终止现金的可信总数仍 unknown，不能写零。各范围有重叠 |
| H4 特殊交易制度与盘前状态证据 | BLOCKING / UNRESOLVED | 70 个日/70 个代码超出普通制度族诊断上下限；历史 IPO/relisting/terminal 和状态可得日期未形成完整证据；全表盘前许可均 false | 普通 dated rules 已复用，但 provisional bounds 不能冒充真实限价；未知或特殊时拒绝成交，已持仓仍受 H2/H3 约束 |
| B494 t close → next open | ACCEPTABLE MVP APPROXIMATION（日期级 PIT） | 沿用 t 日来源齐全、隔夜批次在订单前完成的合同；不声称 t 15:00 全部到齐或历史 vintage 已认证 | E3 接入时验证完整来源清单与批次；本轮未重读真实分数/特征 |
| ADV20 warmup | ACCEPTABLE MVP APPROXIMATION（严格缺值门槛） | 已有 1,706/2,000 首日候选具完整 20 日量；294 个未知时禁止新开仓，直到自然形成完整滞后窗口 | 保留全部日期，不填零、不推迟研究起点、不强制卖出旧仓；不再独立阻塞 E2 |
| 日线 open / auction | ACCEPTABLE MVP APPROXIMATION（open-reference 研究定义） | 日线 open 只作参考成交价格；滞后 ADV、批初现金约束、全日零成交只作不成交否决；不声称竞价排队或实际冲击可复原 | open 缺失、未知状态与公司行动仍 fail closed；竞价证据不再另列硬阻塞 |
| 成交额精度 | ACCEPTABLE MVP APPROXIMATION | 4 日价/股数一致而成交额差异不超过 1 元；另存 patch，成交额取较低值 | 价格/股数差异不豁免，保留原审计与来源；盘前许可不变 |
| 停牌持仓暂估 | ACCEPTABLE MVP APPROXIMATION（有日期来源） | 当天供应商停牌 close 可作为带陈旧期的暂估；不能成交，也不覆盖未知事件/终止权利 | 终止/失联仍为 H2，禁止无限前填掩盖缺口 |
| 股息税与交易费用 | ACCEPTABLE MVP APPROXIMATION / EXISTING DATA BUT NOT WIRED | 明确 before-dividend-income-tax，不充税后；用户佣金万 2.5 双向、母单最低 5 元，法定费另列；现有 dated schedule 沿用 | E3 费用接入时固定舍入/面值/pass-through 等早期假设；未知面值的预算不是已证实上界。本轮未启用旧引擎默认费率，不与 H1–H4 同级 |
| benchmark 与个人资金组合身份 | ACCEPTABLE MVP APPROXIMATION（研究对象分开） | 学术全池 EW reference 与个人可执行账户不要求同一复制能力 | K/AUM/benchmark 选择与真实 lot/fee/liquidity 验收留给另行授权的 E3；本轮未选择或搜索 |

可正式采用的近似范围是上述明确的研究定义和保守入口限制；实际账户尚未运行，也没有冻结 E3。**H1–H4 未关闭，停止等待人工审核。**
