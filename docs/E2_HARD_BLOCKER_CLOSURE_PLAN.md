# E2 Hard-Blocker Closure：本轮执行范围

2026-09-13，基线 main@8501456，已fetch。用户要求参考附件、结合现实推进E2。
采纳 execution-only normalization、unknown fail-closed、真实事件inventory优先、held union、独立warmup。
更正：能拒绝unknown是工程安全条件，不代表未知已解决或九年账户能够跑完。
“日期级PIT可接受”必须明确输入日期早于订单日、批次早于下单，不能伪造历史小时级记录。
早期费用的保守候选单列人工审议，不与×100的单位错误等权，也不自动当成已批准。

本轮不继续K/AUM/benchmark选择，不读真实prediction、label或策略结果，不生成真实NAV，不改frozen research data。
2014数值唯一例外为2015首日ADV20所需2014-12-04至2014-12-31的20个交易日；只用于量单位/停牌/ADV。
2024+研究值保持关闭。长扫描仍由用户执行，有限canary由Codex完成。

实施：

1. 隔离的原语区分identity与单位规则，逐证券/区间/源hash，OHLC与量额检查失败不给valid quote；不自动学习倍率。
2. 有效日状态表复用既有availability、dated limits；unknown/special阻止成交，持仓估值或terminal事件未知则阻止账户推进。
3. Qlib Position最小扩展单列现金应收、红股应收/冻结量；record/ex/pay/listable独立，raw价与事件不重复复权。
   使用已取真实事件字段核查适配条件；仅synthetic账户守恒验收，真实账户不运行。
   未覆盖税、配股、fractional entitlement、terminal对价不猜测，明确fail closed。
4. 固定网络样本：三只既有held gap证券原区间、601313/601360历史分段、少量2014warmup单位交叉、每年一个预定ex-date事件切片。
   整年事件inventory不是“每年一个日期”的计数；完整按日期分页采集交用户长跑。空表/权限失败不等于无事件。
5. 全期quote扫描提供用户入口：4,416个历史候选从首次出现至2023末的潜在held延伸；只读2015–2023明确字节。
   不推断退出日期、不删除离池股；扫描异常表与区间清单，不能自动把未匹配状态视为可交易。
6. Warmup输入40,000证券日逐值检查和严格ADV接口；缺量且无停牌证据不填零，记录覆盖分母。

验收交付为六份专题/矩阵与验证证据，列清已关闭的工程缺口、待用户执行的全期扫描、剩余真实数据/会计缺口。
只有完整数据与账户验收成立才可称E2 READY；否则E2 STILL BLOCKED，提交推送后停止。
