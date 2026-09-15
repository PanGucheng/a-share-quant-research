# C1 + C2 实施与验收

2026-09-15；基线 `main@c312469`。用户要求根据《调整 C1 历史可得性要求并完成 E2 Core 收尾》调整。
附件 SHA256：`68512c2fbb9a799c0214cf8ee0a78117459329562c6f627f2ff6242e40a7cef4`。

**C1 CLOSED / HISTORICAL APPROXIMATION ACCEPTED；C2 CLOSED / SYNTHETIC INTEGRATION ACCEPTED。**
当前为 **E2 CORE READY / STRATEGY PATH VERIFICATION PENDING**。通用 E2 infrastructure 在此停止。
验收对象是受支持的 Core 机制，不是九年全池或某个策略账户连续运行证明。

## C1 历史要求的调整

采纳历史日级研究与实盘 freshness 分开的建议。可信逐日状态在对应 session 生效，标记
`historical_session_effective`，`known_at` 保持 null，不生成具体发布时间。
这是用户授权的研究近似，不能表述为精确盘前 PIT 已认证。

[输入适配](../../../qlib_integration/economic_core_inputs.py)与[历史来源适配](../../../qlib_integration/economic_historical_inputs.py)
保留 instrument、effective session、source/hash、availability basis 和 approximation 清单。
原 strict 模式仍为默认；历史事实必须由显式 historical 模式消费。
旧 overlay 的 `ordinary_regime_certified=false`、原 receipts 和旧失败验收均保持原样。

ordinary 要求日级 ST/停牌状态、无歧义身份/board、至少五个此前已观察到的交易 session，
以及独立当日涨跌停与原始 preclose、已有 dated rule 一致。此前 session 数是上市年龄下界，
不是精确 IPO 天数；日级证券与独立限价作为在市普通制度的研究近似，不精确证明从未重新上市。
已知特殊、缺失、冲突、身份不明和阻塞事件仍禁止准入。
不将旧 overlay 使用当日 high/low 诊断得到的 ordinary/special 标签直接用于 A。

A 只消费状态、身份、事件审查、前 20 日量与前一日质量；A 的参考估值用独立当日 reference，
不充当开盘成交价。B 使用另行绑定的原始 daily open/reference evidence；C 才消费 close。
historical prepared 的 known_at/state_known_at 留空并附 basis；strict prepared 拒绝此 schema。
缺 open 不回退 close，缺 ADV/质量不准入；未来版本先过滤，不倒灌历史黑名单。

## 事件语义与持仓边界

历史 entry 的 `events_clear` 是内部兼容字段，表示已审查来源中未发现已知、当前生效的未解决阻塞事件，
不再声称 distribution/rights/conversion/terminal/identity 五类事件全集完整。
必须提供 dated review、reviewed sources、event IDs、状态和 `coverage_complete=false`。
状态区分 no_known_blocking、known_handled、known_blocking、unresolved；后两者拒绝新买。
覆盖不完整是独立维度，不自动等于存在当前未决事件；仅空表也不能产生完整无事件证明。

固定 canary 检查既有当日状态、身份、独立限价，以及登记日/除权日在该 session 的事件元数据。
未来公告版本不作为历史黑名单；日期未知的当期事件按未解决处理。该日匹配记录为 0。
这是 flat-start 一日样本的已知风险检查，没有声称审清历史遗留应收或未来事件。
一般 rights/conversion/terminal 数据仍可能不完整，实际 exposure 的 R1–R3 验证继续负责发现缺口。

股数、登记权利、应收和未上市红股仍全检。已登记未结事件若遗漏于当日 review，或事件缺处理条款，
仍 HALT_RETAIN；C 新事件缺登记条款不能提交。没有处理 148/528/921 全库案例或把未知权益记零。

## Live contract 独立保留

`adapt_phase(mode="live", live_ttl_seconds=...)` 要求真实 known_at、observed_at、fetched_at，
来源与 receipt hash 一致，instrument/session 一致，无冲突，获取早于 cutoff，观测在明确 TTL 内。
TTL 必须显式提供，没有冻结实盘 TTL。required entry 字段缺失/过期即 NO_NEW_ENTRY。
所有 historical/date-level phase approximation 都被 live 模式拒绝。

本轮仅实现输入校验接口；CoreSession 明确拒绝 live mode，没有 live provider 或券商接入。
live 测试是 synthetic receipts，不代表真实供应商 freshness 已验收；2015–2023 边界未解除。

## 固定 canary 与独立验收

保留[原 scope](CORE_CANARY_SCOPE.json)，本轮模式与工程订单先固定在[补充 scope](HISTORICAL_CORE_SCOPE.json)。
仍为 SH600000 / 2020-08-24，历史窗口 2020-07-27 至 2020-08-21；没有更换样本或搜索成功案例。

| 检查 | 最终结果 |
|---|---|
| 源 hash、状态/身份/限价绑定 | PASS；16 个输入 hash，21 个证券日 |
| 严格 prior-20 ADV | 原始源独立求和与适配均为 50,322,888.6 股 |
| 历史准入及非空执行 | ALLOW_ENTRY；固定 100 股买单成交一次，A→B→C→COMMITTED |
| 工程会计/估值 | 股数、独立标量现金/费用与 C 价格一致性通过；不生成 NAV/PnL |
| 负例与 C2 回归 | 43 项历史/live 新测试 + 125 项原 E2 检查通过 |
| 仓库检查 | fast 46 项、Qlib 6 项通过；总计 220 项，定向 Ruff 通过 |

工程账户固定 10,000 元测试现金，不选择策略 AUM/K。旧万三费率仅用于既有引擎工程断言，
不冒充用户万2.5；个人费用配置及历史税费字段仍按原 E3 合同审议。
[独立核验器](../../../scripts/verify_e2_historical_core.py)不导入生产适配代码，重算 ADV，核对
state/identity/open/close/限价来源、阶段隔离、空 known_at、事件范围和输出 hashes。
完整账户故障恢复与权益算式由原 C2 synthetic 集成及本轮回归验收。

最终输出 `outputs/economic_translation_mvp/e2_historical_core_v2`，见[机器汇总](HISTORICAL_CORE_ACCEPTANCE.json)。
v1 同样本核验保留；v2 绑定非有限限价拒绝、未来版本过滤和历史持仓 reference 的最终保护。
原 [CORE_ACCEPTANCE](CORE_ACCEPTANCE.json) 的严格 PIT 失败结论仍有效于旧合同，未改写为 PASS。
本次按新合同通过，不声称原始证据曾包含历史发布时间。

## 停止点

**C1 与 C2 均关闭；E2 CORE READY / STRATEGY PATH VERIFICATION PENDING。**
不再开发通用 E2 infrastructure；策略未冻结/未启动，R1–R3 仍可能触发 HALT_RETAIN。
未重采三项长扫描、重跑 E1、修改 B494/canonical、选择参数、运行正式策略、生成 NAV/PnL/Sharpe/CAGR 或访问 2024+。
完整 full tier 含超出本轮授权的旧实值验证，本轮使用上述 outcome-isolated 定向套件及 fast/qlib。
提交推送后停止等待人工审核；不自动进入 E3/E4。
