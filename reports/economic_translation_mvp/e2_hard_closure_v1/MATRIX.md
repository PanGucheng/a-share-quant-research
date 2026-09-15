# E2 Data Readiness Matrix

2026-09-15；基于 `main@6656a42` 的 [Core / Strategy Path 阶段评审](STAGE_BOUNDARY_REVIEW.md)。
**E2 CORE PARTIAL / GENERIC INTEGRATION GAPS；STRATEGY PATH NOT STARTED。**
整体 **E2 STILL BLOCKED**，仅 C1/C2 是当前通用阻塞；R1–R3 转为冻结策略的条件验证。
全库异常清零不再是 E2 前提。原 [scope 验证](SCOPE_VERIFICATION.json) 和历史库存保留。

| 范围 | 当前分类 | 验收结论 / 下一责任阶段 |
|---|---|---|
| Model/B494/canonical/E1 | FROZEN / UNCHANGED | 不重跑、不修改、不回溯删股 |
| Quotes / States / Dividends 长扫描 | COMPLETE / SEALED | 不重采；采集事项不再列 blocker |
| PIT Entry、fail-closed、唯一身份 | CORE PRIMITIVE VERIFIED | 不合格未持有候选 NO_NEW_ENTRY；不是完整输入/执行接线 |
| 股数、现金应收、未上市红股保留 | CORE PRIMITIVE VERIFIED | 非空 exposure 必须全检；unknown 保留并停 |
| 普通 open、T+1、lot、容量、母单费与整数事件桥 | COMPONENTS VERIFIED | synthetic 验证通过；受支持组件不等于统一日级入口 |
| **C1：来源绑定的 PIT input adapter** | **GENERIC INFRASTRUCTURE GAP / OPEN** | sealed daily known_at=null，ordinary_regime_certified=false；尚无非空普通历史输入 canary。按预先固定有界样本验收，不要求全池可买 |
| **C2：scope 与 Qlib session/事件/估值接线** | **GENERIC INFRASTRUCTURE GAP / OPEN** | 旧全候选 continuity 与普通 prepared schema 未分离 carry；须统一阶段顺序、禁止半日提交、验证恢复与重放 |
| 完整特殊交易制度模拟器 | NOT REQUIRED | 特殊/未认证时禁止新买及主动交易；支持有证据 carry，未决权益仍停机 |
| R1：已持有市场权利的估值 | STRATEGY-SPECIFIC CONDITIONAL | 3 个 close 冲突及其他实际估值缺口仅 exposure 命中后补证；mark 检查/HALT 原语已有，不再阻止 Core 验收 |
| R2：已暴露身份、迁移、终止结算 | STRATEGY-SPECIFIC CONDITIONAL | 148 起覆盖事件非已确认退市；限定同股数迁移原语已有，一般终止/带权利迁移需触发后处理或停 |
| R3：已登记或未结权益 | STRATEGY-SPECIFIC CONDITIONAL | 528 个未决键、183 个潜在零碎股键、参考诊断保留；普通桥和精确 claim 描述已有，实际分配/未知条款触发后处理或停 |
| 现金应收独立 carry | CONDITIONAL HANDLER AVAILABLE | 固定金额已知且有来源时无须旧股票行情；未支付不能下单，付款仍需事件证据 |
| 无实际 exposure 的历史异常 | IRRELEVANT ONLY AFTER PATH PROOF | 目前已认证 irrelevant 数量 unknown；中途 halt 后未到达日期标 NOT_REACHED |
| Date-PIT、daily open-reference、严格 ADV20、税前股息 | EXISTING MVP APPROXIMATIONS | 沿用原范围和限制；缺量只拒新买；不能代替 C1 来源绑定、C2 接线或未知权益结算 |
| 个人佣金、early fee、AUM/K/buffer、cash reserve、benchmark | E3 FREEZE FIELDS / NOT FROZEN | 已知用户假设可预填，未决语义须冻结前明确；不新增收益/结构搜索，不默认沿用旧万三引擎 |
| Frozen strategy / actual account path | NOT FROZEN / NOT STARTED | Core 通过后按先 freeze、后逐日成交和权利路径、再独立核验执行 |
| Economic evaluation / E4 | NOT AUTHORIZED | 路径完整且独立验收后仍需另行授权；2024+ 禁止 |

R1–R3 的 handler 分为普通成功处理和未知检测停机，不能把后者写成一般公司行动已实现。
148/528/921 数量不是 Core blocker，也不是实际影响次数；可信 rights/conversion/terminal 总数仍 unknown。

**Core Ready 的必要且有限条件：C1/C2 通过。无需预先修完 strategy-specific inventory。**
通过后可以是 `E2 CORE READY / STRATEGY PATH VERIFICATION PENDING`；之后的路径仍可能 HALTED。
本轮只完成阶段合同与能力核验，未实现 C1/C2，未激活以 Core Ready 为条件的 E3 参数选择或路径运行。
见 [当前报告](REPORT.md)、[本轮验证](STAGE_BOUNDARY_VERIFICATION.json)。提交推送后停止等待审核。
