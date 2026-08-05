# Prospective Forward Confirmation V1 计划

## 1. 阶段定位

PR #5A—#5D 已完成。PR #5D 在已观察历史 test 上记录：

```text
historical_oos_research_leader = lightgbm
production_model_selected = false
unbiased_final_estimate = false
```

下一阶段只建立严格的 prospective forward 协议、冻结 provisional candidate，并
等待协议冻结后真正到达的新市场数据。它不是生产上线，也不恢复历史 test 的
无偏性。

Historical Instrument State V2 Decision B 继续冻结。本阶段不搜索历史公告、不
物化 authoritative historical execution，也不以任何估值近似绕过 `SZ300280`
能力缺口。

## 2. 现有数据审计与隔离

当前 Matrix v4 / Labels v2 快照：

```text
latest feature date            = 2026-06-09
latest label-mature decision   = 2026-05-11
PR #5D final comparison commit = 2026-07-26
```

仓库中 `2026-02-05—2026-05-11` 的 58 个 label-mature 日期虽然没有进入前三个
outer test，但在 PR #5D 合并前已经存在。因此它们必须标记为：

```text
retrospective_extension_quarantine
prospective_evidence_eligible = false
```

该区间不得用于 forward 性能结论、候选切换、阈值调整或生产选择。只允许在
不读取标签的条件下验证未来特征投影和 prediction schema。

正式 prospective 起点为：

```text
decision_date > candidate_freeze_effective_date_asia_shanghai
AND
raw_snapshot_first_seen_at > candidate_freeze_effective_time_utc
```

两个条件必须同时成立。冻结后下载的旧交易日仍是 retrospective 数据，即使其
`first_seen_at` 较晚也必须拒绝。正式 forward 从候选有效冻结后的首个合法新
交易日开始，旧 Matrix 的 2026-06-09 只保留训练标签窗口隔离边界，不再决定
official forward 起点。

## 3. Provisional candidate

历史比较只选出方法族，不能直接提供一个生产模型。V1 冻结一个 research-only
provisional candidate：

```text
method                     = lightgbm
feature policy             = split_003 frozen 52-factor allowlist/order
structure                  = structure_04
boosting rounds            = 200
learning rate              = 0.03
num leaves                 = 31
max depth                  = 6
min data in leaf           = 100
feature fraction           = 1.0
bagging fraction/frequency = 0.8 / 1
lambda l1/l2               = 0.1 / 0.0
random seed                = 20260725
threads                    = 1
```

选择上述规格的原因仅是它是最新 split 的已冻结 LightGBM 规格，且 LightGBM
方法族在 PR #5D 预注册汇总指标中排名第一。不得再搜索候选、轮数或特征。

## 4. Candidate refit

候选预注册提交后，允许进行一次无搜索 refit：

```text
training decision dates = 2021-02-01—2026-05-11
features                = frozen 52-factor order
target                  = daily_cross_sectional_rank_centered_v2
label                   = label_20d_t1
fit scope               = all label-mature rows before snapshot cutoff
```

2026-05-11 的 label 使用至 2026-06-09 的价格；因此 official forward
decision date 必须晚于 2026-06-09，保证训练标签窗口与 forward 决策不重叠。

refit 前必须依次通过：

1. clean committed protocol HEAD；
2. parent manifest/hash/lineage 审计；
3. exact 52-factor order 与 split_003 hash 校验；
4. 5 因子 × 20 日期 train-only canary；
5. 固定 threads=1 的重复哈希测试；
6. 全量行数、内存、磁盘和预计耗时 review bundle；
7. 标签最大日期与 snapshot cutoff 的非重叠合同。

正式 refit 不读取 `2026-06-09` 后标签或特征，并发布不可变
`forward_candidate_freeze.json`。

## 5. Future data admission

未来数据到达后必须创建新的 append-only raw snapshot、Universe、Matrix、Labels
artifact。不得原地修改 Matrix v4 或 Labels v2。

每个新日期至少记录：

- `decision_date`；
- `raw_snapshot_first_seen_at`；
- `raw_snapshot_id` 与 SHA256；
- `universe_artifact_id`；
- `factor_frame_id`；
- 52 个 frozen factor 的可用性；
- label maturity 状态；
- 是否晚于 candidate freeze；
- 是否通过 20 日 label maturation。

未知 first-seen provenance、回填日期、Matrix v4 原地覆盖或时间边界冲突均
fail-closed。

## 6. Forward 运行政策

候选冻结后：

- 每个新决策日只生成一次 prediction；
- t 日收盘特征完成后才能生成 prediction；
- prediction payload 与 commit receipt 都必须在下一交易日 09:25
  `Asia/Shanghai` 前不可变发布；
- 每份 receipt 必须记录 `decision_date`、`feature_snapshot_created_at`、
  `prediction_created_at`、`prediction_sha256`、`prediction_commit_sha`、
  `prediction_commit_timestamp`、`label_start_date`、`label_start_cutoff`、
  `label_mature_date` 和 `label_read_count_at_prediction=0`；
- 不因表现改变模型、特征、参数、预处理或指标；
- 标签成熟前只记录 prediction receipt，不计算 IC；
- 允许在第 20、40 个成熟日期生成 operational snapshot；
- 至少 60 个 label-mature 交易日后才生成 primary confirmation；
- primary metric 固定为 mean daily Rank IC；
- 同时报告 ICIR、positive-IC ratio、coverage 和 block-bootstrap 区间；
- historical OOS 与 forward 结果严格分表，不拼接重估。

未来评价器只能在 label maturity 后消费已经存在且 hash-valid 的 prediction
payload 与 pre-label-start commit receipt。标签成熟后补生成或覆盖 prediction
必须 fail-closed，不得称为 forward evidence。

冻结通过标准：

```text
minimum prediction coverage              >= 0.95
mean daily Rank IC                       > 0
60-day moving-block 95% CI lower bound   > 0
unknown provenance count                 = 0
candidate/config/hash changes            = 0
```

未通过只记录 `forward_confirmation_failed`，不得自动切换到 Elastic Net、Ridge
或透明基线，也不得重新调参。

## 7. 执行与生产边界

本阶段的官方主证据仍是 prediction quality。Paper portfolio 只有在未来日期具备
同日可验证的 instrument-state/tradability/valuation 数据时才能单独开启；历史
Decision B 不因 forward 数据到达而被追溯修复。

即使 60 日 forward confirmation 通过，也只允许：

```text
forward_prediction_confirmation_complete = true
provisional_candidate_confirmed = true
```

仍保持：

```text
production_model_selected = false
live_trading_ready = false
authoritative_historical_execution_ready = false
unbiased_historical_estimate = false
```

生产选择、paper/live 风控、实时数据许可、监控和运维必须另建治理计划。

## 8. PR 拆分

### PR #20A：Protocol 与 candidate freeze

- 当前数据可用性审计；
- retrospective extension quarantine；
- candidate spec 与 exact hash；
- forward temporal/provenance contract；
- refit canary 与资源门禁；
- 一次无搜索 candidate refit；
- immutable candidate freeze；
- `forward_data_waiting = true`。

### PR #20A.1：Prospective boundary 与 durability hardening

- official date 同时晚于候选有效冻结本地日期；
- raw snapshot first-seen 严格晚于候选冻结时间戳；
- prediction payload 和 commit receipt 均早于 t+1 09:25；
- feature order 只消费 V1.1 protocol artifact；
- V1.1 protocol 与 Labels v2 成为 direct parents；
- Labels runtime 只从 manifest-controlled config 解析并校验 SHA256；
- 模型与预处理进入普通 Git 的内容寻址耐久目录；
- 只重新绑定 freeze，不重训、不搜索、不读取 forward label；
- 完成后继续 `forward_data_waiting=true`。

### PR #20B：Future append pipeline

仅在 freeze 后新数据到达时启动：

- append-only snapshot；
- Universe/Matrix/Labels extension；
- first-seen provenance；
- daily prediction receipt；
- label maturity tracker；
- mutation/lineage tests。

### PR #20C：60-day confirmation

仅在至少 60 个合法、成熟日期后启动：

- 单次 primary evaluation；
- block-bootstrap；
- frozen threshold decision；
- research-only confirmation report。

## 9. 当前立即执行顺序

1. 提交本计划，使 prospective boundary 先成为 clean HEAD；
2. 实现机器可读的 candidate/time/data-availability freeze；
3. 运行零标签读取的 quarantine projection canary；
4. 审阅 canary、资源和 exact refit bundle；
5. 运行一次固定规格 candidate refit；
6. 发布 candidate freeze 并进入 `forward_data_waiting=true`；
7. 完成 PR #20A.1 并重新发布有效候选 freeze；
8. 若没有同时晚于有效冻结日期与时间戳的新数据，必须停止计算并等待，不得把
   任何冻结后下载的历史日期改名为 forward。

## 10. PR #20A 实施回执（2026-07-26）

协议与候选冻结已按计划完成：

```text
forward_protocol_ready               = true
forward_candidate_canary_ready       = true
forward_candidate_refit_complete     = true
forward_candidate_freeze_ready       = true
forward_data_waiting                 = true
forward_prediction_confirmation_complete = false
provisional_candidate_confirmed      = false
production_model_selected            = false
live_trading_ready                   = false
```

时间审计将 2026-02-05—2026-06-09 的 79 个现有日期全部隔离，其中 58 个日期
标签已成熟、21 个日期因 20 日 horizon 尚未成熟；全部
`prospective_evidence_eligible=false`。

小规模 canary 使用 5 因子 × 20 个旧训练日期，随后只投影 20 个隔离日期，
生成 40,000 条 prediction。两次训练的模型和 prediction 哈希完全一致，隔离
日期标签读取数为 0，峰值 RSS 322.0 MiB。

正式 refit 不做任何超参数搜索，严格采用 split_003 的 52 因子顺序和
`structure_04 × 200 rounds`。结果：

```text
training dates      = 1,273
fit rows            = 2,538,428
training end        = 2026-05-11
runtime             = 253.1 seconds
peak RSS            = 1,860.2 MiB
model SHA256        = c89972d27ec610cf7c2598d8ccb1ecd1c227c73d0b5dc51dcf11210b57245ee7
preprocessing SHA256= 679765a462e79a3018db3ab77170a1bc60e3114816aff23b1d8fd38d2a2e37f2
```

本节是 PR #20A 原始回执。其 runtime-only 保存与“晚于 2026-06-09”起点已由
PR #20A.1 加固要求接管；旧 freeze 保留历史证据，不得作为 PR #20B authority。

## 11. PR #20A.1 实施回执（2026-08-02）

审阅意见经代码与 artifact 核验后确认成立，现已完成以下修复：

```text
prospective_time_boundary_hardened          = true
prediction_before_label_contract_ready      = true
forward_lineage_hardened                    = true
forward_candidate_durable_storage_ready     = true
forward_candidate_rebound_without_retraining= true
forward_data_waiting                        = true
forward_prediction_confirmation_complete    = false
production_model_selected                   = false
live_trading_ready                          = false
```

新 authority 为：

```text
outputs/prospective_forward_hardening_v1/current/
```

新候选有效冻结边界：

```text
candidate_freeze_effective_time_utc            = 2026-08-02T14:33:38.772344+00:00
candidate_freeze_effective_date_asia_shanghai  = 2026-08-02
earliest possible official decision date       = 2026-08-03
```

`2026-08-03` 只是日期下界，不自动获得资格；对应 raw snapshot 的
`first_seen_at` 仍必须严格晚于上述精确 UTC 时间戳。冻结后下载的 2026-08-02
及更早行情一律拒绝。

每个未来 prediction 必须形成两层不可变证据：

1. t 日收盘特征完成后的 prediction payload；
2. 下一交易日 09:25 `Asia/Shanghai` 前完成的 commit receipt。

payload 与 receipt 任一超时、label read count 非零、hash 不一致或 commit SHA
缺失，均禁止进入 label-mature evaluation。

lineage 已改为直接消费 `research_model_protocol_v1_1`，旧 V1 feature-order 路径
删除。Labels runtime 只能由 Labels v2 manifest 控制的 `resolved_config.json`
解析，实际 runtime SHA256 冻结为：

```text
4acdfd874c339cd094bf702619861714ec9c75eb27547240eaaa7b945a302ac8
```

模型未重训、未搜索，原始 binary/preprocessing hash 保持不变，并已复制到普通
Git 管理的内容寻址目录：

```text
artifacts/prospective_forward_candidate_v1/sha256/
  c89972d27ec610cf7c2598d8ccb1ecd1c227c73d0b5dc51dcf11210b57245ee7/
```

模型 688,235 bytes、预处理 5,639 bytes，均在读取前执行 SHA256 与 size 复验；
`.gitattributes` 禁止换行转换。旧 runtime 路径只保留本机历史副本，不再是唯一
候选存储。

PR #20A.1 到此完成。PR #20B 继续停止，等待严格晚于新冻结边界的真实新交易
日和 first-seen snapshot。

## 12. Forward prediction 入口密码学合同（2026-08-02）

在首份正式 prediction 生成前，入口合同进一步 fail-closed：

1. `decision_date` 必须存在于调用方从 admitted raw snapshot manifest 解析出的
   权威交易日历；
2. 程序在该日历中定位紧邻的下一交易日，生成 `label_start_date`；
3. 程序固定生成该日 `09:25:00 Asia/Shanghai` 的
   `label_start_cutoff`，receipt 只能复述结果；
4. receipt 中的日期、cutoff 或 canonical calendar SHA256 与推导结果任一不同即
   阻断；
5. `prediction_commit_sha` 必须解析为精确 Git commit；
6. `prediction_repo_path` 必须是安全、规范的仓库相对路径，且 commit tree 中该
   路径必须是普通 file blob；
7. 从 Git blob 原始字节重新计算 SHA256，并与 `prediction_sha256` 完全一致；
8. committer timestamp 只从 Git `%cI` 元数据读取，receipt 记录值必须完全一致，
   且真实时间严格早于程序推导的 cutoff。

上述实现只完成 prediction 入口能力，不生成 prediction、不读取 forward label，
也不改变 2026-08-02 的 candidate freeze。PR #20B 评价继续停止等待新数据。

## 13. PR #20B MVP 实施方案（personal research grade）

### 13.1 定位与边界

本阶段按 `personal_research_grade` 实现，重点防止无意的数据泄漏、模型漂移和
同日预测覆盖；它不是监管合规、机构级资管或实盘授权系统，也不增加外部时间戳、
数字签名、数据库、工作流引擎或多层 readiness artifact。

PR #20B 负责合法单日数据接入、冻结特征投影、每日预测、标签成熟跟踪、逐日
Rank IC/coverage 等 operational metrics 和一个运行状态文件。PR #20C 仍独占至少
60 个成熟日期后的 primary confirmation、block bootstrap 和 research-only 正式报告。
PR #20B 的逐日指标不得提前解释为 primary confirmation。

### 13.2 MVP 主流程

```text
合法新交易日的本地 raw bundle
→ 保存并校验 raw schema、first-seen 与 SHA256
→ 导入 Matrix-v4/factor-registry 既有链生成的当日 52 因子快照
→ 校验 52 个名称、数量、顺序及 date/instrument keys
→ 从 Git 内容寻址目录复验并加载冻结 preprocessing 与 LightGBM
→ 生成 prediction（此阶段 label read count 固定为 0）
→ 原子保存 prediction 与 pending receipt
→ 将 prediction blob 提交 Git 后，反向校验 commit/tree/blob/timestamp
→ 完成 receipt，状态进入 pending_label
→ t+21 成熟后由独立命令读取标签并写逐日指标
→ 更新 outputs/forward/status.json
```

第一版采用明确的本地文件导入模式，不接入新的行情供应商。raw 输入固定为单日
OHLCVA schema；feature 输入必须是仓库既有 Matrix v4、factor registry 与 feature
projection 语义计算出的单日快照。MVP 只负责严格导入、精确投影和模型推理，不复制
Alpha158/Alpha360/TA/Alpha101/basic 的因子实现。未来自动增量数据源属于后续小型
扩展，不是完成本 PR 的前提。

### 13.3 目录与命令

```text
data/forward/raw/                    # 本地输入，不提交
data/forward/features/               # 本地 52 因子快照，不提交
data/forward/labels/                 # 成熟后本地输入，不提交
outputs/forward/predictions/<date>/  # prediction + 简单 receipt
outputs/forward/metrics/             # daily metrics
outputs/forward/status.json          # 唯一累计状态文件
```

```powershell
python scripts/run_forward_prediction_v1.py --date YYYY-MM-DD `
  --calendar-file <calendar.txt> --raw-file <raw.csv> `
  --feature-file <features.csv> --first-seen-at <ISO-8601>

python scripts/run_forward_prediction_v1.py --date YYYY-MM-DD `
  --calendar-file <calendar.txt> --finalize-commit <40-char Git SHA>

python scripts/update_forward_labels_v1.py --as-of-date YYYY-MM-DD `
  --calendar-file <calendar.txt> --label-dir data/forward/labels

python scripts/show_forward_status_v1.py
```

正式 prediction 分两步完成：第一步在 cutoff 前生成不可变 CSV；第二步提交该 CSV
后用真实 Git commit 完成 receipt。程序不信任 receipt 自报时间，而是从交易日历
生成下一交易日 09:25 `Asia/Shanghai` cutoff，并从 commit tree 读取 blob 重算
SHA256、从 Git 元数据读取 committer timestamp。

### 13.4 Dry-run、重复保护与标签成熟

`--dry-run` 可使用历史 fixture 验证 frozen 52-factor → preprocessing → LightGBM
链，但固定 `evidence_eligible=false`，写入独立 `dry_run/`，不增加正式 prediction
计数。`--force-dev` 只允许覆盖 dry-run；正式目录同日存在即 fail closed。

预测命令不接受 label 路径。标签更新命令只扫描已完成 commit receipt 的
`pending_label_dates`；交易日历尚未到 `label_mature_date` 时不打开标签文件。
成熟后仅计算 daily Rank IC、Pearson IC、coverage、valid pair count 和正 IC 标记，
并继续记录 `primary_confirmation_complete=false`。

### 13.5 完成状态与当前停止条件

代码与测试完成时允许：

```text
forward_pipeline_code_ready              = true
single_day_feature_pipeline_ready        = true
single_day_prediction_pipeline_ready     = true
label_maturity_tracker_ready             = true
duplicate_prediction_protection_ready    = true
frozen_model_hash_valid                  = true
frozen_feature_order_valid               = true
prediction_stage_label_read_count        = 0
forward_data_waiting                     = true
official_forward_prediction_count        = 0
primary_confirmation_complete            = false
production_model_selected                = false
live_trading_ready                       = false
```

截至本方案实施日，仓库数据仍止于 2026-06-09，没有满足 2026-08-02 精确冻结边界
的合法新交易日。故只允许运行明确标记的历史 dry-run；不得伪造、回填或提交正式
forward prediction，也不得重训、调参、更换模型、改变 52 因子或根据 forward
表现修改候选。
