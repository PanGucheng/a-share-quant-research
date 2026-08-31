# 下一阶段任务：Extended Matrix Overlap Lineage Resolution V1

## 背景

请先完整审阅当前仓库、最新 Extended Matrix、frozen Matrix、Factor Universe V2、Historical Data Engineering Extension V1 及其 overlap / lineage artifacts。

当前历史数据工程已经取得实质结果：

- Extended Matrix 已真实生成；
- price-volume 长历史已推进到 2000 年附近；
- Full Factor Universe V2 practical history 已推进到 2010 年附近；
- PIT、historical universe、partition continuity 等核心检查已经通过；
- 新旧 Matrix 在 overlap 区间的 factor key set 完全一致；
- 738 个因子值完全一致；
- 仍有 36 个因子存在值级差异；
- 差异绝大多数集中于 Alpha101，另有极少 TA 和 Fundamental PIT residual；
- 当前 Extended Matrix 状态因此保留为 `partial_extension`；
- Structured ML 尚未启动。

本阶段不再研究历史数据还能不能更早。现在的核心问题是：为什么同一个 frozen factor
definition，在新旧 Matrix overlap 区间会得到不同值？

## 核心目标

请系统解决剩余 36 个 overlap lineage differences。最终每一个存在差异的 factor 都应被归入
明确类别，例如 historical extension/frozen parent 实现错误、两边语义不同但各自有来源依据、
warm-up/state/window horizon、cross-sectional universe/ranking scope、raw field/VWAP/adjustment、
floating/initialization、PIT upstream revision residual，或其他可以证明的 lineage 原因。

不要只统计有多少值不同，要尽可能追到为什么不同。

## 优先处理 Alpha101

当前绝大多数差异来自 Alpha101，而且部分因子在 overlap 区间几乎完全不一致。因此 Alpha101
是本阶段最高优先级。请自行审阅 frozen Factor Universe V2 definition、KunQuant/Alpha101
source、当前 factor implementation、historical extension implementation、相关 adapter、
cross-sectional operators、rank/ts_rank、correlation、covariance、decay、signed power、scale、
VWAP、universe scope、NaN handling、rolling warm-up 和 execution order。

不要预设问题一定来自某一个算子。应通过最小可复现实验逐层缩小差异来源。重点不是让两个
结果看起来一样，而是确定哪一个 implementation 才符合被冻结的 Factor Universe V2 semantics。

## Frozen definitions 是判断基准，但 frozen artifact 不是绝对真理

Factor Universe V2 definitions 已被冻结，本阶段不得偷偷改公式来追求一致。但需要区分
definition authority 和 historical calculated artifact。

如果调查证明 frozen Matrix 的计算实现存在 bug、Extended Matrix 的实现更符合冻结公式，
不要为了 overlap 100% 而复制旧 bug：保留旧 frozen artifact 不变，明确记录 bug 和 lineage，
生成 corrected/versioned implementation，不静默改写历史证据。反过来，如果 Extended Matrix
实现偏离 frozen semantics，则应修正 Extended Matrix。

## 调试与语义检查

不要一次性整体重算 Alpha101 后再看结果。研究逻辑应保持：

```text
factor mismatch
↓
small reproducible sample
↓
operator / input / universe comparison
↓
root cause
↓
shared fix
↓
targeted recomputation
```

目标是建立可复用的 lineage debugging 方法，而不是人工逐个猜。

Cross-sectional semantics 必须重点检查 ranking universe、missing-stock handling、suspended
stocks、eligible universe、top-N selection、PIT membership、instrument ordering 和
cross-sectional NaN policy。若 historical extension 与 frozen Matrix 同一天使用不同横截面，
即使 raw price 完全一致，也可能导致整个 factor 横截面变化。

Warm-up 与历史上下文也需要检查。Extended Matrix 拥有更长历史，某些 rolling/stateful factor
可能因完整历史状态与较短 bootstrap window 的差异而不同。应判断 frozen semantics 要求完整
历史状态还是固定 warm-up contract。不要为了复现旧 Matrix 人为截断历史，除非冻结 contract
明确要求；有限 bootstrap 的边界效应应记录为 lineage。

## TA residual

在 Alpha101 主问题解决后审阅 initialization、rolling horizon、recursive state、library version、
NaN handling 和 warm-up。明确实现差异应统一；浮点级非实质差异可采用有依据的 tolerance，
但不得为了通过测试随意放宽。

## Fundamental PIT residual

判断极少数 Fundamental PIT 差异属于 current endpoint revision、same-day revision priority、
announcement-date ordering、source vintage 或实际 implementation bug。若属于 leakage-safe practical
PIT 下不可避免的 upstream revision residual，可明确 version/provenance 后接受，不应重新开启整个
历史 Fundamental 数据工程；若发现 PIT ordering bug，则必须修复并重新验证 no-future。

## Factor lineage decision

对每个 mismatch factor，最终至少记录：

```text
factor
root cause
authoritative semantics
action
resolved?
remaining risk
```

Action 可以是 fix extension、preserve extension、create corrected version、accept explained residual
或 quarantine。不得允许 unexplained mismatch 直接进入后续 Structured ML。

## Quarantine

若极少数因子经充分调查仍无法确定正确实现，可建立 unresolved lineage quarantine，但必须数量有限、
原因明确、从连续 representation 中排除、不修改 frozen definitions、后续模型不得使用且 manifest
明确记录。是否需要 quarantine 由实际调查决定，不要求必须做到 774/774 exact。

## Extended Matrix 处理原则

当前 `partial_extension` artifact 必须保持 immutable，不得覆盖。若本阶段发生任何值修正，生成新的
Extended Matrix identity/version 并保留 parent lineage。新 Matrix 仍需验证 keys、values、missingness、
PIT、universe、stateful continuity、partition integrity 和 overlap。

## 成功标准

成功不等于 overlap 数字从 36 变成 0；真正标准是所有剩余 mismatch 都得到可审计解释和处理决策：
exact match + explained acceptable residuals + very small explicit quarantine，而不是通过改公式或放宽
tolerance 强行 100% match。

## 本阶段不要做的事情

不要继续扩历史数据、新增数据源、修改 Factor Universe V2 definitions、扩展因子库、redesign Research
Protocol、启动 Structured ML、做 training-history comparison、训练 LightGBM/DoubleEnsemble、修改
Strategy V1 或修改 Forward Track。本阶段只解决 Extended Matrix overlap lineage。

## 最终报告重点回答

1. 36 个因子分别为什么不同？
2. 差异是否集中在共同 operator/execution semantics？
3. Alpha101 的主要 root cause 是什么？
4. 是否涉及 cross-sectional universe？
5. 是否涉及 warm-up/long-history state？
6. 是否发现 frozen implementation bug？
7. 是否发现 extension implementation bug？
8. 哪些因子被修复？
9. 哪些 residual 被接受，为什么？
10. 是否存在 quarantine？
11. overlap 最终达到什么状态？
12. 新 Extended Matrix 是否生成？
13. 新 artifact identity 是什么？
14. PIT/universe/partition/stateful checks 是否仍通过？
15. 当前 Extended Matrix 是否已可作为下一阶段 Dataset/Research Protocol redesign 的正式输入？

## 执行方式

这是开放式 debugging + lineage research + data engineering 任务。先理解真实 implementation，再决定
具体调试方式。总体逻辑：inspect mismatch inventory → cluster by lineage/implementation → reproduce
smallest failures → identify root causes → fix or classify → targeted recompute → full overlap validation →
new artifact if justified。不要机械照搬本 prompt 中列出的可能原因。

## 治理与 Git

必须保持：

```text
model outcomes read = false
Structured ML started = false
Research Protocol redesign started = false
Factor Universe V2 definitions changed = false
Strategy V1 changed = false
Forward Track changed = false
old frozen Matrix changed = false
current partial-extension artifact overwritten = false
```

保护用户已有未跟踪文件。完成后 review diff，运行针对 mismatch 的 tests、必要全仓 tests/quality
checks，检查 frozen artifacts 和 lineage manifest，commit、push，并汇报 branch/commit SHA、root-cause
分类、exact/explained/quarantined 数量、新 Matrix identity 以及是否具备进入下一阶段的条件，然后停止。
不要自动进入下一阶段。
