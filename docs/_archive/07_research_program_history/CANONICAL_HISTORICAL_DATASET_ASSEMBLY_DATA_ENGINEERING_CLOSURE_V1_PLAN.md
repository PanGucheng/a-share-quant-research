# 下一阶段任务：Canonical Historical Dataset Assembly & Data Engineering Closure V1

> 生命周期：CLOSED execution plan。本文保存当时的执行要求，不是重启研究的授权；当前数据 authority
> 见 [`../../CANONICAL_RESEARCH_DATASET.md`](../../CANONICAL_RESEARCH_DATASET.md)。

## 背景与目标

在 Historical Data Engineering Extension V1 和 Extended Matrix Overlap Lineage Resolution V1
之后，项目已确认长期 price-volume history、2010+ Full V2 practical history，以及 Alpha101 PIT-rank、
causal KAMA、Fundamental provenance 等 lineage。旧 frozen Matrix、旧 partial-extension 与
lineage-resolved historical Matrix 必须保持 immutable。

本阶段的唯一目标是建立一份 2010–2026 semantics 连续一致的 canonical research dataset。不得在
2021-02-01 后切回已经证明有实现问题的 frozen values，也不得覆盖任何旧 evidence。

## Continuation semantics

自行判断哪些 2021–2026 factors 需要重算。至少重点处理 corrected PIT-rank Alpha101、causal KAMA
和其他已确认 corrected semantics；已经证明一致的 factors 应直接复用并保留 lineage reference，不能
为了流程统一无意义地全量重算。

同一 factor name 在整个 canonical 时间轴上只能表示一种实现语义。若无法统一，必须 version、rename
或隔离，不能静默形成 implementation regime break。

Fundamental 继续采用 practical reconstructed PIT，保持
`information_available_date <= decision_date`；没有新 PIT ordering/revision bug 时，不重启大规模
Fundamental 审计。Historical Universe 同样沿用 practical historical universe，重点验证 2021 边界
语义连续，不重新要求 archived security-master snapshots。

## Canonical artifact contract

若证据充分，生成新的 versioned canonical artifact，明确：

- artifact identity、parent lineage 与日期范围；
- factor coverage、factor-family frontiers 与 qualification；
- PIT / universe contract；
- corrected factor semantics；
- reused versus recomputed partitions；
- known accepted residuals；
- blocked / non-research-usable factors。

不能因为 schema 有 774 个 definitions 就宣称 774 个全部 research-usable，必须继续尊重 Factor
Universe V2 qualification。

## Validation

验证时间 key、schema、factor semantics、PIT leakage、universe、partition integrity、cross-year state、
Alpha101、causal KAMA、missingness、non-finite qualification 和 source lineage。特别检查 2021-01 /
2021-02 边界，区分市场、source、universe 与 implementation 变化；implementation break 不得进入
canonical dataset。Canonical 不要求 100% reproduce frozen values，差异必须有明确 lineage，不能恢复旧 bug。

完成后更新 authority/current-pipeline 文档，让未来任务绑定 canonical dataset identity，而不是默认读取
old frozen Matrix。若所有 continuity、PIT、universe 和 state checks 通过，则将 Historical Data Engineering
正式标为 CLOSED；未来仅在发现明确 data bug、leakage 或 provenance failure 时重开。

## Scope and governance

任务完成后停止，不设计 validation windows/folds，不比较 training history，不运行模型或 Structured ML，
不修改 Research Protocol、Factor Universe V2 definitions、Strategy V1 或 Forward Track。

必须保持：model outcomes unread；Structured ML / Research Protocol redesign 未启动；old frozen、partial
extension 与 lineage-resolved evidence 未改写。完成 diff review、focused/full checks、artifact identity 与
immutability checks、文档更新、commit 和 push 后，汇报 branch、SHA、canonical identity、range、remaining
blocker、Historical Data Engineering 是否 CLOSED，然后停止。

