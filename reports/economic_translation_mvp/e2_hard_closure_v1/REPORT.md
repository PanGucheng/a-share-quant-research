# Economic Translation MVP — 当前 E2 状态

2026-09-15；基线 `main@146cb04`。**C2 已验收关闭；C1 已实现但真实来源验收未通过。
E2 CORE PARTIAL / E2 STILL BLOCKED；STRATEGY PATH NOT STARTED。**

用户本轮要求只实现并验收 C1 + C2。本轮已交付两个 opt-in 模块、定向测试、固定真实 canary
与独立验证，没有扩展 E2 scope。详见 [实施验收](CORE_IMPLEMENTATION_ACCEPTANCE.md)、
[当前 Matrix](MATRIX.md)、[机器证据](CORE_ACCEPTANCE.json)。

## 已解决：C2

CoreSession 复用 Qlib Account/EventPosition/EconomicOpenExchange，将盘前 A、公司行动、
Entry/Holding 门控、开盘 B、日终 C 与登记接通。坏的未持有候选只拒买；特殊持仓和现金应收
通过独立 carry 分支保留，不构造假的普通限价或行情。普通订单沿用原 lot、T+1、容量和费用检查。

账户日只在工作副本全部检查通过后提交。事件后、成交后、收盘后和提交前故障均保留原账户；
恢复重放结果一致。现金/红股在原股卖出后继续存在，未知权益/估值和非整数分配继续停机。
C2 为 **CLOSED / ACCEPTED WITHIN CORE SCOPE**，不是实际策略路径已经跑通。

## 尚未验收通过：C1

输入适配已实现 instrument/field/phase/source/hash 绑定，未可得版本先过滤；
现有量价 overlay 接入严格 prior-20 ADV，开盘价单独使用固定原始源，避免日终诊断影响开盘。
已允许的日线阶段近似显式标注 source_known_at=null，不拿它补造 state/events_clear。

真实样本固定为 SH600000 / 2020-08-24。21 行切片、独立量价和涨跌停表验证通过；
ADV20 双方均为 50,322,888.6 股。但固定来源未提供普通状态、身份可得性和完整事件覆盖的
盘前证明，实际为 **NO_NEW_ENTRY**。事件切片为空也不代表完整无事件。
因此 C1 为 **IMPLEMENTED / REAL-SOURCE ACCEPTANCE BLOCKED**，不能把拒绝分支通过当作普通路径成功。

这仍是原 C1 的证据缺口，不新增 blocker 或扩展采集，也不退回全库异常修复。
R1–R3 保持冻结实际 exposure 的条件事项；148/528/921 inventory 和旧 receipts 均保留。

## 验证与边界

新增定向测试覆盖分阶段输入、普通会计、carry、拒绝与失败恢复；既有 E2/fast/Qlib 检查通过。
独立 canary 程序核验 14 个输入 hash、4 个输出 hash，并从原始数据单独复算 ADV。
最终输出 e2_core_acceptance_v4，前版同一固定样本的核验结果保留；未换样本、未改通过标准。

未重采三项长扫描、未重跑 E1、未读取分数或 2024+、未运行真实账户/收益评价。
旧执行组件、B494/canonical/冻结证据保持不变；费用参数选择仍在原 E3 范围。
**当前不能宣布 E2 CORE READY，不进入 E3/E4。提交推送后停止等待人工审核。**
