# Selection Holdout Integrity 与后续模型计划 V1

## 1. 文档定位

本文是 PR #4 合并后的强制增补计划，优先级高于此前所有“直接进入模型训练”的表述。

适用顺序：

```text
PR #4 已完成的工程规模化证据
        ↓
逻辑 PR #4.1：Selection Holdout Integrity + Provenance
        ↓
PR #5A：透明基线与模型输入协议
        ↓
PR #5B：Ridge / Elastic Net
        ↓
PR #5C：LightGBM
        ↓
PR #5D：统一 OOS 比较与最终结论
```

“逻辑 PR #4.1”表示它属于 PR #4 的统计语义收尾；由于 GitHub PR #4 已合并，它将使用下一张实际 GitHub PR，但不得包含任何模型训练。

## 2. 当前审计结论

PR #4 的以下成果继续有效：

- 669 因子确定性目录；
- 30 个 PIT 特征矩阵分区；
- 2,588,000 个 PIT key grid；
- `label_20d_t1` 与 daily Rank IC 框架；
- purged walk-forward split 基础设施；
- Qlib Exchange、A 股交易约束和会计契约；
- 大型 runtime 隔离、batch resume、输出哈希和 Manifest v2 基础设施。

以下结论撤回，等待 PR #4.1 重新生成：

```text
feature_allowlist_frozen = true
core_model_ready = true
pr5_model_training_ready = true
```

原因不是矩阵或执行链不可用，而是当前选择链存在四类问题：

1. `stable_core` 角色读取 outer test IC、test coverage 和 test degradation；
2. 聚类使用完整时间范围的 factor exposure 和 daily IC；
3. Stability 声明 FDR artifact 为上游，但实际自行重新 bootstrap/FDR；
4. raw market cache 与外部 TA/KunQuant 源码没有完整进入 batch input hash 和直接 lineage。

只读审计还确认：外部 FDR 与 stability 内部 FDR 的 2,007 个 q-value 全部不一致，112 个 BH pass 判断不一致；仅反转 test IC，`stable_core` 从 65 个变为 1 个。当前 16 个代表因此只能保留为历史探索证据。

## 3. 立即目标状态

逻辑 PR #4.1 的第一个业务提交必须先把当前门禁恢复为：

```text
full_research_669_infrastructure_ready = true
full_research_669_matrix_content_ready = true
full_research_669_qlib_execution_operational = true
full_research_authoritative_tradability_ready = false

feature_selection_holdout_clean = false
clustering_holdout_clean = false
fdr_family_semantics_valid = false
fdr_artifact_consumed = false
raw_input_provenance_complete = false
split_allowlists_frozen = false

core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
```

当前输出不删除、不改写旧 manifest。新增状态清单将现有代表标记为：

```text
selection_name = exploratory_global_representatives_v1
selection_status = test_influenced
model_input_allowed = false
superseded_by = split_specific_holdout_clean_allowlists_v1
```

## 4. 逻辑 PR #4.1 范围

### 4.1 唯一目标

建立一条真实无 outer-test 泄漏、真实消费 FDR artifact、输入 provenance 完整、按 outer split 冻结 allowlist 的研究选择链。

### 4.2 允许范围

- readiness 撤回和文档勘误；
- raw/provider/source provenance；
- matrix cache key v3；
- nested selection split；
- 三个独立 FDR family；
- train/validation-only stability；
- date-bounded split-specific clustering；
- split-specific transparent scores；
- 重新执行相同 Qlib Exchange；
- anti-leakage、lineage、freshness、provenance 测试和 validator。

### 4.3 禁止范围

- Ridge、Elastic Net、LightGBM 或任何新模型训练；
- 根据修复后的结果放宽 FDR、IC、稳定性或聚类阈值；
- 追求固定代表数量；
- 把三个 split 的代表强制求交集或并集作为 OOS 模型输入；
- 覆写 PR #4 和 `v0.4-full-research-669` 的历史证据；
- 使用 outer test 指标修正 feature、方向、权重、超参数或交易配置；
- 将 `legacy_provenance_attested` 冒充完整生成 provenance。

## 5. 目标研究结构

每个 outer split 独立执行：

```text
Outer Train
    ├─ 669-factor FDR family
    └─ inner expanding train/validation windows
                       ↓
Outer Validation ─→ train/validation-only stability
                       ↓
              date-bounded clustering
                       ↓
              split-specific allowlist
                       ↓
         transparent weights / model tuning
                       ↓
Outer Test：所有决策冻结后才允许评价
```

最终输出必须是：

```text
split_001 allowlist → split_001 test
split_002 allowlist → split_002 test
split_003 allowlist → split_003 test
```

不存在用于三个历史 test 的单一全局 allowlist。未来若要生成“截至当前日期”的生产候选 allowlist，必须使用独立 as-of 配置和新 artifact，不得回写历史 OOS 评价。

## 6. 工作包 A：Readiness 撤回与历史证据隔离

| ID | 动作 | 输出 | 通过标准 |
| --- | --- | --- | --- |
| A1 | 修改 669 readiness 生成器 | 新 readiness summary | model readiness 全部 false |
| A2 | 增加 exploratory selection registry | `selection_status.csv` | 当前 16 因子 model_input_allowed=false |
| A3 | 修改 validator | blocked 状态仍以 exit 0 验证 | CI 不把诚实 blocked 当失败 |
| A4 | 更新入口文档 | README、DOC_INDEX、context | 不再宣称可直接训练 |
| A5 | 增加模型 loader 拒绝测试 | synthetic rejection test | exploratory artifact 无法进入模型 |

必须保留：

```text
model_training_started = false
```

## 7. 工作包 B：Raw Market 与外部源码 Provenance

### 7.1 Raw market artifact

新增：

```text
configs/raw_market_data_snapshot_v1.yaml
research_validation/input_provenance.py
scripts/audit_raw_market_data_snapshot_v1.py
scripts/validate_raw_market_data_snapshot_v1.py
outputs/raw_market_data_snapshot_v1/full_research_669/
```

至少输出：

```text
artifact_manifest.json
raw_market_data_manifest.json
provider_file_inventory.csv
field_schema.json
contract_status.csv
raw_market_data_report.md
```

必须记录：

- 逻辑 provider URI；
- provider snapshot ID；
- Qlib commit；
- calendar 和 instruments hash；
- 实际参与字段对应 provider 文件的 Merkle/hash inventory；
- raw parquet SHA256；
- row/instrument/date counts；
- 字段顺序、dtype、复权/单位语义；
- PIT universe artifact ID；
- 生成配置和代码状态。

### 7.2 Factor source provenance

新增：

```text
configs/factor_source_provenance_v1.yaml
scripts/audit_factor_source_provenance_v1.py
scripts/validate_factor_source_provenance_v1.py
outputs/factor_source_provenance_v1/current/
```

至少记录：

| 来源 | 必需信息 |
| --- | --- |
| Alpha158/360 | Qlib commit、formula inventory hash、expression adapter hash |
| TA | repo URL、commit、clean status、wrapper/source hashes、license |
| KunQuant Alpha101 | repo URL、commit、clean status、source/metadata hashes、license |
| project_basic | project commit、factor library hash、依赖字段 |

当前审计到的本地 commit 只作为预期值写入计划，不替代 runner 重新验证：

```text
TA       a890410710a6e483c9ba08da7f3dd5089e4b9dff
KunQuant d4b9e61f729df347730aa921b539b9df3c3fe36d
Qlib     d5379c520f66a39953bad76234a7019a72796fd0
```

### 7.3 Matrix cache key v3

每个 batch 的 `input_hash` 必须包含：

```text
factor_catalog_artifact_id
universe_artifact_id
market_data_snapshot_artifact_id
source_provenance_artifact_id
source_specific_tree_hash
adapter_hash
formula_or_metadata_hash
qlib_commit
start/end/warmup dates
factor names
key_schema_version
```

Feature matrix 的直接 manifest parents 改为：

```text
catalog + universe + raw/provider snapshot + factor source provenance
```

Labels 的直接 parents 改为：

```text
matrix + universe + raw/provider snapshot
```

### 7.4 是否重算矩阵

统计泄漏修复本身不要求重算 7.36 GB 矩阵。但旧运行无法事后证明完整 generation provenance，因此采用以下明确政策：

1. `legacy_provenance_attested` 只允许开发和对照，不得打开模型门禁；
2. `raw_input_provenance_complete=true` 必须基于 cache key v3 完成一次 30 批受控重跑；
3. 重跑后必须再次验证 30/30 cache hit；
4. 因子值或覆盖率发生非浮点级差异时停止，不进入选择链；
5. 大型 parquet 继续只保留在 ignored runtime。

## 8. 工作包 C：Nested Selection Split

保留现有三个 outer split，不修改 outer test 日期。

每个 outer split 在其 train+validation development period 内生成 inner expanding windows：

- 只使用 outer train/validation assignments；
- inner train 与 inner validation 标签区间仍执行 purge；
- inner validation 后执行 20 个交易日 embargo；
- 每个 outer split 至少 3 个 eligible inner windows；
- inner split 配置在读取任何新选择结果前冻结；
- 若最早 outer split 无法形成 3 个窗口，阶段 blocked，不降低要求。

新增输出：

```text
outputs/nested_selection_split_v1/full_research_669/
  outer_split_manifest.csv
  inner_split_manifest.csv
  development_date_assignments.csv
  purged_dates.csv
  embargoed_dates.csv
  leakage_audit.csv
  contract_status.csv
  artifact_manifest.json
  nested_selection_split_report.md
```

关键 contract：

```text
inner_train_outer_test_overlap = 0
inner_validation_outer_test_overlap = 0
inner_label_outer_test_overlap = 0
development_date_outside_outer_train_validation = 0
minimum_inner_window_count >= 3 per outer split
same_date_cross_inner_fold = 0
```

## 9. 工作包 D：FDR 真实数据流

采用三个独立 rolling families：

```text
family(split_001) = 669 hypotheses
family(split_002) = 669 hypotheses
family(split_003) = 669 hypotheses
```

FDR 只使用对应 outer train assignments。Outer validation 用于方向、强度和稳定性确认，不进入 raw p-value 计算。Outer test 完全不可访问。

配置必须显式包含：

```text
family_scope: outer_split
expected_family_count: 3
expected_hypotheses_per_family: 669
included_folds: [train]
```

关键 contract：

```text
family_count = 3
unique_factor_count_per_family = 669
duplicate_outer_split_factor_count = 0
unexpected_fold_count = 0
test_date_in_fdr_input_count = 0
```

Stability 不再 import 或调用 bootstrap/FDR 计算。它必须读取上游 `fdr_results.csv`，按 `(outer_split_id, factor)` 进行 `many_to_one` merge。

每个业务阶段新增 `input_receipts.csv`，记录实际消费文件的 artifact ID、SHA256、join keys、输入/消费行数和缺失数量。FDR→Stability 必须满足：

```text
fdr_join_missing = 0
fdr_join_extra = 0
fdr_q_value_mismatch = 0
internally_recomputed_fdr = false
```

## 10. 工作包 E：Train/Validation-Only Stability

选择 API 不得接收任何 `test_*` 字段。只允许：

```text
outer_split_id
inner_split_id
factor
train_mean_ic
validation_mean_ic
train/validation counts
train/validation coverage
upstream FDR pass/q-value
```

`stable_core` 判定改为：

- eligible inner windows 数；
- selection frequency；
- frozen direction agreement；
- `validation_mean_ic × frozen_direction > 0` 的窗口比例；
- validation 相对 train 的退化；
- train/validation coverage；
- 上游 FDR pass。

删除或迁移以下选择字段：

```text
test_mean_ic
test_coverage
direction_adjusted_test_success
test_vs_validation_degradation
median_test_ic
worst_test_ic
```

Outer test 指标只允许由独立的 `run_factor_oos_diagnostics_v1.py` 在 allowlist 已发布后生成。其 manifest 不得出现在 stability、clustering、score 或 model 的 input parents 中。

## 11. 工作包 F：Split-Specific Clustering 与 Allowlist

聚类 runner 必须按 outer split 运行，并强制接收：

```text
outer_split_id
allowed_dates artifact
allowed_dates_sha256
```

`allowed_dates` 必须是 purged development assignments 中 train+validation 的精确集合，不能只依赖宽松 cutoff。

以下两个 API 都必须先过滤 allowed dates：

```text
daily_exposure_similarity(..., allowed_dates=...)
performance_similarity(..., allowed_dates=...)
```

输出：

```text
representatives_by_split.csv
excluded_redundant_factors_by_split.csv
split_allowlist_manifest.csv
selection_date_audit.csv
```

每个 split allowlist 记录：

```text
outer_split_id
development_start/end
outer_test_start/end
allowed_dates_sha256
factor_count
allowlist_sha256
stability_artifact_id
clustering_artifact_id
holdout_clean
```

代表数量由数据决定，不设“必须 16 个”。不足 `minimum_components` 的 split 必须 blocked。

## 12. 工作包 G：Split-Specific Score 与 Qlib Execution

Score runner 不再读取全局 representatives，而是按 outer split 读取对应 allowlist。

规则：

- 方向只来自该 split 的 development evidence；
- `stability_weight` 只读取该 split 的 nested selection/FDR；
- 不使用当前或历史 outer test 指标更新权重；
- factor preprocessing 只使用当日横截面或 train-fitted 参数；
- 每个 split 的 outer test 只在 weights 和 allowlist 冻结后生成 score；
- 三个 split 使用同一 Qlib Exchange 配置和成本语义。

必须重新运行：

```text
split-specific transparent score
Qlib Exchange
execution reconciliation/readiness
```

不要求收益为正；只要求执行、lineage、holdout 和 accounting contract 成立。

## 13. PR #4.1 Anti-Leakage 测试矩阵

### 13.1 合成单元测试

1. selection 输入出现 `test_*` 列立即失败；
2. 修改 outer test IC，stability 与 allowlist hash 不变；
3. 修改 outer test factor exposure，cluster 与 representatives 不变；
4. 修改未来 split 数据，较早 split allowlist 不变；
5. FDR artifact 行缺失、重复或 q-value 被篡改时失败；
6. allowed dates 包含 outer test 日期时失败；
7. exploratory global representatives 被 model loader 拒绝；
8. 每个 split allowlist 只引用自己的 development evidence；
9. model/evaluator 不能在 allowlist 冻结前打开 test；
10. 输入顺序变化不改变 allowlist hash。

### 13.2 真实 compact validator

```text
feature_selection_holdout_clean = true
clustering_holdout_clean = true
fdr_family_semantics_valid = true
fdr_artifact_consumed = true
raw_input_provenance_complete = true
selection_lineage_issue_count = 0
test_date_consumption_count = 0
```

### 13.3 Mutation contract

在不修改正式 runtime 的临时副本上，对 outer test 的 IC 和 factor exposure 注入极端值。允许 OOS diagnostics 改变，但以下哈希必须完全不变：

```text
FDR results
stability board
cluster assignments
representatives_by_split
split allowlist manifest
factor weights
```

## 14. PR #4.1 推荐提交拆分

1. retract false-positive model readiness and document exploratory outputs
2. add raw market and factor-source provenance artifacts
3. upgrade matrix cache keys and regenerate provenance-complete evidence
4. add nested selection split contracts
5. make stability consume split-scoped FDR artifacts
6. make clustering and representatives development-date bounded
7. generate split-specific transparent scores and Qlib execution
8. add anti-leakage mutation tests, readiness, validators, and documentation

不得把 readiness 撤回延迟到最后一个提交。

## 15. PR #4.1 Definition of Done

只有全部满足才可合并：

1. 当前 16 个代表被明确标记为 exploratory/test-influenced；
2. 模型入口拒绝 exploratory artifact；
3. raw/provider/source provenance 完整；
4. cache key v3 实际生效；
5. 30 批 provenance-complete 重跑与 cache-hit 复跑通过；
6. 三个 FDR families 各有 669 个唯一假设；
7. Stability 逐行消费上游 FDR，内部不再重新 FDR；
8. selection/stability 输入不含 test 字段；
9. 三个 outer split 各自产生独立 allowlist；
10. clustering exposure 和 performance dates 都是 allowed development dates；
11. test mutation 不改变任何选择产物；
12. split-specific transparent score 和 Qlib execution 可运行；
13. unknown selection lineage issue = 0；
14. 测试、validator、PR CI 和 main CI 均通过；
15. 模型训练仍未启动。

完成后才允许：

```text
split_allowlists_frozen = true
core_model_ready = true
pr5_model_training_ready = true
model_training_started = false
```

## 16. PR #5A：透明基线与模型输入协议

### 16.1 目标

冻结所有模型共同使用的数据、特征、日期、预处理、prediction schema、Qlib execution 和评价口径，并重跑：

```text
Equal Weight
Stability Weight
```

PR #5A 不训练 Ridge、Elastic Net 或 LightGBM。

### 16.2 共同输入协议

每个 outer split 必须使用：

```text
该 split 的 frozen allowlist
outer train
outer validation
outer test
label_20d_t1
相同 PIT universe
相同 signal lag
相同 Qlib Exchange config
```

模型特征输入 schema：

```text
datetime
instrument
outer_split_id
factor columns from split allowlist only
label_20d_t1
universe_artifact_id
factor_frame_id
split_allowlist_id
```

### 16.3 预处理协议

- 当日横截面 winsorization/z-score 只能使用同日股票；
- scaler、imputer 或任何跨日期统计量只在 outer train fit；
- validation/test 只能 transform；
- 特征列顺序由 allowlist manifest 冻结；
- 缺失处理策略在模型运行前冻结；
- 禁止根据 test coverage 删除特征；
- prediction 统一输出 `datetime/instrument/score/method/outer_split_id/model_artifact_id`。

### 16.4 输出

```text
outputs/model_input_protocol_v1/current/
outputs/model_baseline_comparison_v1/full_research_669/
```

至少包含：

```text
resolved_protocol.json
split_feature_inventory.csv
preprocessing_receipts.csv
prediction_schema.json
baseline_predictions_sample.csv
baseline_execution_summary.csv
contract_status.csv
artifact_manifest.json
```

## 17. PR #5B：Ridge 与 Elastic Net

### 17.1 固定顺序

```text
Ridge
  ↓
Elastic Net
```

Elastic Net 不得先于 Ridge 完成。

### 17.2 Ridge

初始候选仅在 train/validation 搜索：

```text
alpha = [0.01, 0.1, 1.0, 10.0, 100.0]
```

每个 outer split 独立：

1. 在 outer train fit preprocessing 与 Ridge；
2. 用 outer validation 选择 alpha；
3. 冻结参数和 coefficient hash；
4. 打开 outer test 生成一次预测；
5. 使用共同 Qlib Exchange 执行。

### 17.3 Elastic Net

初始候选：

```text
alpha = [0.0001, 0.001, 0.01, 0.1, 1.0]
l1_ratio = [0.1, 0.5, 0.9]
```

必须记录：

- validation search table；
- 最终 alpha/l1_ratio；
- 非零系数数量；
- coefficient sign/stability；
- cluster concentration；
- convergence status；
- fit/predict runtime。

若不收敛，不扩大搜索范围掩盖问题；先审计 scale、缺失和共线性。

## 18. PR #5C：LightGBM

只有 PR #5B 的线性链、prediction schema 和 execution 全部通过后才能开始。

初始受限搜索空间：

```text
num_leaves = [15, 31]
max_depth = [4, 6]
learning_rate = [0.03, 0.05]
min_data_in_leaf = [50, 100]
feature_fraction = [0.8, 1.0]
lambda_l1 = [0.0, 0.1]
lambda_l2 = [0.0, 1.0]
```

规则：

- 只用 train/validation 搜索；
- 使用固定随机种子；
- 限制总候选数和总训练预算；
- early stopping 只观察 validation；
- test 不进入 early stopping、特征重要性选择或二次调参；
- 不因 test 表现添加/删除特征；
- 保存 gain/split importance，但不得用 test 重要性重训同一 OOS 结果。

## 19. PR #5D：统一 OOS 比较

比较方法固定为：

```text
Equal Weight
Stability Weight
Ridge
Elastic Net
LightGBM
```

所有方法必须使用相同：

- 三段 outer test；
- stitched common period；
- PIT universe；
- signal lag；
- Qlib Exchange；
- 费用、整手、T+1、参与率和估值规则；
- 评价代码和 transaction-cost schema。

至少报告：

```text
daily Rank IC / ICIR
prediction coverage
turnover
gross/net return
maximum drawdown
transaction costs
capacity/participation diagnostics
per-split performance
stitched OOS performance
feature/cluster concentration
runtime/resource usage
```

测试集只允许一次最终读取。任何看到 test 后的修改都必须进入新研究版本和新 outer test，不能覆盖本次结果。

模型没有显著优于透明基线不是失败。允许最终结论为：

```text
保留 Equal Weight 或 Stability Weight 作为默认研究方案。
```

## 20. PR #5 系列统一门禁

```text
split_allowlist_mismatch_count = 0
disallowed_feature_count = 0
test_preprocessing_fit_count = 0
test_hyperparameter_reference_count = 0
test_early_stopping_reference_count = 0
test_feature_selection_reference_count = 0
prediction_schema_valid = true
common_period_identical = true
execution_config_identical = true
all_model_manifests_complete = true
unknown_model_lineage_issue_count = 0
```

## 21. PR #5 系列输出结构

```text
outputs/model_comparison_v2/full_research_669/
  protocol/
  equal_weight/
  stability_weight/
  ridge/
  elastic_net/
  lightgbm/
  comparison/
```

每个模型目录至少包含：

```text
artifact_manifest.json
resolved_config.json
split_model_manifest.csv
hyperparameter_search.csv
prediction_artifact.csv
prediction_sample.csv
feature_importance_or_coefficients.csv
execution_summary.csv
contract_status.csv
model_report.md
```

模型二进制、完整 predictions 和大型中间数据保留在 ignored runtime，由 compact artifact 记录路径、大小和 SHA256。

## 22. 最终决策门禁

### PR #4.1 → PR #5A

需要：

```text
feature_selection_holdout_clean = true
clustering_holdout_clean = true
fdr_family_semantics_valid = true
fdr_artifact_consumed = true
raw_input_provenance_complete = true
split_allowlists_frozen = true
core_model_ready = true
pr5_model_training_ready = true
model_training_started = false
```

### PR #5A → PR #5B

需要透明基线、输入协议、prediction schema、common execution 全部通过。

### PR #5B → PR #5C

需要 Ridge 与 Elastic Net 的三个 outer split 全部完成，test leakage audit 为 0。

### PR #5C → PR #5D

需要 LightGBM 三个 outer split 全部完成，搜索预算与 early-stopping audit 通过。

### PR #5D 完成

需要统一 common-period 报告、所有 lineage、成本和执行 contract 通过；最终可以选择透明基线，不强制选择机器学习模型。

## 23. 当前立即执行顺序

1. 创建逻辑 PR #4.1 分支；
2. 第一提交撤回 false-positive readiness；
3. 固化 raw/provider/source provenance；
4. 升级 cache key v3 并完成 provenance-complete 重跑；
5. 构建 nested selection dates；
6. 修复 FDR→Stability 真实消费；
7. 生成 split-specific clustering/allowlists；
8. 重跑透明 score 与 Qlib Exchange；
9. 运行 mutation contracts、全部测试和 validator；
10. 合并 PR #4.1 并在 main 复验；
11. 只有此时才创建 PR #5A。

在第 10 步完成前，不得创建模型训练 artifact 或把 `model_training_started` 改为 true。
