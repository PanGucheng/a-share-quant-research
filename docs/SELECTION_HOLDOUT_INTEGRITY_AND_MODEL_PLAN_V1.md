# Selection Holdout Integrity 与后续模型计划 V1

## 1. 文档定位

本文是 PR #4 合并后的强制增补计划，优先级高于此前所有“直接进入模型训练”的表述。

适用顺序：

```text
PR #4 已完成的工程规模化证据
        ↓
P0：同一 Draft PR 立即实施机器级模型 hard-stop
        ↓
逻辑 PR #4.1：Selection Holdout Integrity + Provenance
        ↓
PR #5A：透明基线与模型输入协议
        ↓
PR #5B：Ridge / Elastic Net
        ↓
PR #5C：LightGBM
        ↓
PR #5D：历史 OOS 科学比较
        ↓
PR #6：新未来数据 / forward paper confirmation
```

“逻辑 PR #4.1”表示它属于 PR #4 的统计语义收尾；由于 GitHub PR #4 已合并，它使用当前 Draft GitHub PR #5 实施，但不得包含任何模型训练。本文中的 PR #5A—#5D 是后续逻辑模型阶段，不等同于当前 GitHub PR 编号。

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

只读核对确认当前仓库的 `outputs/full_research_669_readiness_v1/current/` 和 `scripts/report_full_research_669_readiness_v1.py` 仍会把模型门禁写为 true。因此不能把撤回动作留给下一张 PR：当前 Draft GitHub PR #5 的第一个实现提交必须在 provenance、选择链和任何批量运行之前先完成机器级 hard-stop。

该提交必须把机器状态恢复为：

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
selection_integrity_status = blocked
model_entry_hard_stop_active = true
bulk_run_user_review_status = not_requested
bulk_run_execution_authorized = false

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

P0 hard-stop 的验收规则：

- 669 readiness runner 必须稳定生成上述 false/blocked 状态；
- readiness validator 对“诚实 blocked”返回 exit 0，表示状态被正确识别；
- Ridge、Elastic Net、LightGBM 及任何通用 model loader 读取 `exploratory_global_representatives_v1` 时必须拒绝并非零退出；
- 仅修改 CSV/Markdown 而不修改状态生成器、validator 和模型入口，不算完成；
- `selection_integrity_status=blocked` 只能由 PR #4.1 的完整 validator 在所有 contract 通过后解除；
- hard-stop 提交通过 CI 前，不得开始后续实现，也不得启动任何大批量任务。

## 4. 逻辑 PR #4.1 范围

### 4.1 唯一目标

建立一条真实无 outer-test 泄漏、真实消费 FDR artifact、输入 provenance 完整、按 outer split 冻结 allowlist 的研究选择链。

### 4.2 允许范围

- readiness 撤回和文档勘误；
- raw/provider/source provenance；
- matrix cache key v3；
- outer-train FDR gate 与 inner-window development robustness dates；
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
    └─ 669-factor FDR eligibility gate
                       ↓
Development period（Outer Train + Validation）
    └─ inner expanding train/validation robustness windows
                       ↓
        train/validation-only stability diagnostics
                       ↓
              date-bounded clustering
                       ↓
              split-specific allowlist
                       ↓
         transparent weights / model tuning
                       ↓
               PRE-TEST FREEZE
                       ↓
Outer Test：所有决策冻结后才允许评价
```

这里的 inner windows 是 development robustness diagnostics，不是每个历史时点独立进行 FDR 的严格 nested pseudo-OOS selection replay。每个 outer split 只有一个使用完整 outer train 的 669-hypothesis FDR eligibility gate；同一个 `(outer_split_id, factor)` q-value 会合并到该 split 的各 inner-window stability diagnostics。完整 outer-train 中晚于早期 inner validation 的数据因此可以影响 eligibility，但不能影响 outer test。本文不把这些 inner windows 宣称为严格逐窗口 OOS 选择。如果未来需要该语义，必须另建“每个 inner train 独立 FDR”的研究版本。

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
| A6 | 增加模型执行 hard-stop | model entry gate | blocked 状态或旧 selection 触发非零退出 |

必须保留：

```text
model_training_started = false
```

工作包 A 属于当前 Draft GitHub PR #5 的 P0 安全修复，不得推迟到后续 PR，也不得与 30 批重跑绑定。

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
5. 大型 parquet 继续只保留在 ignored runtime；
6. 30 批受控重跑属于大批量运行，必须先完成第 13.4 节的用户人工审查和显式放行；没有有效 approval artifact 时 runner 必须拒绝启动。

## 8. 工作包 C：Development Robustness Windows

保留现有三个 outer split，不修改 outer test 日期。

每个 outer split 在其 train+validation development period 内生成 inner expanding windows，但这些窗口的正式语义是“开发期稳健性诊断”，不是严格 nested pseudo-OOS 因子选择回放：

- 只使用 outer train/validation assignments；
- inner train 与 inner validation 标签区间仍执行 purge；
- inner validation 后执行 20 个交易日 embargo；
- 每个 outer split 至少 3 个 eligible inner windows；
- inner split 配置在读取任何新选择结果前冻结；
- 同一个 outer split 的完整 outer-train FDR eligibility 可以用于所有 inner-window diagnostics；
- 不得声称早期 inner validation 对该 FDR gate 保持逐时点不可见；
- 若最早 outer split 无法形成 3 个窗口，阶段 blocked，不降低要求。

新增输出：

```text
outputs/development_robustness_split_v1/full_research_669/
  outer_split_manifest.csv
  inner_split_manifest.csv
  development_date_assignments.csv
  purged_dates.csv
  embargoed_dates.csv
  leakage_audit.csv
  contract_status.csv
  artifact_manifest.json
  development_robustness_split_report.md
```

关键 contract：

```text
inner_train_outer_test_overlap = 0
inner_validation_outer_test_overlap = 0
inner_label_outer_test_overlap = 0
development_date_outside_outer_train_validation = 0
minimum_inner_window_count >= 3 per outer split
same_date_cross_inner_fold = 0
semantic_role = development_robustness_not_nested_selection_replay
```

## 9. 工作包 D：Outer-Split FDR Gate 与真实数据流

采用三个独立 rolling families：

```text
family(split_001) = 669 hypotheses
family(split_002) = 669 hypotheses
family(split_003) = 669 hypotheses
```

FDR 只使用对应 outer train assignments。Outer validation 用于方向、强度和稳定性确认，不进入 raw p-value 计算。Outer test 完全不可访问。

统计解释固定为：

```text
完整 Outer Train → 该 outer split 的统计候选资格
Inner Train/Validation Windows → 候选方向、覆盖和稳定性诊断
Outer Test → allowlist、方向、权重和配置全部冻结后的最终评价
```

因此，`(outer_split_id, factor)` 的一个 FDR q-value 会以 `many_to_one` 方式合并到该 split 的多个 inner windows。该设计在 outer-test 层保持无泄漏，并降低每个 inner window 重新进行 669 因子 FDR 的复杂度；它不提供逐 inner-window 完全 nested 的统计声明。

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
- `stability_weight` 只读取该 split 的 development robustness/FDR；
- 不使用当前或历史 outer test 指标更新权重；
- factor preprocessing 只使用当日横截面或 train-fitted 参数；
- 每个 split 的 outer test 只在 weights、allowlist 和 pre-test freeze manifest 冻结后生成 score；
- 三个 split 使用同一 Qlib Exchange 配置和成本语义。

### 12.1 Pre-Test Freeze

每个 outer split 第一次读取 test labels、test feature values 或 test market data 前，必须生成不可变的 `pre_test_freeze_manifest.json`。透明基线与后续模型共用同一契约，字段至少包括：

```text
outer_split_id
allowlist_sha256
feature_order_sha256
preprocessing_config_sha256
fitted_preprocessing_artifact_id
selected_hyperparameters
validation_selection_metric
model_config_sha256
model_binary_sha256
final_fit_scope
training_data_sha256
validation_search_sha256
qlib_exchange_config_sha256
code_commit_sha
freeze_timestamp
```

透明基线没有模型二进制时，`model_binary_sha256` 必须使用显式的 `not_applicable` 枚举，不能留空。Test runner 的固定行为：

```text
missing pre_test_freeze_manifest       → blocked / non-zero exit
freeze manifest hash mismatch         → blocked / non-zero exit
code/config/input changed after freeze → blocked / non-zero exit
valid immutable freeze manifest        → one test release
```

第一次 test release 另写 `test_release_receipt.json`，记录 freeze artifact ID、test partition IDs、release timestamp 和执行 commit。重复运行只能是同一 frozen inputs 的确定性复现；任何开发决策变化都必须创建新研究版本和新的未来 test，不能覆盖原结果。

必须重新运行：

```text
split-specific transparent score
Qlib Exchange
execution reconciliation/readiness
```

不要求收益为正；只要求执行、lineage、holdout 和 accounting contract 成立。

## 13. PR #4.1 Guardrails、Anti-Leakage 与人工放行

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
10. 缺少或篡改 `pre_test_freeze_manifest.json` 时 test runner 非零退出；
11. 输入顺序变化不改变 allowlist hash。

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

在不修改正式 runtime 的临时副本上，分别执行以下 outer-test-only mutation：

1. 反转或注入极端 IC；
2. 修改 factor exposure；
3. 修改 labels；
4. 修改 raw OHLCVA；
5. 打乱 row order；
6. 注入极端缺失值。

选择 runner 必须读取按 allowed dates 物化、规范排序且 content-addressed 的 development input projection；outer-test 原始分区不得成为任何选择阶段的直接 parent。允许 OOS diagnostics、test partition manifest 和完整 fixture root lineage 改变，但 development input projection hash 以及以下业务 payload hash 必须完全不变：

```text
FDR results
stability board
cluster assignments
representatives_by_split
split allowlist manifest
factor weights
```

对 row-order mutation，规范排序后的输入 content hash 也必须不变。对 labels、OHLCVA 和极端缺失 mutation，若任何 development projection、FDR、stability、cluster、allowlist 或 weights hash 改变，必须视为 P0 泄漏并阻塞阶段。

### 13.4 大批量运行的用户人工审查门禁

后续任何大批量运行都必须在启动前交由用户检查并获得明确放行。Codex、CI、定时任务和 runner 均不得自行批准。满足任一条件即属于大批量运行：

- 100 个及以上因子；
- 超过 5 个 matrix batches；
- 预计运行时间达到 30 分钟；
- 预计读取达到 20 GB 或写入达到 5 GB；
- 30 批 provenance-complete 重跑或全量 669 因子下游计算；
- 每个 split 超过 15 个候选拟合，或跨三个 split 的 LightGBM 搜索；
- 用户另行指定为需要检查的运行。

在请求放行前，只允许执行有预算上限的 canary：最多 5 个因子、1 个 batch、1 个 outer split、6 个月数据；若 canary 自身预计超过上述资源阈值，也必须先审查。

每次请求必须先生成并推送独立 review bundle：

```text
outputs/bulk_run_review_v1/<run_id>/
  bulk_run_review.md
  resolved_config.json
  input_inventory.csv
  factor_and_family_inventory.csv
  split_and_date_inventory.csv
  canary_contract_status.csv
  canary_summary.csv
  resource_estimate.json
  exact_command.txt
  artifact_manifest.json
```

Review bundle 至少披露：

- clean code commit 与 diff scope；
- resolved config、输入 inventory、factor catalog 和 source hashes；
- 日期范围、outer/inner split、FDR family 和 allowed-dates 语义；
- 预期 batch 数、任务数、运行时间、峰值内存、读写量和剩余磁盘；
- canary 输出、mutation/contract 结果和与历史样本的差异；
- exact command、输出目录、resume/cache 行为、失败停止和清理方案；
- 本次运行是否会读取 outer test，以及对应 pre-test freeze 状态。

用户明确同意后才生成本次运行专用的 `user_approval.json`：

```text
bulk_run_user_review_status = approved
bulk_run_approval_id
approved_by
approval_source/reference
approved_commit_sha
approved_resolved_config_sha256
approved_input_inventory_sha256
approved_command_sha256
approved_scope
approval_timestamp
```

Runner 启动时必须逐项复核 approval。代码 commit、配置、输入 inventory、命令、因子数量、日期范围、split/FDR 语义或资源范围任一变化，都将状态改为 `invalidated` 并重新请求用户检查。Approval 只适用于一个 `run_id`，不可跨运行复用；没有用户明确回复时必须停下等待，不得根据历史授权、超时或“继续推进”指令自动放行。

状态机固定为 `not_requested → pending_review → approved → running → consumed`，任一哈希或 scope 变化可从未完成状态转为 `invalidated`。只有用户能执行 `pending_review → approved`；runner 只能验证、进入 `running` 并在结束后写为 `consumed`，已 consumed 的 approval 不可再次使用。

## 14. PR #4.1 推荐提交拆分

1. add machine-level hard-stop, retract false-positive readiness, and reject exploratory model inputs
2. add raw market and factor-source provenance artifacts
3. upgrade matrix cache keys and publish the bulk-run review bundle
4. after explicit user approval, regenerate provenance-complete evidence
5. add development robustness window contracts
6. make stability consume split-scoped FDR artifacts
7. make clustering and representatives development-date bounded
8. add mutation tests and pre-test freeze contracts
9. generate split-specific transparent scores and Qlib execution after freeze
10. finalize readiness, validators, and documentation

不得把 readiness 撤回延迟到最后一个提交。第 3 步完成后必须停下，把 review bundle 交给用户；没有第 4 步的明确批准不得启动 30 批重跑。

## 15. PR #4.1 Definition of Done

只有全部满足才可合并：

1. 当前 16 个代表被明确标记为 exploratory/test-influenced；
2. 机器 readiness 已 false/blocked，模型入口拒绝 exploratory artifact；
3. raw/provider/source provenance 完整；
4. cache key v3 实际生效；
5. 用户审查的 review bundle、有效 approval ID、30 批 provenance-complete 重跑与 cache-hit 复跑全部通过；
6. 三个 FDR families 各有 669 个唯一假设；
7. Stability 逐行消费上游 FDR，内部不再重新 FDR；
8. selection/stability 输入不含 test 字段；
9. 三个 outer split 各自产生独立 allowlist；
10. clustering exposure 和 performance dates 都是 allowed development dates；
11. test IC、exposure、labels、OHLCVA、row order 和极端缺失 mutation 不改变任何选择产物；
12. 每个 outer split 都在读取 test 前生成有效 pre-test freeze manifest；
13. split-specific transparent score 和 Qlib execution 可运行；
14. unknown selection lineage issue = 0；
15. 测试、validator、PR CI 和 main CI 均通过；
16. 模型训练仍未启动。

完成后才允许：

```text
split_allowlists_frozen = true
selection_integrity_status = ready
model_entry_hard_stop_active = false
bulk_run_user_review_status = consumed
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
- 超参数搜索阶段，scaler、imputer 或任何跨日期统计量只在 outer train fit，validation 只能 transform；
- 超参数选定后，`final_fit_scope=outer_train_plus_validation`：在完整 development period 上重新 fit preprocessing，并从头重新 fit final model；
- outer test 只能使用已冻结的 final preprocessing/model 做 transform/predict，不能参与任何 fit；
- 特征列顺序由 allowlist manifest 冻结；
- 缺失处理策略在模型运行前冻结；
- 禁止根据 test coverage 删除特征；
- prediction 统一输出 `datetime/instrument/score/method/outer_split_id/model_artifact_id`。

### 16.4 Validation 选择协议

PR #5A 必须在任何模型搜索前冻结所有方法共同使用的候选比较规则：

```text
primary_validation_metric = mean_daily_rank_ic
metric_aggregation = equal_weight_by_valid_date
tie_break_1 = higher_rank_ic_ir
tie_break_2 = higher_prediction_coverage
tie_break_3 = lower_model_complexity
tie_break_4 = ascending_config_sha256
minimum_prediction_coverage = 0.95
random_seed = 20260721
```

`mean_daily_rank_ic` 使用 validation 中每日 eligible prediction-label pairs 的 Spearman IC，再对有效日期等权平均。训练 objective/loss、收益、Sharpe、单个最佳月份或 test 表现只能作为诊断，不能替代 primary metric。候选先满足 coverage 和 contract eligibility，再按上述唯一顺序排序；不得为不同模型事后选择不同主指标。

搜索预算固定为：

| 模型 | search_method | maximum_candidates_per_split | complexity tie-break |
| --- | --- | ---: | --- |
| Ridge | deterministic full grid | 5 | 更大的 alpha |
| Elastic Net | deterministic full grid | 15 | 更少非零系数，其次更大的 alpha |
| LightGBM | pre-registered balanced candidate table | 16 | 更少 leaves、更浅 depth、更少 boosting rounds |

LightGBM 的 16 行精确候选必须在读取 validation metrics 前写入 `hyperparameter_candidate_manifest.csv`，由固定 seed 和 canonical parameter serialization 冻结。修改候选、指标、tie-break、coverage 阈值或 seed 都会创建新 protocol version，并使已有 bulk-run approval 与 pre-test freeze 失效。

### 16.5 输出

```text
outputs/model_input_protocol_v1/current/
outputs/model_baseline_comparison_v1/full_research_669/
```

至少包含：

```text
resolved_protocol.json
split_feature_inventory.csv
preprocessing_receipts.csv
validation_selection_protocol.json
hyperparameter_candidate_manifest.csv
prediction_schema.json
pre_test_freeze_manifest.json
test_release_receipt.json
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
2. 用 outer validation 和 PR #5A 的唯一指标/tie-break 选择 alpha；
3. 冻结 feature list、alpha 和 final training protocol；
4. 在 outer train+validation 重新 fit preprocessing 和 Ridge；
5. 冻结 final coefficient、model binary、training data 和 validation search hashes；
6. 生成并验证 `pre_test_freeze_manifest.json`；
7. 打开 outer test 生成一次预测；
8. 使用共同 Qlib Exchange 执行。

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

Elastic Net 使用与 Ridge 相同的 `final_fit_scope=outer_train_plus_validation` 和 pre-test freeze 流程。Validation 选择后必须从头重拟合，不能直接把只在 outer train 上拟合的搜索模型当作 final test model。

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
- `search_method=pre_registered_balanced_candidate_table`；
- `maximum_candidates_per_split=16`，`random_seed=20260721`；
- `max_boost_rounds=1000`，`early_stopping_rounds=50`；
- candidate ranking 与最佳 boosting round 只观察 validation `mean_daily_rank_ic`；
- test 不进入 early stopping、特征重要性选择或二次调参；
- 不因 test 表现添加/删除特征；
- 选定参数和最佳 boosting rounds 后，在 outer train+validation 从头重训 final model；
- final preprocessing、model binary、rounds、training data 和 validation search 全部进入 pre-test freeze；
- 保存 gain/split importance，但不得用 test 重要性重训同一 OOS 结果。

LightGBM 搜索属于第 13.4 节定义的大批量运行。必须先提交 16 行 candidate manifest、资源预算和 canary 结果给用户检查，取得针对每个 run ID 的明确 approval 后才能启动。

## 19. PR #5D：历史 OOS 科学比较

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

PR #5D 可以比较并记录历史 OOS leader，但该 leader 是在同一组历史 test 上比较后得到的。它支持科研结论，不再是被选中策略的无偏未来性能估计。必须分开记录：

```text
historical_oos_comparison_complete = true
historical_oos_leader_recorded = true
production_model_selected = false
forward_confirmation_complete = false
```

模型没有显著优于透明基线不是失败，允许科研结论为“Equal Weight 或 Stability Weight 在本组历史 OOS 中更优”。但不得把 `historical_oos_leader` 写成 `production_model`、`unbiased_expected_future_winner` 或已确认实盘策略。

### 19.1 PR #6：新未来数据 / Forward Paper Confirmation

PR #5D 后另建独立 PR #6。其目标是对一个 provisional forward candidate 使用 PR #5D 完成后才出现、此前完全不可见的新时间段进行确认；仍只做研究或 paper execution，不接入实盘。

规则：

- forward 起始日严格晚于 PR #5D 的最大 test 日期和最终比较 commit；
- 候选方法、allowlist 生成规则、超参数、预处理、Qlib Exchange 和成本配置在 forward 数据可用前预注册；
- 推荐最少覆盖 120 个交易日且不少于 6 个自然月；未达到时只能报告 interim，不得完成确认；
- forward 期间不得因表现切换候选、调参或改变评价指标；
- 任何策略变更都创建新 candidate/version，并从新的未来起点重新累计；
- 历史 OOS 与 forward 结果分别报告，不能拼接后重新宣称历史 test 仍是未见数据。

PR #6 完成后可以设置：

```text
forward_confirmation_complete = true
production_model_selected = false
```

是否选择生产模型仍需单独治理决策；数据授权、实时数据质量、paper/live 风控和运维不在当前研究计划范围内，因此不能由 PR #5D 或单一历史 winner 自动打开。

## 20. PR #5 系列统一门禁

```text
split_allowlist_mismatch_count = 0
disallowed_feature_count = 0
test_preprocessing_fit_count = 0
test_hyperparameter_reference_count = 0
test_early_stopping_reference_count = 0
test_feature_selection_reference_count = 0
pre_test_freeze_missing_count = 0
pre_test_freeze_hash_mismatch_count = 0
test_release_before_freeze_count = 0
final_fit_scope_mismatch_count = 0
validation_metric_protocol_mismatch_count = 0
bulk_run_without_user_approval_count = 0
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
validation_selection_protocol.json
pre_test_freeze_manifest.json
test_release_receipt.json
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
valid_bulk_run_user_approval = true
pre_test_freeze_contract_ready = true
core_model_ready = true
pr5_model_training_ready = true
model_training_started = false
```

### PR #5A → PR #5B

需要透明基线、输入协议、prediction schema、validation selection metric/tie-break、final fit scope、pre-test freeze 和 common execution 全部通过。

### PR #5B → PR #5C

需要 Ridge 与 Elastic Net 的三个 outer split 全部完成，test leakage audit 为 0。

### PR #5C → PR #5D

需要 LightGBM 三个 outer split 全部完成，搜索预算与 early-stopping audit 通过。

### PR #5D 完成

需要统一 common-period 报告、所有 lineage、成本和执行 contract 通过，并保持：

```text
historical_oos_comparison_complete = true
production_model_selected = false
```

### PR #5D → PR #6

需要预注册一个 provisional forward candidate 和未来窗口协议。历史 OOS leader 可以成为候选，但不能因此声称生产模型已被无偏确认。

## 23. 当前立即执行顺序

1. 在当前 Draft GitHub PR #5 中立即实施机器级 readiness/model-entry hard-stop；
2. hard-stop 测试与 CI 通过后，固化 raw/provider/source provenance；
3. 升级 cache key v3，但不启动 30 批重跑；
4. 运行受限 canary、资源估算和 preflight contracts；
5. 生成并推送 bulk-run review bundle；
6. **停止执行，把 review bundle 交给用户检查并等待明确批准；**
7. 只有 approval artifact 与 commit/config/input/command 全部匹配后，才运行 30 批 provenance-complete 重跑和 cache-hit 复跑；
8. 构建 development robustness dates；
9. 生成 outer-split FDR gate，并修复 FDR→Stability 真实消费；
10. 生成 split-specific date-bounded clustering/allowlists；
11. 执行扩展 mutation contracts；
12. 生成 split-specific transparent baseline 和 pre-test freeze manifests；
13. pre-test freeze 通过后才执行 Qlib outer-test evaluation；
14. 运行全部测试、validator 和 CI，合并逻辑 PR #4.1 并在 main 复验；
15. 只有此时才创建 PR #5A；后续任何达到第 13.4 节阈值的模型搜索仍需单独提交 review bundle 并等待用户批准。

第 6 步是强制人工暂停点，不得自动越过。在第 14 步完成前，不得创建模型训练 artifact 或把 `model_training_started` 改为 true。
