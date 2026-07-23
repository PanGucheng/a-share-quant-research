# Research / Execution Accuracy Correction V1 实施计划

> 文档状态：正式实施基线（已冻结；模型前强制修正）
> 制定日期：2026-07-23
> 适用仓库：`E:\qlib_prj\qlib_baseline`
> 前置阶段：逻辑 PR #4.1 Selection Holdout Integrity 已完成
> 后续阶段：PR #5A 模型输入协议（当前暂停）

> 2026-07-23 实施回执：第 5.1 节机器级 hard-stop 与 supersession registry 已落地；第 5.2 节 Universe lifecycle v2 已在 clean committed HEAD 上完成完整物化。旧 29 个越界 membership interval 已被截断，329 个非法 key 已全部移除，最终 lifecycle violation、interval overlap 和 removed-key residual 均为 0。当前权威治理状态位于 `outputs/accuracy_correction_v1/current/`，但 Matrix v4、IC v2 与后续研究修正仍未完成，模型 hard-stop 不变。

## 1. 文档权威性与当前结论

本计划接管所有“直接进入 PR #5A”或“当前模型输入已经 ready”的旧表述。逻辑 PR #4.1 已证明选择链不读取 outer test 来决定 FDR、stability、cluster、allowlist 或 weights；这项 holdout 隔离成果继续有效。但是，2026-07-23 的实现级复核确认研究公式、PIT lifecycle 和历史执行语义仍有会改变结果准确性的缺陷，因此当前 48/46/54 split allowlist、透明 score 和历史 OOS NAV 全部降级为被替代证据，不得作为模型或权威收益结论的输入。

本计划已经冻结为 Accuracy Correction V1 的正式实施基线。实现期间只允许用版本化提交修正确定性错误、补齐测试或处理真实阻塞；不得静默改变 PR #6/#7 职责、统计阈值、已冻结研究语义或模型暂停边界。

当前固定状态为：

```text
selection_holdout_integrity_ready = true
research_formula_accuracy_ready = false
matrix_v4_lifecycle_clean = false
pairwise_ic_ready = false
model_research_ready = false
execution_semantics_accuracy_ready = false
market_cache_v2_ready = false
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
```

当前证据的语义为：

```text
current_split_allowlists = superseded
current_transparent_scores = superseded
current_transparent_oos_nav = non_authoritative
historical_test_already_observed = true
production_model_selected = false
```

在 PR #6 与 PR #7 的 Definition of Done 全部满足前，不得实现或训练 Ridge、Elastic Net、LightGBM。

## 2. 已核实问题与优先级

### 2.1 P0：PIT lifecycle 实际越界

- 现有 PIT membership 有 29 个 interval 超过源 lifecycle；
- 2,588,000 个 key 中存在 329 个非法日期—股票 key；
- 这些 key 上有 18 个 Alpha101 因子产生 5,922 个非空值；
- 其中若干因子已进入当前 split allowlist。

修复不能停留在 validator。PIT 生成逻辑必须保证：

```text
final_membership_interval
= rolling_universe_interval ∩ source_lifecycle_interval
```

### 2.2 P0：Matrix v4 不能统一“删除 329 行”

非法股票可能已经参与同日横截面 `rank`、`scale` 或类似运算，并改变其他合法股票的因子值。因此 669 因子必须先按计算依赖分类：

```text
pure_time_series
cross_sectional
mixed
unknown
```

只有经实现证据证明为 `pure_time_series` 的因子，才允许从 v3 过滤非法 key，并要求所有 common key bit-identical。`cross_sectional`、`mixed` 与 `unknown` 必须在 lifecycle-clean universe 上重算其完整影响范围；`unknown` 在证明前按最保守策略处理。

影响范围不能只取非法 key 当天。若表达式含滚动、延迟、相关性或其他状态传播，日期 `d` 的非法输入可能影响 `d ... d + lookback - 1`；实现必须生成 `impact_date_manifest.csv`，按表达式最大回看和运算依赖给出传播边界。

### 2.3 P0：Daily IC 不是严格 pairwise Spearman

现有实现先在更大的 label-valid 横截面上计算 label rank，再与 factor-valid 子集相关。这不等价于在 `(factor, label)` 同时非空的当日样本上分别重新排名。所有 daily IC、bootstrap、FDR、stability、cluster 和 allowlist 必须由 pairwise-valid v2 IC 重新派生。

### 2.4 P0：开盘执行读取同日 `$change`

当前开盘执行的涨跌停/可交易性判断使用接近 `当日 close / 前收 - 1` 的同日 `$change`。该字段在开盘执行时尚不可知，属于未来市场字段。复核中其与当日收盘收益的相关系数约为 0.999976。必须改为通用字段时点契约，而不是只替换单个字段。

### 2.5 P0：历史税费参数错误

当前配置仍使用 `0.001` 卖出印花税，而 OOS 从 2024-08 开始；2023-08-28 起证券交易印花税已减半征收，应使用按日期生效的费率表。旧 NAV 不能作为权威结果。

### 2.6 P0/P1：长期陈旧估值与执行缓存绑定不足

- split 1 每种方法有 174 个持仓日的价格陈旧超过 20 个交易日，最大 110 日；
- split 2 每种方法有 56 个，最大 76 日；
- 当前估值路径存在 `ffill().bfill()`，并未建立完整 terminal security event 语义；
- market cache 目前只检查文件、schema 和 key，未绑定字段时点、费率、板块/ST/IPO/停牌/涨跌停状态与执行配置。

### 2.7 P1：Bootstrap 缺口语义需在 FDR 前冻结

现有 bootstrap 对序列直接 `dropna()` 后构造 block，可能把真实时间缺口两侧拼接成相邻样本。当前缺失率约 1.63%，大部分来自标签末端，内部缺口集中在少数因子，因此实际影响预计低于 P0，但它属于 FDR 上游，必须在新 FDR 前完成 sensitivity audit；如差异超过冻结阈值，则切换 gap-aware bootstrap。

### 2.8 P1：Score component completeness 属于研究规则

当前各 split 的 score component 最小数仅约 5/48、6/46、6/54，但 score coverage 报告为 1.0，因为缺失组件会按可用项重新归一化。该行为直接决定横截面排序与 TopK，必须在 PR #6 使用 development-only 数据审计并冻结质量政策；PR #7 只能消费冻结后的 score，不得再次改变信号。

### 2.9 其他必须硬化但当前数据未触发的问题

- Alpha101 positional relabel fallback 必须有触发回执，并通过列置换 metamorphic test；
- label row shift 依赖每只股票交易日连续性。当前源数据未发现内部日历缺口或重复 key，但仍需把这一事实固化为 contract，未来数据不满足时必须阻断。

## 3. 阶段拆分与编号

实际 GitHub PR 顺序固定为：

```text
GitHub PR #6  Research Accuracy Correction V1
        ↓
GitHub PR #7  Execution Accuracy Correction V1
        ↓
逻辑 PR #5A   透明基线与统一模型输入协议
        ↓
逻辑 PR #5B   Ridge / Elastic Net
        ↓
逻辑 PR #5C   LightGBM
        ↓
逻辑 PR #5D   历史 OOS 科学比较
        ↓
新未来区间 / forward paper confirmation
```

建议分支：

```text
fix/research-accuracy-correction-v1
fix/execution-accuracy-correction-v1
```

旧文档中的“PR #6 = forward confirmation”编号废止。逻辑 PR #5A—#5D 是研究阶段标签，不预占 GitHub 实际编号；后续 PR 号在创建时确定。

## 4. 共同范围与禁止事项

两个修正 PR 只修复已经识别的正确性、lineage、cache 与 contract 问题，不借机：

- 调低 FDR、stability、coverage 或选因子阈值；
- 根据已观察历史 test 收益调整策略、TopK、权重或模型参数；
- 增加新因子或新数据源；
- 训练任何模型；
- 把历史 bug-fix 结果描述为全新 untouched OOS；
- 覆盖、删除或伪造旧 evidence。

旧产物应保留 artifact ID 和 supersession 关系。新产物必须使用新版本目录、Manifest v2、输入/输出哈希和 code commit；不得在原路径静默改写。

## 5. GitHub PR #6：Research Accuracy Correction V1

### 5.1 立即 hard-stop 与 supersession registry

第一个业务提交必须让机器状态与本计划一致：

```text
research_formula_accuracy_ready = false
matrix_v4_lifecycle_clean = false
pairwise_ic_ready = false
model_research_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
```

这一步必须发生在任何 Matrix v4、Labels v2、IC v2、bootstrap 或全量重算之前。新增 supersession registry，至少记录旧 matrix、IC、FDR、stability、cluster、allowlist、weights、score、freeze、execution 和 NAV 的 artifact ID、被替代原因、替代者（暂空）以及 `model_input_allowed=false`。旧 allowlist、transparent weights、transparent scores 与 historical OOS execution 必须立即分别标记为 `superseded` / `non_authoritative`，所有模型入口继续 fail-closed。

### 5.2 Universe lifecycle v2

修复 membership interval 生成器，在写出前与 source lifecycle 做区间交集。必须验证：

- membership 起止均落在源生命周期内；
- 无上市前和退市后 key；
- interval 无重叠、起止合法；
- key grid 唯一且按日期、股票排序；
- 修复前的 29 interval / 329 key 有完整差异清单；
- 对不受影响的 membership interval 保持一致。

建议产物：

```text
outputs/point_in_time_universe_v2/current/
  universe_membership.csv
  lifecycle_difference.csv
  illegal_key_resolution.csv
  contract_status.csv
  artifact_manifest.json
  universe_report.md
```

### 5.3 669 因子依赖分类

在 Matrix v4 运行计划生成前，提交 `factor_dependency_inventory.csv`。最低 schema：

```text
factor
source_family
batch_id
dependency_class
cross_sectional_operator_present
max_lookback_trading_days
state_propagation_rule
classification_evidence
classifier_version
affected_date_count
recompute_policy
review_status
```

分类要求：

- 以表达式、adapter 和实际实现证据为准，不能仅凭名称或输出相等推断；
- `pure_time_series` 必须证明每个股票的输出不依赖同日其他股票；
- `cross_sectional` 包含 rank/scale/去均值/截面标准化等同日 universe 依赖；
- `mixed` 同时有横截面依赖与滚动/滞后传播；
- 不能可靠证明的因子为 `unknown`，按 `mixed` 重算；
- `unknown` 必须 fail-closed：禁止 `filter-only reuse`，禁止进入“common-key 等价即视为正确”的快捷路径；
- Alpha101 宽表实现必须逐函数检查，不可把整个 family 默认标记为纯时间序列。

### 5.4 Matrix v4 生命周期清洁物化

处理策略：

| 依赖类别 | v4 处理 | 一致性契约 |
| --- | --- | --- |
| `pure_time_series` | 从 v3 删除非法 key | 所有合法 common key bit-identical |
| `cross_sectional` | 在 lifecycle-clean universe 上重算影响日期 | 无影响日期 bit-identical；影响日期差异有归因 |
| `mixed` | 按影响日期及传播窗口重算 | 影响范围外 bit-identical；范围内差异有归因 |
| `unknown` | 按 `mixed` 保守处理 | 不得通过简单过滤复用 |

`impact_date_manifest.csv` 必须记录非法输入日期、受影响因子、依赖类别、lookback/传播边界、重算起止、影响股票数和差异摘要。若无法证明传播上界，则重算对应因子的完整所需区间。

大规模运行前先做覆盖五个 source family 的 canary，至少包含：

- 一个 Alpha158 batch；
- 一个 Alpha360 batch；
- 一个 TA batch；
- 一个 Alpha101 batch，且包含横截面运算；
- 一个项目基础/自定义因子 batch。

来源覆盖之外，canary 还必须正交覆盖以下依赖语义：

```text
一个已证明 pure_time_series 的因子
一个已证明 cross_sectional 的因子
一个 mixed / 复杂传播因子
一个 Alpha101 fallback-sensitive 因子
一个 unknown fixture，证明其被 fail-closed 拒绝 filter-only reuse
```

同一因子可以同时覆盖一个来源和一个依赖类别，但 review bundle 必须逐项列出覆盖关系。canary 必须证明分类器、clean universe 输入、影响日期传播、common-key 一致性、Alpha101 positional relabel 安全性和差异归因可用。完成分类前不得承诺只重跑 Alpha101，也不得默认重跑全部 7.36 GB；最终范围由 inventory 与 impact manifest 决定。

Matrix v4 最低产物：

```text
outputs/full_research_feature_matrix_v4/current/
  factor_dependency_inventory.csv
  impact_date_manifest.csv
  partition_status.csv
  common_key_equivalence.csv
  recompute_difference_attribution.csv
  alpha101_relabel_receipts.csv
  contract_status.csv
  artifact_manifest.json
  matrix_v4_report.md
```

### 5.5 Labels v2 与日期连续性证明

标签继续只使用 PIT-legal key。每个 instrument 必须显式对齐 canonical trading calendar 后再按 horizon 构造未来收益；禁止仅依赖物理行偏移而不验证连续性。

最低 contract：

```text
label_key_unique
label_calendar_continuity_proved
label_horizon_exact
label_terminal_missing_expected
label_source_lifecycle_clean
no_future_feature_in_label_inputs
```

### 5.6 Pairwise Spearman IC v2

每个 `(date, factor)` 按如下唯一流程计算：

```text
pair = rows where factor.notna && label.notna
factor_rank = rank(pair.factor)
label_rank = rank(pair.label)
rank_ic = corr(factor_rank, label_rank)
```

记录 `pair_count`、factor/label missing count、tie policy 和最小样本门槛。增加人工小例、与 `scipy.stats.spearmanr` 的容差对照、缺失模式 mutation 和行顺序不变性测试。

### 5.7 Bootstrap gap sensitivity audit

在 FDR 前比较：

1. 当前 `dropna` 后连续 block；
2. 按真实日期连续 segment 分块的 gap-aware bootstrap；
3. 对内部缺口因子进行受控缺口注入。

在配置中预先冻结差异阈值，至少覆盖 p-value、置信区间、BH/BY pass 和最终候选变化。若任何关键差异超阈值，则正式 bootstrap 必须切换 gap-aware 实现；否则保留现实现也必须附 sensitivity evidence。不得先生成 allowlist 再决定 bootstrap 语义。

### 5.8 重新运行完整研究选择链

固定顺序为：

```text
Matrix v4 + Labels v2
→ Pairwise Daily IC v2
→ Bootstrap audit / frozen bootstrap policy
→ Outer-train FDR
→ Train/validation-only Stability
→ exact development-date clustering
→ split-specific allowlist
→ transparent weights
```

仍然采用：

- 每个 outer split 一个完整 outer-train 669 hypotheses FDR family；
- outer-train FDR 作为候选资格门，inner windows 只作为 development robustness diagnostics；
- stability 不读取 outer test；
- clustering 必须读取精确 `allowed_dates`；
- 不因修复后候选减少而放宽阈值；
- 允许最终得到 0 个合格因子，并诚实阻断后续。

### 5.9 Development-only score component completeness

在生成新的透明 score 前，只使用 outer train / validation 审计每个日期—股票的：

```text
expected_component_count
available_component_count
component_fraction
missing_component_ids
renormalization_applied
```

必须预先冻结：最低 component count、最低 component fraction、缺失时是拒绝 score、降级标记还是允许重归一化，以及 Equal Weight / Stability Weight 是否采用同一政策。报告必须同时区分：

```text
score_row_presence_coverage
component_completeness_coverage
```

不得再用“score 非空率 1.0”代替组件完整性。政策选择不得读取 outer-test 收益或执行 NAV。

输出 `transparent_score_policy.json`，PR #7 只能按其哈希消费 score。

PR #6 可以生成并冻结不包含收益结果的 corrected transparent score，作为“研究信号发生了什么变化”的证据；但不得调用 Qlib Exchange / Executor，不得生成 orders、fills、positions、daily accounting、portfolio return、Sharpe、drawdown 或任何历史 OOS NAV。研究信号与执行收益必须分属两个 PR，避免旧 NAV 与修正 NAV 的变化无法归因。

### 5.10 Selection mutation 与 metamorphic tests

保留既有 test-only mutations，并从原始输入层覆盖：

- 修改 outer-test IC / exposure / labels / raw OHLCVA；
- 打乱 outer-test 行顺序；
- 注入 outer-test 极端缺失值；
- 删除或加入非法 lifecycle key；
- 置换 Alpha101 宽表列顺序；
- 改变不相关股票的值，验证纯时间序列因子不变；
- 改变同日 universe，验证横截面依赖被分类并进入重算范围。

对 outer-test mutations，FDR、stability、cluster、allowlist 和 weights hash 必须不变。对 lifecycle/universe mutations，变化必须严格落在 `impact_date_manifest` 声明范围内。

### 5.11 PR #6 输出与 Contract

建议新增：

```text
configs/research_accuracy_correction_v1.yaml
scripts/audit_factor_dependency_v1.py
scripts/build_full_research_matrix_v4.py
scripts/run_pairwise_daily_ic_v2.py
scripts/audit_bootstrap_gap_sensitivity_v1.py
scripts/validate_research_accuracy_v1.py
outputs/research_accuracy_correction_v1/current/
```

最低 critical checks：

```text
old_research_artifacts_superseded
universe_intersected_with_source_lifecycle
illegal_membership_interval_count == 0
illegal_matrix_key_count == 0
factor_dependency_inventory_complete
unknown_factor_treated_conservatively
impact_date_manifest_complete
pure_time_series_common_keys_bit_identical
cross_sectional_recompute_complete
alpha101_column_permutation_invariant
label_calendar_continuity_proved
pairwise_spearman_exact
bootstrap_policy_frozen_before_fdr
fdr_family_exact_669
stability_holdout_clean
clustering_exact_development_dates
score_component_policy_development_only
selection_mutation_pass
output_hashes_valid
lineage_complete
```

### 5.12 PR #6 Definition of Done

只有以下条件全部满足才能合并：

1. 机器级模型 hard-stop 已生效；
2. lifecycle generator 已从源头修复，非法 interval/key 均为 0；
3. 669 因子依赖分类完成，无未处置 unknown；
4. Matrix v4 按依赖类型过滤或重算，影响范围与差异可归因；
5. Labels v2 连续性契约通过；
6. Daily IC 为严格 pairwise Spearman；
7. bootstrap policy 在 FDR 前完成审计与冻结；
8. 新 FDR、stability、cluster、allowlist 和 weights 从修正链派生；
9. score component policy 仅用 development data 冻结；
10. 所有 mutation/metamorphic tests 通过；
11. 旧产物保留且标记 superseded；
12. 全量测试、validator、Manifest、freshness 与 CI 通过。
13. 未调用 Exchange/Executor，未生成或刷新任何历史 OOS NAV。

PR #6 合并后只有在全部上述条件满足时才允许：

```text
research_formula_accuracy_ready = true
matrix_v4_lifecycle_clean = true
pairwise_ic_ready = true
model_research_ready = true
```

但此时仍必须保持：

```text
authoritative_oos_execution_ready = false
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
```

## 6. GitHub PR #7：Execution Accuracy Correction V1

### 6.1 输入冻结与职责边界

PR #7 只读取 PR #6 已冻结的 split-specific score、`transparent_score_policy.json` 和对应 lineage。不得在本 PR 改因子、FDR、allowlist、weights、score component 规则或选股参数。PR #6 没有生成任何 NAV；首次修正后的历史 bug-fix execution 必须只在本 PR 发生。

### 6.2 Date-aware fee schedule

新增按证券类型和生效日期解析的费率表，至少分项记录佣金、最低佣金、卖出印花税、过户费和滑点。2024-08 之后的当前 OOS 不得再使用 0.001 印花税。费率解析结果进入 resolved config、订单成本明细和 cache key。

### 6.3 通用市场字段时点契约

每个会影响订单生成、可交易性、价格或估值的字段必须记录：

```text
field_name
observation_timestamp
available_at
execution_timestamp
source_artifact_id
```

强制：

```text
available_at <= execution_timestamp
```

任何 future market field 都阻断运行。开盘执行不得读取同日 close、同日 high/low、收盘后 `$change` 或当日完整成交量。若参与率必须使用当日全量成交量，则只能改用收盘后执行或明确的滞后/估计量，不能伪称开盘时已知。

### 6.4 PIT instrument state artifact

构建统一的 point-in-time instrument state，至少包含：

```text
datetime
instrument
board
st_flag
ipo_age
listed
delisted
suspended
previous_close
price_limit_rule_id
lot_rule_id
state_available_at
source_artifact_id
```

板块、ST、IPO 初期、规则变更、停牌与退市状态必须按当时信息判定；缺少关键状态时不得用统一 10% 规则静默替代。

### 6.5 价格限制与 lot 规则

- 价格限制由 `previous_close + PIT rule` 计算，不读取同日收盘收益；
- 区分主板、科创板、创业板、ST/风险警示和 IPO 特殊期；
- 方向语义明确：涨停禁止买、跌停禁止卖；
- lot 规则由板块和交易方向决定，不再假设所有场景都是统一 100 股；
- 所有 approximation 必须进入 contract，不能计入 authoritative readiness。

### 6.6 估值陈旧与 terminal security event

禁止 `bfill` 使用未来价格。可以在有限窗口内用最后一个合法 close 估值，但每个持仓日必须记录 `valuation_price_age_trading_days`。默认 authoritative 上限暂定 20 个交易日，最终值在 PR #7 配置审阅时冻结。

超过上限、永久停牌、退市、吸收合并、现金选择权等必须按明确 terminal event policy 处理。缺少足够历史事件数据时，相关 split 应诚实 blocked，而不是把持仓无限 ffill 或按零价估值。

### 6.7 Market cache v2

cache key 至少绑定：

```text
raw market artifact hashes
field timing schema hash
instrument state artifact hash
fee schedule hash
price-limit rule hash
lot rule hash
stale valuation policy hash
terminal event policy hash
execution config hash
calendar hash
score artifact hash
code commit sha
```

任何一项变化必须 cache miss。validator 必须检测 stale output、unknown input artifact、config/hash mismatch 和旧 runtime 误用。

### 6.8 修正后的历史 OOS 运行

运行顺序：

```text
frozen PR #6 score
→ field-timing validation
→ PIT instrument state
→ corrected Exchange / Executor
→ normalized accounting
→ execution contract
```

旧 OOS 不覆盖，生成新的、明确标记为 `non_authoritative` 的 evidence version，并提供 old-vs-new 差异归因：

```text
signal_change
fee_schedule
price_limit_semantics
lot_rule
stale_valuation
terminal_event
calendar_or_cache
unknown
```

`unknown` 差异必须阻断 readiness。

### 6.9 Post-observation bug-fix freeze

本次历史 test 已经被观察，不得生成名称暗示 untouched 的 `pre_test_freeze_v2`。每个 split 在修正执行前生成：

```text
bugfix_research_freeze_v1/
  artifact_manifest.json
  freeze_manifest.json
```

强制字段：

```text
freeze_type = post_observation_bugfix
historical_test_already_observed = true
selection_uses_test_outcomes = false
unbiased_final_estimate = false
allowlist_sha256
weights_sha256
score_policy_sha256
score_artifact_sha256
execution_config_sha256
market_cache_sha256
code_commit_sha
freeze_timestamp
```

该 artifact 证明修复规则在重新执行前已固定，并不能恢复历史 test 的“完全未观察”统计资格。即使 `execution_semantics_accuracy_ready=true`，本次结果仍是 post-observation historical bug-fix evidence，不是无偏最终收益估计；真正的无偏最终确认只能依赖未来未见数据或 forward/paper tracking。

### 6.10 PR #7 输出与 Contract

建议新增：

```text
configs/execution_accuracy_correction_v1.yaml
configs/a_share_fee_schedule_v1.yaml
configs/a_share_market_field_timing_v1.yaml
scripts/build_instrument_state_v1.py
scripts/audit_market_field_timing_v1.py
scripts/run_corrected_oos_execution_v1.py
scripts/validate_execution_accuracy_v1.py
outputs/execution_accuracy_correction_v1/current/
```

最低 critical checks：

```text
frozen_score_hash_valid
signal_policy_unchanged_in_execution_pr
date_aware_fee_schedule_applied
future_market_field_count == 0
instrument_state_pit_valid
price_limit_rule_resolved
lot_rule_resolved
no_future_price_execution
no_valuation_bfill
stale_policy_valid
terminal_event_policy_valid
market_cache_v2_ready
cash_non_negative
position_conservation
accounting_conservation
unknown_execution_difference_count == 0
output_hashes_valid
lineage_complete
```

### 6.11 PR #7 Definition of Done

只有以下条件全部满足才能合并：

1. 费率按日期和证券语义正确；
2. 所有执行字段通过 `available_at <= execution_timestamp`；
3. 不再使用同日 `$change` 判断开盘可交易性；
4. PIT instrument state、price-limit 与 lot 规则有来源和测试；
5. 估值无 bfill，陈旧价格和 terminal event 有明确政策；
6. market cache v2 与所有语义输入绑定；
7. 修正历史 OOS 只消费 PR #6 冻结 score；
8. old-vs-new 差异归因中无 unknown；
9. bug-fix freeze 明确为 post-observation；
10. 全量测试、validator、Manifest、freshness 与 CI 通过。

若历史 instrument/tradability/terminal-event 数据不足以满足 authoritative contract，PR #7 可以以“实现完成、readiness honest-blocked”合并，但不得把 `authoritative_oos_execution_ready` 设为 true，PR #5A 继续暂停。

## 7. Readiness 分层

```text
model_research_ready
= selection_holdout_integrity_ready
  && research_formula_accuracy_ready
  && matrix_v4_lifecycle_clean
  && pairwise_ic_ready

authoritative_oos_execution_ready
= model_research_ready
  && execution_semantics_accuracy_ready
  && market_cache_v2_ready
  && future_market_field_count == 0
  && stale_policy_valid

pr5_model_training_ready
= model_research_ready
  && authoritative_oos_execution_ready
```

`core_model_ready` 与 `pr5_model_training_ready` 保持同级保守门禁。研究输入正确但执行证据尚不权威时，可以清楚地表示 `model_research_ready=true`，但本项目当前政策仍禁止启动模型。

## 8. 大规模运行前审阅门禁

每个会触发大规模矩阵、IC、bootstrap、选择链或 OOS 执行的 run 都必须遵守：

```text
代码与配置冻结
→ clean worktree / committed HEAD
→ 输入、lineage、统计语义审阅
→ 单元测试与 mutation/metamorphic tests
→ 小规模 canary
→ 资源/磁盘/断点续跑审阅
→ exact review bundle
→ approval artifact
→ 大规模运行
→ compact validation
```

review bundle 至少绑定 commit、config、input、command、日期范围、因子数、batch、估计磁盘/内存/时长、恢复命令和 canary 证据。任一绑定内容变化都必须重建 bundle。

当前持续对话已有用户 waiver，允许 Codex 在完整自审通过后不等待人工回复，直接执行已提交计划内的大规模计算；该 waiver 只豁免等待，不豁免上述任何技术门禁。出现 warning、unknown difference、hash mismatch、lineage issue、canary failure 或资源不足时必须停止并修复。

## 9. 推荐提交拆分

PR #6：

1. retract inaccurate research/model readiness;
2. fix lifecycle interval generation and add v2 contracts;
3. classify factor dependencies and build Matrix v4 canary;
4. materialize Matrix v4 and Labels v2;
5. implement pairwise IC and bootstrap sensitivity policy;
6. rebuild FDR, stability, clustering, allowlists and weights;
7. freeze score completeness policy and run mutation tests;
8. add lineage, validators, reports and documentation.

PR #7：

1. add field-timing and date-aware fee contracts;
2. build PIT instrument state and board/ST/IPO rules;
3. correct price-limit, lot and execution semantics;
4. implement stale valuation and terminal-event policy;
5. bind market cache v2;
6. generate post-observation bug-fix freeze and corrected OOS;
7. add reconciliation, validators, reports and documentation.

## 10. 立即执行顺序与停止边界

```text
1. 将本计划同步到所有入口文档
2. 创建 PR #6 分支
3. 机器级撤回 readiness 与登记 supersession
4. 完成 Universe v2、依赖分类和 Matrix v4 canary
5. 通过大规模运行前完整自审后物化必要范围
6. 完成 Pairwise IC、bootstrap、选择链和 score policy
7. 合并 PR #6，并在 main 复验
8. 创建 PR #7 分支
9. 完成执行语义修正、cache v2 与小样本对账
10. 通过完整自审后运行修正历史 OOS
11. 合并 PR #7，并在 main 复验
12. 重新审计 readiness
13. 若全部 ready，只更新 PR #5A 计划并停在模型实现前
```

本计划的强制停止边界仍是：实施 PR #5A 模型代码前暂停。PR #6/#7 完成并不授权模型训练。

## 11. 规则来源

- 财政部、税务总局关于减半征收证券交易印花税的公告：<https://www.mof.gov.cn/jrttts/202308/t20230828_3904235.htm>
- 上海证券交易所科创板投资者教育：<https://edu.sse.com.cn/tib/>
- 深圳证券交易所创业板 20% 涨跌幅规则说明：<https://www.szse.cn/www/investor/index/update/t20200729_580056.html>
- 深圳证券交易所风险警示股票历史 5% 规则说明：<https://investor.szse.cn/knowledge/t20210127_584469.html>

规则实现仍须在 PR #7 对固定版本官方规则和 Qlib 源码逐项审计；本节链接只作为计划阶段的权威来源入口。
