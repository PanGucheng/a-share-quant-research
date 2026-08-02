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
