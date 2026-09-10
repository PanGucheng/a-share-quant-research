# Literature Factor Representation D1

2026-09-10。计划先以 `b877ad3` 提交；随后按用户授权实施 D1。

当前为 **D1 IMPLEMENTED / STRUCTURAL DEFECT FOUND / POLICY REVISION REQUIRED / D2 NOT AUTHORIZED**。
完整扫描尚未执行，所有 candidate 均未冻结。

第一版诊断候选见 [candidate_v1](candidate_v1/recipe.json)，自然列数 R218/C201/H358，
U61、raw representatives157、rank outputs140，其中116个 singleton，2个 multi-family。
逐项状态见 [494 inventory](candidate_v1/inventory_494.csv)。32个 Alpha101 经济语义仍未解决，
提议沿用 canonical raw identity 不等于完成专业语义解释；correctness blocker 不得进入 U。

12日期 feature-only canary 完成：23544行、独立 naive oracle 全部通过，
最大绝对误差 `2.7755575615628914e-16`、mask 完全一致、5组 exact alias 保持相等。
12日中428个可 rank 叶全部达到100且非常数；3个 early-day raw U 的有限样本数为1，
这些 U 不作 rank。无 infinity、无常数 C 输出。不能据此推断全年/九折计数。

实测发现 range-intensity 两 family 组合在2010/2012采样日分别有288/1526、401/1986的
有效输出只依靠一个 family。两个源估计量最小窗口不同，50% family 门槛导致测量轴组成漂移。
下一步依据这一结构缺陷收紧为全部 frozen families 可用，family 内节点保留50%候选门槛，
只保留一个可继续审阅的修订候选；V1保留为诊断证据，不供D2选择。

代码包括受限 feature reader、确定性 R/C/H 构造、独立 oracle、按月断点续跑及逐年/折诊断汇总。
本轮未训练模型、未读取已封存 prediction/IC/importance 等 outcome，未访问2024+研究值。

检查：D1 synthetic37项通过；加 V3 precompute regression 共42项通过；fast46项及Ruff通过；
PowerShell语法通过；canary独立重放与receipt/aggregate复核通过。
没有运行完整 `check_quality.py full`：其中历史 closeout validators 会访问当前任务禁止的
冻结 outcome/近期证据。采用 scoped synthetic checks，不宣称全仓验证通过。

运行证据位于 `outputs/literature_factor_representation_d1/d1_structure_20260910_v1/canary/`。
长时间全历史扫描由用户执行，当前先修订并复核已暴露的结构问题。
