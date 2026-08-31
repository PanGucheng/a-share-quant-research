# Extended Matrix Overlap Lineage Resolution V1

> 状态：`lineage_resolved`。旧 frozen Matrix 与旧 `partial_extension` 均保持 byte-immutable；未读取模型 outcomes，未启动 Structured ML 或 Research Protocol redesign。

## 最终结论

- New Extended Matrix identity: `extended-matrix:22fbf692d22e97a90d3b63ad1258f4867be38f5476494e27fbf68d5825cc38f0`
- Parent Extended Matrix identity: `extended-matrix:af96ac22035f884b120d18a4a92e06febdff52e9e94e3cb4cbc074241b40cce1`
- Historical partitions: `762`（corrected `110`；parent references `652`）
- Overlap factors: `774`
- Exact / explained / quarantined: `739` / `35` / `0`
- Key-set pass: `True`
- Exact-value pass against frozen parent: `False`（不以复制旧 bug 为目标）
- All old mismatches explained: `True`

## Root causes

```text
                           root_cause_category  factor_count  old_value_difference_count  new_value_difference_count  resolved
  explained_upstream_statement_window_residual            19                         152                         152      True
frozen_and_parent_extension_implementation_bug             1                         113                       71857      True
              frozen_parent_implementation_bug            15                      937034                      975996      True
                        overlap_comparator_bug             1                           2                           0      True
```

### Alpha101

15 个 Alpha101 mismatch 具有同一主因：冻结计算的全区间列轴包含未来才出现的股票，而上游部分公式会先把结构性 NaN 填为 0/1，再执行横截面 rank；因此 raw mask 被中间 fillna 取消，早期横截面依赖未来 instrument axis。新实现不改公式，只在每个 rank operator 前重新施加当日 PIT eligibility。

### TA

`ta_momentum_kama` 的上游实现使用 `np.roll` 生成滞后，序列开头读取序列末尾，递归状态随后持续传播。新实现采用因果 diff、明确的 `2000-01-04` state anchor 和跨年连续缓存。`ta_volatility_kcp` 两边是相同 `-inf`；旧 comparator 误报，同号 infinity 现按 lineage-equal 处理，但该因子继续沿用既有 non-finite qualification block。

### Fundamental PIT

19 个 factor 的 residual 只涉及 `SZ300094` 的 overlap 前两日和 `SZ002217` 的同比基期。旧父 artifact 的 statement endpoint 从 2018 开始；扩展抓取从 2008 开始，恢复了当时已经公开的旧事件和 prior-year base。PIT 规则、same-day ordering 与 no-future contract 未发现错误，因此保留 extension 值并记录 source-window provenance。

## Validation

- Partition integrity: `True`
- Causal KAMA state/cache equality: `True`
- Parent continuous-state checks retained: `True`
- Practical PIT checks retained: `True`
- Historical universe overlap retained: `True`
- Quarantine: `0`

逐因子决策见 `factor_lineage_decisions.csv`；新 overlap 数值审计见 `matrix_overlap_validation.csv`；Fundamental source-window 证据见 `fundamental_statement_window_evidence.csv`。

## 下一阶段条件

从 overlap lineage 条件看，新的 versioned Extended Matrix 已可作为 Dataset / Research Protocol redesign 的正式输入：`True`。这不等于已启动下一阶段，也不授权读取模型结果或训练模型；后续必须显式绑定上述新 identity，并继续尊重 frozen qualification（包括 KCP 的既有 block）。

## Governance

Factor Universe V2 definitions、Research Protocol、Strategy V1、Forward Track、旧 frozen Matrix 与旧 partial-extension artifact 均未改变；Structured ML/model/portfolio 工作未启动。
