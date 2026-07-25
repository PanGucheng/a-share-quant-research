# 研究级多因子模型 V1 实施计划

> 状态：正式实施基线，尚未启动模型训练  
> 日期：2026-07-25  
> 前置：Research Accuracy Correction、Selection Lineage Closure、Execution Unit Semantics V1.2 与 Historical Instrument State V2 Decision B 已完成  
> 当前入口：逻辑 PR #5A（统一模型输入与实验协议）

## 0. 2026-07-25 审阅修正

本版已落实模型计划审阅提出的六项修正：

1. 日期 authority 改为 `date_split_semantics_v1`，模型日期读取
   Selection Lineage Closure 的 `date_assignments.csv`；
2. 旧 `purged_walk_forward_v1/full_research_669` 只保留 legacy payload，
   禁止成为模型 artifact 的直接 parent；
3. LightGBM 取消 L2 early stopping，候选结构与固定 boosting checkpoint 一起
   按 Rank IC 选择；
4. 线性预处理冻结 daily-equal weighted median/scaler、全空列、近零方差和
   all-NaN row 规则；
5. Ridge `solver=auto` 禁止进入正式运行，环境版本、BLAS 与线程配置进入 freeze；
6. validation-label mutation 只强制指标与 search artifact 改变，不脆弱地要求
   最优候选必然变化。

其中日期 authority 是 PR #5A 发布任何输入 artifact 前的 P0 contract。

## 1. 方向调整与冻结边界

Historical Instrument State V2 已按计划结束：

```text
source_decision = B
historical_instrument_state_v2_ready = false
authoritative_oos_execution_ready = false
terminal_disposition_ready = false
```

Decision B 被正式接受并冻结。除非用户未来明确提供新数据源或新的 Tier-0
结构化接口，否则后续任务禁止：

- 搜索、抓取或核实更多历史公告；
- 扩大 Historical Instrument State canary；
- 物化 Instrument State v2 或 Market Cache v4；
- 重跑所谓 authoritative historical NAV；
- 把 V1.2 的 terminal approximation 改写成权威现金处置。

当前主线改为研究级多因子模型：

```text
PR #5A  统一模型输入、统计协议和防泄漏门禁
   ↓
PR #5B  Ridge → Elastic Net
   ↓
PR #5C  LightGBM
   ↓
PR #5D  透明基线与学习模型的历史 OOS 科学比较
   ↓
未来新时间段 / forward paper confirmation
```

这里的 PR #5A—#5D 是逻辑阶段名；实际 GitHub PR 编号按创建顺序分配。

## 2. 研究资格与执行资格分离

当前研究链已经具备模型研究所需的统计输入：

```text
selection_holdout_integrity_ready = true
universe_lifecycle_v2_ready = true
matrix_v4_lifecycle_clean = true
labels_v2_ready = true
pairwise_ic_ready = true
corrected_outer_fdr_ready = true
corrected_stability_ready = true
corrected_clustering_ready = true
corrected_allowlist_ready = true
selection_mutation_ready = true
model_research_ready = true
```

但历史执行仍不具权威性：

```text
historical_instrument_state_v2_ready = false
authoritative_oos_execution_ready = false
unbiased_final_estimate = false
production_model_selected = false
```

因此必须拆分两套能力：

### 2.1 允许推进

- 基于 Matrix v4 与 Labels v2 的训练、验证和预测；
- mean daily Rank IC、ICIR、coverage 等预测层评价；
- Ridge、Elastic Net、LightGBM 的预注册比较；
- 使用固定 V1.2 execution 语义进行非权威、辅助性的组合敏感度诊断；
- 历史 OOS 的科研比较和可复现实验。

### 2.2 不允许声称

- 历史 NAV 是 authoritative execution evidence；
- 模型 test 表现是从未被人观察过的无偏最终估计；
- 历史 OOS winner 自动成为生产模型；
- 模型已具备实盘、paper trading 或资金部署资格；
- `core_model_ready` 可以替代更细的研究/生产能力字段。

所有模型输出必须带：

```text
experiment_class = post_observation_research
historical_test_already_observed = true
authoritative_execution = false
unbiased_final_estimate = false
production_model_selected = false
```

## 3. 机器门禁重构

现有 `model_entry_hard_stop_active=true` 不能被简单删除或绕过。PR #5A
应把单一 hard-stop 改为 scope-aware gate：

```text
default / unspecified experiment class
    → blocked

authoritative_oos / production / paper / live
    → blocked

post_observation_research
    → 仅在 PR #5A 协议全部通过后允许
```

新增机器状态：

```text
research_model_protocol_ready
research_model_input_ready
research_model_training_ready
research_model_experiment_started
linear_model_research_complete
lightgbm_model_research_complete
historical_oos_model_comparison_complete
research_model_hard_stop_active
production_model_hard_stop_active
```

初始值：

```text
research_model_protocol_ready = false
research_model_input_ready = false
research_model_training_ready = false
research_model_experiment_started = false
linear_model_research_complete = false
lightgbm_model_research_complete = false
historical_oos_model_comparison_complete = false
research_model_hard_stop_active = true
production_model_hard_stop_active = true
production_model_selected = false
```

`core_model_ready`、`pr5_model_training_ready` 语义过宽，本阶段不得直接改为
true。它们保持 false；研究模型入口只读取上述新的 scoped capabilities。

`model_training_started` 不能永久伪装为 false：首次真实模型 fit 成功发布后应诚实
改为 true，同时继续保持 production 与 authoritative execution 门禁为 false。

## 4. 权威模型输入

### 4.1 唯一允许的上游

```text
Universe:
  outputs/point_in_time_universe_v2/full_research/

Feature matrix:
  outputs/full_research_feature_matrix_v4/current/

Labels:
  outputs/full_research_labels_v2/current/

Date split authority:
  outputs/date_split_semantics_v1/current/

Selection authority:
  outputs/research_selection_lineage_closure_v1/current/

Selection and model date assignments:
  outputs/research_selection_lineage_closure_v1/current/date_assignments.csv

Selection mutation proof:
  outputs/research_selection_lineage_closure_v1/current/

Legacy split payload source only:
  outputs/purged_walk_forward_v1/full_research_669/
```

`outputs/purged_walk_forward_v1/full_research_669/artifact_manifest.json`
仍直接绑定 Matrix v1、Labels v1 与 Universe v1。它只能作为
`date_split_semantics_v1` 已登记的 legacy payload evidence，**不得成为任何
PR #5A—#5D artifact 的直接 parent**。

模型 stage 必须同时把以下两个当前 artifact 作为直接 parent：

```text
date_split_semantics_v1
research_selection_lineage_closure_v1
```

并验证：

```text
date_split_semantics_v1/date_assignments.csv SHA
==
research_selection_lineage_closure_v1/date_assignments.csv SHA
```

日期 authority 只声明 `split_manifest_id`；Universe v2、factor catalog 和
factor frame authority 由 Selection Lineage Closure、Matrix v4 与 Labels v2
分别提供。禁止从 date-only artifact 传播 Universe、catalog 或 frame 身份。

不得直接把历史
`outputs/split_specific_allowlist_v2/current/artifact_manifest.json` 当作模型
权威 parent。该历史 manifest 曾携带不一致的 Universe lineage；模型必须消费
`research_selection_lineage_closure_v1` 中已验证且业务 payload 不变的：

```text
split_allowlist_manifest.csv
factor_weights_by_split.csv
business_payload_hashes.csv
mutation_contract_status.csv
date_assignments.csv
```

### 4.2 Split-specific feature sets

冻结输入：

| split | train | validation | test | factor count |
|---|---|---|---|---:|
| split_001 | 2021-02-01—2023-12-04 | 2024-02-01—2024-06-03 | 2024-08-01—2025-01-27 | 45 |
| split_002 | 2021-02-01—2024-06-05 | 2024-08-05—2024-11-28 | 2025-02-05—2025-08-04 | 46 |
| split_003 | 2021-02-01—2024-11-28 | 2025-02-05—2025-06-06 | 2025-08-05—2026-02-04 | 52 |

每个 split 使用独立：

```text
allowlist_sha256
feature_order_sha256
allowed_dates_sha256
```

不存在一个合并后的“全局模型因子列表”。禁止取三个 allowlist 的 union、
intersection 或历史 16 因子替代 split-specific 输入。

## 5. 标签、样本与时间语义

唯一标签：

```text
label_id = label_20d_t1
source = full_research_labels_v2
feature_time = t
label_start = t+1
label_end = t+21
```

所有样本必须来自 exact split date assignments，不得用行号、自然日 cutoff 或
物理 `shift()` 重新推导 train/validation/test。

Fit/evaluation 行规则：

- `(datetime, instrument)` 唯一；
- 特征日期与 Matrix v4 完全一致；
- 标签只从 Labels v2 exact key join；
- fit 时删除 label 缺失行，不填充 label；
- test label 在 pre-test freeze 前禁止读取；
- 每日样本总权重归一为 1，每只股票权重为当日有效样本数的倒数；
- 不用未来日期的 coverage、均值、方差或缺失率决定当前样本。

PR #5A 对 raw return target 和冻结变换后的 target 做**仅限 train 的分布审计**，
但不再把 target 类型作为可选择项。V1 已直接冻结：

```text
training_target_transform = daily_cross_sectional_rank_centered
evaluation_target = raw label_20d_t1
primary evaluation = daily Spearman Rank IC
```

精确定义：

```text
在每个 datetime 内，仅对 label 非空样本：
rank = pandas.rank(method="average", pct=true)
training_target = rank - 0.5
```

单日有效标签数不足 100 时，该日不得进入 fit 或 metric，并记录为
`blocked_insufficient_daily_pairs`。不得根据 validation/test 结果改回 raw target
或更换 rank method。

该变换只改变训练目标的尺度，不改变 Labels v2 artifact，也不重新定义 test
收益。

## 6. 预处理协议

共同输入清洗：

```text
±inf → NaN
feature order exact match
unexpected feature → blocked
missing required feature → blocked
duplicate key → blocked
label leakage column → blocked
```

线性模型：

```text
DailyEqualWeightedMedianImputer
StandardScaler.fit(X_train, sample_weight=train_daily_equal_weights)
Ridge / ElasticNet
```

精确规则：

```text
训练期整列全 NaN
  → blocked

训练期 daily-equal weighted variance <= 1e-12
  → blocked_near_zero_variance

某一行所有 frozen features 均为 NaN
  → 在所有模型中统一排除；保留 missing-prediction row receipt

单个特征部分缺失
  → 用 fit scope 内、按 daily-equal sample weight 计算的确定性 weighted median

validation 缺失值
  → 搜索阶段只能使用 outer-train weighted median

test 缺失值
  → final model 只能使用 outer train+validation 重新 fit 的 weighted median

imputer 输出列数或列顺序变化
  → blocked
```

Weighted median 对排序相同值使用稳定的 canonical key 顺序，并把算法版本写入
`preprocessing_config_sha256`。不得依赖 `SimpleImputer` 对全空列的版本相关
行为，也不得静默删除 frozen feature。

imputer 与 scaler 在超参数搜索阶段只能 fit outer train；选参后在
outer train+validation 重新 fit。Scaler 的 weighted mean/variance 必须消费与
模型 fit 完全相同的 daily-equal weights。所有模型的 all-NaN row 排除规则必须
一致；排除行计入 prediction coverage 分母。

LightGBM：

```text
保留 NaN 由模型原生处理
不做 StandardScaler
使用与线性模型相同的 feature order、target transform 和 daily sample weight
```

所有 fit 对象必须记录：

```text
fit_scope
fit_date_sha256
fit_key_sha256
feature_order_sha256
preprocessing_config_sha256
fitted_preprocessing_sha256
```

## 7. 统一验证与选参协议

在任何模型 validation 结果产生前冻结：

```text
primary_validation_metric = mean_daily_rank_ic
tie_break_1 = daily_rank_ic_ir
tie_break_2 = prediction_coverage
tie_break_3 = lower_model_complexity
final_tie_break = canonical_candidate_sha256
minimum_prediction_coverage = 0.95
final_fit_scope = outer_train_plus_validation
```

禁止：

- Ridge 看 IC、LightGBM 看收益或 Sharpe；
- 参数跑完后改变主指标；
- 用 test 选择超参数、预处理、target transform 或 boosting checkpoint；
- 跨 split 看 test 后统一选择一个“更好”的参数。

每个 outer split 独立搜索并冻结参数。三个 split 可以得到不同最优参数。

## 8. PR #5A：统一输入和实验协议

### 8.1 范围

PR #5A 不训练 Ridge、Elastic Net 或 LightGBM，只建立：

- P0 date authority resolver，拒绝 legacy purged manifest 直接作为 parent；
- scope-aware model entry gate；
- authoritative input resolver；
- split-specific wide matrix projection；
- label exact join；
- feature order receipt；
- target-transform audit/freeze；
- daily-equal weighted preprocessing contract；
- validation metric registry；
- environment/thread/solver freeze schema；
- prediction schema；
- pre-test freeze/release contract；
- canary、mutation、lineage 与 CI。

PR #5A **第一个业务提交**必须同时完成：

```text
date_split_semantics_v1 direct-parent contract
legacy purged manifest direct-parent rejection
date-assignment hash equality contract
scope-aware research/production gate skeleton
weighted preprocessing edge-case policy
environment_lock schema
solver=auto rejection
fixed-checkpoint model-selection policy
validation-mutation hash assertions
```

在该提交通过测试和 CI 前，不得发布任何模型 input artifact。

### 8.2 标准输出

建议模块：

```text
model_research/
  gates.py
  inputs.py
  targets.py
  preprocessing.py
  metrics.py
  freeze.py
  schemas.py
  lineage.py
```

建议配置与脚本：

```text
configs/research_model_protocol_v1.yaml
configs/research_model_protocol_canary_v1.yaml
scripts/audit_research_model_inputs_v1.py
scripts/run_research_model_protocol_canary_v1.py
scripts/freeze_research_model_protocol_v1.py
scripts/validate_research_model_protocol_v1.py
```

输出：

```text
outputs/research_model_protocol_v1/current/
  artifact_manifest.json
  parent_receipts.csv
  split_input_manifest.csv
  feature_order_manifest.csv
  target_transform_manifest.json
  preprocessing_protocol.json
  metric_registry.json
  prediction_schema.json
  mutation_results.csv
  contract_status.csv
  readiness_summary.csv
  protocol_report.md
```

大矩阵 runtime 不提交 Git，只提交 key/hash/schema/统计摘要。

### 8.3 PR #5A canary

先运行：

```text
1 split
5 factors
20 train dates
10 validation dates
0 test reads
```

必须验证：

- canonical feature order；
- exact date/key join；
- imputer/scaler 只 fit canary train；
- label、IC、return 字段不能进入 prediction schema；
- row-order mutation 结果不变；
- feature-order mutation fail-closed；
- validation/test 日期加入 train 时被拒绝；
- test labels/raw features 的访问审计计数为 0；
- parent manifest stale/hash/lineage 异常时非零退出。

## 9. PR #5B：Ridge 与 Elastic Net

### 9.1 固定顺序

```text
Ridge
→ Ridge 三个 split 完成并验证
→ Elastic Net
```

Elastic Net 不得先于 Ridge。

### 9.2 Ridge 候选

预注册 deterministic grid：

```text
alpha = [0.01, 0.1, 1.0, 10.0, 100.0]
fit_intercept = true
solver = <frozen_solver_receipt>
maximum_candidates_per_split = 5
```

`solver=auto` 仅可出现在拒绝测试中，禁止进入正式 candidate manifest。
PR #5B canary 允许比较：

```text
solver_canary_candidates = [lsqr, cholesky]
```

比较只使用固定 train-only 子集，不读取 validation/test，也不使用预测质量：

```text
eligibility = repeated-fit coefficient/prediction hash stable
tie_break_1 = lower_peak_memory
tie_break_2 = lower_wall_time
final_tie_break = canonical_solver_name
```

选定 solver 后生成 `ridge_solver_receipt.json`；solver 变化必须创建新 protocol
version，并使 run approval 与 pre-test freeze 失效。

复杂度 tie-break：优先更大的 `alpha`。

### 9.3 Elastic Net 候选

预注册 deterministic grid：

```text
alpha = [0.001, 0.01, 0.1, 1.0, 10.0]
l1_ratio = [0.1, 0.5, 0.9]
maximum_candidates_per_split = 15
max_iter = frozen_before_run
tol = frozen_before_run
random_seed = 20260725
```

复杂度 tie-break：

```text
更少非零系数
→ 更大的 alpha
→ 更大的 l1_ratio
→ canonical candidate SHA
```

### 9.4 每个 split 的流程

```text
outer train
→ fit preprocessing / candidate model
→ outer validation predictions
→ 唯一 metric registry 选参
→ 冻结 feature list、target、参数、best validation evidence
→ outer train+validation 重新 fit preprocessing 与 final model
→ 生成 pre_test_freeze_manifest
→ release test once
→ prediction-only test artifact
→ 独立评价
```

不得直接把搜索阶段只在 train 上 fit 的对象用于 final test。

### 9.5 线性模型诊断

只用 train/validation 做开发诊断：

- coefficient path；
- 非零系数数；
- coefficient sign/stability；
- condition/collinearity summary；
- feature missingness；
- daily prediction coverage；
- residual distribution。

Test 后的 coefficient/metric 只进入只读 OOS evidence，不反馈选参。

## 10. PR #5C：LightGBM

只有 PR #5B 三个 split 全部完成、prediction schema 和 leakage audit 通过后开始。

PR #5B 的辅助 Qlib 执行不属于 PR #5C 的训练入口。若模型 prediction 已完整、
零提前 test read 和 leakage audit 通过，但某个历史持仓因 Decision B 下缺少
可用估值而 fail-closed，则允许继续 prediction-only LightGBM 研究；禁止把该
授权扩展为完整历史组合比较、authoritative execution 或生产资格。

基础协议：

```text
objective = regression
trainer metric = l2
trainer metric authority = diagnostic_only
official candidate selection metric = mean_daily_rank_ic
early_stopping = false
boosting_round_checkpoints = [100, 200, 400, 800]
boosting_type = gbdt
deterministic = true
force_col_wise = true
seed = 20260725
feature_fraction_seed = 20260725
bagging_seed = 20260725
data_random_seed = 20260725
```

每个 outer split 精确使用：

```text
4 个预注册 structural parameter rows
× 4 个固定 boosting-round checkpoints
= 16 个完整 candidate rows
```

每个 candidate ID 同时绑定 structural parameters 与 `num_boost_round`。候选表
在任何 validation fit 前写入 `hyperparameter_candidate_manifest.csv`。
Structural row 的变化维度限制为：

```text
num_leaves
max_depth
min_data_in_leaf
learning_rate
lambda_l1
lambda_l2
feature_fraction
bagging_fraction
```

禁止大范围随机搜索、Bayesian optimization 或 test-driven grid expansion。
禁止用 LightGBM 内部 L2 early stopping 生成 `best_iteration`。L2 只能作为训练
健康度诊断；不得控制 checkpoint、候选排名或最终轮数。

流程：

1. outer train 对每个 structural row 训练到 800 rounds；
2. 只在 100/200/400/800 checkpoint 生成 outer-validation prediction；
3. 每个 structural-row/checkpoint 形成一个完整候选；
4. 按统一 Rank IC/ICIR/coverage/complexity 规则选择候选及轮数；
5. 冻结 `num_boost_round` 与所有 structural parameters；
6. outer train+validation 按冻结轮数从头重训；
7. 生成并验证 pre-test freeze；
8. test 只预测一次；
9. SHAP/feature importance 在 test release 后仅作解释，不反馈模型选择。

复杂度 tie-break：

```text
更少 num_leaves
→ 更浅 max_depth
→ 更少 boosting rounds
→ canonical candidate SHA
```

## 11. Pre-test Freeze

每个 `(outer_split_id, method)` 在首次读取 test feature/label 前必须生成：

```text
pre_test_freeze_manifest.json
```

至少包含：

```text
outer_split_id
method
experiment_class
allowlist_sha256
feature_order_sha256
training_target_transform_sha256
preprocessing_config_sha256
fitted_preprocessing_artifact_id
selected_hyperparameters
model_config_sha256
model_binary_sha256
training_data_sha256
train_validation_date_sha256
validation_search_sha256
metric_registry_sha256
random_seed
code_commit_sha
freeze_timestamp
python_version
numpy_version
pandas_version
scipy_version
scikit_learn_version
lightgbm_version
qlib_commit_sha
environment_lock_sha256
num_threads
omp_num_threads
mkl_num_threads
openblas_num_threads
numexpr_num_threads
blas_backend
historical_test_already_observed
authoritative_execution
unbiased_final_estimate
```

`environment_lock.json` 必须在 model fit 前生成并纳入所有 model/cache key。
当前环境审计值只能作为 canary 输入；正式值必须由 runner 从实际进程读取，禁止
手写。线程数不得使用 auto。相同 model binary hash 的严格复现声明只在
environment lock、代码、数据、配置和线程设置全部相同时成立。

Test runner：

```text
missing freeze                     → blocked
dirty code                         → blocked
hash mismatch                      → blocked
feature order mismatch             → blocked
test accessed before freeze        → blocked
candidate/metric changed           → blocked
unspecified experiment_class       → blocked
```

每份 freeze 只允许一个 immutable release receipt；失败重跑必须区分基础设施失败
与结果观察后的模型变更。后者不能复用原 freeze 身份。

## 12. 防泄漏 Mutation Contracts

对每个 split 和模型方法至少执行：

```text
修改 outer-test labels
修改 outer-test feature values
修改 outer-test raw OHLCVA
打乱 outer-test row order
注入 outer-test 极端缺失值
添加 outer-test-only instrument
删除 outer-test-only instrument
```

以下 hash 必须不变：

```text
allowlist
feature order
target transform
preprocessing config
fitted preprocessing
selected hyperparameters
validation search
model binary
train/validation predictions
```

Test prediction hash可以因 test feature mutation 变化；开发与冻结 hash 不得变化。

附加测试：

- train mutation 必须改变 fit-data/model hash；
- validation label mutation 必须改变 validation-label hash、validation-metric
  hash 与 validation-search artifact hash；
- 真实数据 mutation 中，最优候选是否改变只作记录，不作为 pass/fail；
- 另建一个候选排名必然翻转的 synthetic fixture，专门验证 selector 会响应
  validation metric 变化；
- feature-order permutation 必须被 schema gate 拒绝；
- test column 名伪装成 feature 必须被 leakage registry 拒绝；
- test label loader 在 freeze 前必须非零退出。

## 13. 统一 Prediction Artifact

所有方法，包括 Equal Weight、Stability Weight、Ridge、Elastic Net、LightGBM，
统一输出：

```text
outer_split_id
datetime
instrument
method
prediction
prediction_artifact_id
allowlist_sha256
feature_order_sha256
model_freeze_id
experiment_class
```

Prediction artifact 禁止包含：

```text
label
future_return
IC
Rank IC
NAV
Sharpe
test selection rank
```

透明基线必须从现有 frozen score 无损适配，不得根据模型结果重新改变权重。

## 14. PR #5D：历史 OOS 科学比较

统一比较：

```text
Equal Weight
Stability Weight
Ridge
Elastic Net
LightGBM
```

### 14.1 主要科研比较

以 prediction quality 为主：

- mean daily Rank IC；
- daily Rank IC IR；
- positive-IC day ratio；
- prediction coverage；
- split 间方向与排名稳定性；
- common-period pooled summary；
- block-bootstrap uncertainty。

不能只报告 pooled 平均，必须保留三个 split。

### 14.2 辅助组合诊断

可使用完全相同的 V1.2 Qlib execution 配置做敏感度分析，但必须：

```text
execution_evidence_class = non_authoritative_historical_diagnostic
historical_instrument_state_v2_ready = false
terminal_approximation_present = true
```

收益、Sharpe、换手和成本只作辅助，不参与超参数选择，也不得覆盖 prediction
quality 的主结论。

应额外给出：

- 排除三只 terminal-focus 股票的敏感度；
- 不生成 synthetic terminal liquidation 的持仓/估值未决情形；
- 无成本与固定成本的方向性比较；
- 结果对非权威 execution 假设的依赖说明。

### 14.3 科研 winner 与生产选择分离

PR #5D 可以记录：

```text
historical_oos_comparison_complete = true
historical_oos_research_leader = <method or none>
```

但必须保持：

```text
production_model_selected = false
unbiased_final_estimate = false
authoritative_oos_execution_ready = false
```

历史 test 已被透明基线、审计和人员观察。Pre-test freeze 能防止本轮代码和模型
搜索读取 test，但不能让已经观察过的历史时期重新变成从未见过的数据。

## 15. 大规模运行门禁

模型搜索开始前必须完成：

1. clean committed HEAD；
2. input/lineage/freshness 全仓审阅；
3. exact split、factor、date、target、candidate grid 冻结；
4. 小规模 canary；
5. leakage mutation；
6. 内存、磁盘、线程和预计耗时预算；
7. resume 与失败分类策略；
8. exact run review bundle；
9. session-waiver 或新的明确授权 artifact；
10. 输出目录与 cache key 冻结。

当前持续对话中过往授予的计算授权可以写入 exact session-waiver，但不豁免上述
技术门禁。任何 code/config/input/command/scope/hash 变化都会使 waiver 失效。

运行顺序：

```text
1 split × 5 factors × 1 candidate
→ 1 split × full allowlist × Ridge grid
→ 3 split Ridge
→ 1 split Elastic Net
→ 3 split Elastic Net
→ 1 split LightGBM × 2 candidates
→ 1 split LightGBM × frozen 16 candidates
→ 3 split LightGBM
```

不得一次启动全部模型、全部 split 和全部候选。

## 16. Artifact 与 Lineage

建议输出：

```text
outputs/research_model_protocol_v1/current/
outputs/research_linear_models_v1/canary/
outputs/research_linear_models_v1/current/
outputs/research_lightgbm_v1/canary/
outputs/research_lightgbm_v1/current/
outputs/research_model_comparison_v1/current/
```

每个 stage 至少包含：

```text
artifact_manifest.json
resolved_config.json
parent_receipts.csv
contract_status.csv
readiness_summary.csv
resource_summary.csv
run_report.md
```

模型 stage 另含：

```text
candidate_manifest.csv
validation_metrics.csv
selected_hyperparameters.json
preprocessing_receipt.json
model_receipt.json
prediction_receipt.csv
pre_test_freeze_manifest.json
test_release_receipt.json
```

大 prediction、model binary、SHAP 明细只存 runtime；Git 只提交 compact receipt、
hash、schema、摘要和复现命令。

## 17. Contracts

PR #5A：

```text
authoritative_selection_closure_consumed
date_split_semantics_authority_consumed
legacy_purged_split_not_direct_parent
date_assignment_payload_hash_equal
matrix_v4_hash_valid
labels_v2_hash_valid
split_dates_exact
split_allowlists_exact
feature_order_exact
target_transform_frozen
metric_registry_frozen
prediction_schema_leakage_free
test_read_count_before_freeze_zero
scope_aware_model_gate_valid
```

PR #5B/#5C：

```text
train_only_search_fit
validation_only_hyperparameter_selection
daily_sample_weight_valid
preprocessing_fit_scope_valid
daily_equal_weighted_imputer_valid
daily_equal_weighted_scaler_valid
all_nan_feature_blocked
near_zero_variance_feature_blocked
all_nan_row_policy_consistent
imputer_feature_order_preserved
solver_auto_forbidden
environment_lock_complete
final_refit_train_plus_validation
pre_test_freeze_valid
single_test_release
prediction_coverage_valid
mutation_invariance_pass
model_binary_hash_valid
output_hashes_valid
```

PR #5D：

```text
common_prediction_schema
common_period_valid
primary_metric_consistent
test_not_used_for_hyperparameters
execution_evidence_marked_non_authoritative
historical_test_observed_disclosed
production_model_not_selected
```

Critical contract 不通过时 runner 非零退出；不得把 capability blocker 转成 warning。

## 18. Definition of Done

### PR #5A

```text
research_model_protocol_ready = true
research_model_input_ready = true
research_model_training_ready = true
research_model_hard_stop_active = false
production_model_hard_stop_active = true
research_model_experiment_started = false
```

### PR #5B

```text
Ridge 3/3 split complete
Elastic Net 3/3 split complete
linear_model_research_complete = true
research_model_experiment_started = true
model_training_started = true
```

辅助执行状态独立记录。若出现 `blocked_unpriceable_held_position`：

```text
linear_model_research_complete = true
linear_model_execution_complete = false
linear_model_execution_operational_ready = false
```

不得通过无限价格回填、未来知情清仓或无证据结算消除阻断。

### PR #5C

```text
LightGBM 3/3 split complete
lightgbm_model_research_complete = true
unknown leakage difference = 0
```

### PR #5D

```text
five-method prediction comparison complete
historical_oos_model_comparison_complete = true
historical_oos_research_leader recorded or explicitly none
production_model_selected = false
authoritative_oos_execution_ready = false
unbiased_final_estimate = false
```

只有五种方法的相同执行链均完成时，才可额外设置：

```text
five_method_historical_portfolio_comparison_complete = true
```

任一方法存在长期停牌后不可估值持仓时，该字段必须为 false，并记录
`blocked_execution_capability`；prediction IC 比较不得被误写为 NAV 比较。

## 19. 当前立即执行顺序

下一次实施从以下顺序开始：

1. PR #5A 第一提交：P0 date authority/legacy-parent rejection、scope-aware
   model gate、weighted preprocessing/environment schema 与新 readiness 字段；
2. 审计 Date Split Semantics、Selection Lineage Closure、Matrix v4、Labels
   v2 和 exact split 输入；
3. 冻结 target transform、metric registry 与 preprocessing protocol；
4. 建立 prediction schema 与 test-access audit；
5. 运行 1 split × 5 factor、零 test read canary；
6. 完成 mutation、lineage、compact validator 与 CI；
7. 物化完整的 PR #5A input receipts；
8. PR #5A 合并和 main 复验；
9. 在启动 Ridge 前生成 exact candidate/run review bundle；
10. 按 PR #5B → #5C → #5D 顺序推进。

在本计划提交前以及 PR #5A protocol readiness 通过前，不启动任何真实模型 fit。
