# Economic Translation MVP — 当前 E2 状态

2026-09-15；基线 `main@6656a42`。**E2 CORE PARTIAL / GENERIC INTEGRATION GAPS；
STRATEGY PATH NOT STARTED。整体 E2 STILL BLOCKED。**

已采纳 Core Infrastructure 与 Strategy-specific Account Path 分开验收。
停止以全库历史异常清零为前提的 E2 治理工作流；R1–R3 不再阻止 Core 验收，
只有实际冻结路径形成 exposure 后，才要求补证、处理或保留账本停止。

详细 [阶段评审与 path contract](STAGE_BOUNDARY_REVIEW.md)、[当前 Matrix](MATRIX.md)、
[本轮验证](STAGE_BOUNDARY_VERIFICATION.json)。原 [Scope Review](MVP_SCOPE_SIMPLIFICATION_REVIEW.md)、
[Scope 验证](SCOPE_VERIFICATION.json)、[语义审计](SEMANTIC_RECONCILIATION.md) 和
[语义验证](SEMANTIC_VERIFICATION.json) 保留为历史证据，不重写原始结论/receipts。

## 仍缺的通用能力

1. **C1：来源绑定的 PIT 执行输入适配与有界验收。** 原始采集已完成，
   但日终状态的 known_at 仍为空、ordinary regime 未认证；缺少从现有证据到 Fact/prepared
   的可消费输入交付。只需验证预先固定的非空普通 canary 与拒绝分支，不要求全池每个事件补完。
2. **C2：新 scope 与 Qlib 日级生命周期接通。** 旧 continuity 仍可能因坏的未持有候选而停止，
   旧 prepared schema 要求普通上下限；新的 carry 原语尚未接入统一执行/事件/估值流程。
   需要阶段检查点、失败后账本保留及跨日集成验收，不需要完整特殊制度模拟器。

PIT 拒买、持仓/权利保留、未知停机、普通成交和普通公司行动组件已有验证，
不能因此宣称整个基础设施失败；也不能把组件通过升级为已经完成 C1/C2。
本轮没有修改这些生产组件或实现通用接线。

## 已转为路径条件事项

R1 是实际市场敞口的估值冲突；R2 是实际敞口的身份/生命周期/结算；R3 是实际登记/未结权益。
3 个 close 冲突、148 起覆盖事件、528 个未决权益键、183 个潜在零碎股键及 921 个去重诊断键
全部保留，但不再作为 Core 前置修复清单。实际触发数、已证明 irrelevant 数量目前 unknown。

普通分红、整数红股、固定现金应收、限定同股数迁移有处理原语；一般换股/退市/零碎股分配
尚不能自动结算，触发则补证或 halt。安全 halt 可以通过 Core 故障测试，不能通过完整路径验收。

## 后续阶段怎样推进

C1/C2 关闭并审查后，可进入 E3 Freeze Preparation，完成 universe/holding、K/buffer、AUM、
现金保留、费用和 benchmark 等字段。当前仅交付准备合同，未冻结/选择参数，未激活真实 path。
固定策略函数必须先冻结，再由冻结分数和逐日真实模拟成交生成 exposure；不能把目标名单等同持仓。

独立 preflight 不读分数，检查实际股数、现金、应收和红股的连续性；结果开放仍关闭。
遇到 R1–R3 保留最后完整检查点并停机，不能修改策略躲避异常；halt 后未来未走到的区间不能标无影响。
仅当路径完整、触发事项解决、独立验证和边界会计通过，且用户另行授权，才允许 economic evaluation。

严格 ADV warmup 缺值拒买、date-PIT、daily-open-reference、税前口径等既有 MVP 近似保留。
不能用它们填零未知权益、伪造盘前证据或绕过身份/估值冲突。

## 验证与停止点

93 项既有 E2 范围测试通过；synthetic probe 重现 scope 接受/旧 continuity 拒绝的两个接线边界，
并确认账户不变、空 known_at 不可用。它是缺口定位，不是统一执行路径验收。
本轮未重采 Quotes/States/Dividends，未重跑 E1、读 B494 分数、生成真实 NAV/收益或访问 2024+。

**全库修复前置要求已关闭；通用 C1/C2 尚未关闭；当前不宣布 E2 CORE READY。**
提交推送后停止等待人工审核，不自动进入 E3/E4。
