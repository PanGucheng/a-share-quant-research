# E2 Data Readiness Matrix

2026-09-15；基于 `main@c312469` 完成历史可得性合同修订与同一固定 canary 验收。
**E2 CORE READY / STRATEGY PATH VERIFICATION PENDING。C1 与 C2 均 CLOSED。**
通用 E2 infrastructure 已收尾。2026-09-15用户最新授权有限参数与development经济研究：
**E3 PARAMETER RESEARCH / ACTUAL PATH BLOCKED**，见[当前报告](../e3_parameter_research_v1/REPORT.md)。
30候选搜索合同及目标结构核验完成；原100k/K8/Hold16/5日/max-drop1保留为Candidate v1。
尚未选择Strategy V2，actual path未启动，R1–R3仍unknown；2024+继续封闭。
见[实施验收](CORE_IMPLEMENTATION_ACCEPTANCE.md)和[本轮机器证据](HISTORICAL_CORE_ACCEPTANCE.json)。
原严格 PIT [失败验收](CORE_ACCEPTANCE.json)、采集与语义 receipts 保留，不改写历史结果。

| 范围 | 当前分类 | 验收结论 / 下一责任阶段 |
|---|---|---|
| Model/B494/canonical/E1 | FROZEN / UNCHANGED | 不重跑、不修改、不回溯删股 |
| Quotes / States / Dividends 长扫描 | COMPLETE / SEALED | 不重采；采集事项不再列 blocker |
| Entry、fail-closed、唯一身份 | CORE VERIFIED | strict 默认；historical 显式；live receipt/freshness 校验独立，历史近似不可用于 live |
| 股数、现金应收、未上市红股保留 | CORE PRIMITIVE VERIFIED | 非空 exposure 必须全检；unknown 保留并停 |
| 普通 open、T+1、lot、容量、母单费与整数事件桥 | CORE INTEGRATION VERIFIED | 原 C2 与历史模式回归通过；不等于真实策略路径验证 |
| **C1：历史输入适配与来源验收** | **CLOSED / HISTORICAL APPROXIMATION ACCEPTED** | 显式 session-effective、known_at 保持 null；同一 SH600000 / 2020-08-24 ALLOW_ENTRY→一笔普通成交→COMMITTED；不声称精确盘前 PIT 或完整事件覆盖 |
| **C2：scope 与 Qlib session/事件/估值接线** | **CLOSED / SYNTHETIC INTEGRATION ACCEPTED** | 新 opt-in CoreSession 已接通 A→事件→B成交→C估值/登记；carry 无普通报价；整日副本提交、失败保留原账本与恢复重放均通过 |
| 完整特殊交易制度模拟器 | NOT REQUIRED | 特殊/未认证时禁止新买及主动交易；支持有证据 carry，未决权益仍停机 |
| R1：已持有市场权利的估值 | STRATEGY-SPECIFIC CONDITIONAL | 3 个 close 冲突及其他实际估值缺口仅 exposure 命中后补证；mark 检查/HALT 原语已有，不再阻止 Core 验收 |
| R2：已暴露身份、迁移、终止结算 | STRATEGY-SPECIFIC CONDITIONAL | 148 起覆盖事件非已确认退市；限定同股数迁移原语已有，一般终止/带权利迁移需触发后处理或停 |
| R3：已登记或未结权益 | STRATEGY-SPECIFIC CONDITIONAL | 528 个未决键、183 个潜在零碎股键、参考诊断保留；普通桥和精确 claim 描述已有，实际分配/未知条款触发后处理或停 |
| 现金应收独立 carry | CONDITIONAL HANDLER AVAILABLE | 固定金额已知且有来源时无须旧股票行情；未支付不能下单，付款仍需事件证据 |
| 无实际 exposure 的历史异常 | IRRELEVANT ONLY AFTER PATH PROOF | 目前已认证 irrelevant 数量 unknown；中途 halt 后未到达日期标 NOT_REACHED |
| Historical session-effective、known-event review、daily open-reference、严格 ADV20、税前股息 | ACCEPTED MVP APPROXIMATIONS | 日级有效状态不证明具体发布时间；已知事件审查不证明全集完整；缺失/冲突/未知权益仍拒绝或停止 |
| 个人佣金、early fee、cash reserve、benchmark | DEFINITIONS PRESERVED / EXECUTION WIRING PENDING | 万2.5、最低5元、5%reserve、dated税费/early最低0与10bps代理沿用；首批SH600070面值未组装，旧万三/批初buy budget不能冒充新合同 |
| K/buffer/interval/cap有限搜索 | SEARCH FROZEN / TARGET SCREEN VERIFIED | 30候选共享B494与日历、独立重放全量目标路径；V1控制与旧逐日证据一致，没有真实收益/成本排名或V2选择 |
| 首日策略专属市场/ADV输入 | BOUNDED INTAKE VERIFIED / LOCAL DENIALS | Top10身份、prior quote quality、原始open可用；已有warmup函数接出8个ADV；SZ300220/SZ002382缺量不填零。只验证首个session，不宣称全2015接线完成 |
| 首日ordinary执行状态 | SOURCE INTAKE BLOCKED | 原States均active且非ST，但现有C1独立限价receipt对10只首日均无匹配，不能将provisional限价升级认证；限定现有receipt库存结论 |
| Strategy actual account path | NOT_STARTED / INTEGRATION PENDING | 源限价、conditional multi-sale/cash/personal-fee Core wiring、持仓事件与独立账户验证待完成；不能用全NO_ENTRY路径通过，R1–R3仍unknown |
| Development economic evaluation | AUTHORIZED / NOT EXECUTABLE YET | 用户最新授权2015–2023调参与经济评价；须先完成真实路径和独立验证，无需再申请同一权限。2024+ 禁止 |

R1–R3 的 handler 分为普通成功处理和未知检测停机，不能把后者写成一般公司行动已实现。
148/528/921 数量不是 Core blocker，也不是实际影响次数；可信 rights/conversion/terminal 总数仍 unknown。

**当前没有待关闭的通用 Core blocker。**
C1 按新历史研究合同验收通过；C2 回归通过。R1–R3 的实际路径验证仍 pending，
Core Ready 不代表已证明 2015–2023 全池或特定策略无账户断点。
不再以精确历史发布时间缺失阻塞 Core，也不以空事件表宣称不存在未知公司行动。
E3本轮已冻结30候选搜索空间并完成target-only结构对照；没有产生真实持仓路径或收益，尚未选择V2。
actual R1/R2/R3数均unknown；目标成员不能证明异常从未暴露。已完成采集不再列blocker。
E2机制不扩scope；E3专项来源与账户接线为下一责任，不通过改变候选绕过问题。
提交推送后停止审核；当前停止因实际执行依赖，而不是development调参/经济评价未获授权。
