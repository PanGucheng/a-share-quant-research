# Selection Holdout Integrity 实施前审计 V1

> ARCHIVED / HISTORICAL：实施前审计已完成。

## 1. 审计结论

本审计在任何 669 因子重跑之前完成。结论是：PR #4 的特征矩阵规模化与 Qlib 执行工程证据可保留，但旧选择结果不具备模型输入资格；必须先完成精确日期、FDR 消费、来源 provenance 与 cache key v3 修复。

当前机器门禁保持：

```text
selection_integrity_status = blocked
model_entry_hard_stop_active = true
core_model_ready = false
pr5_model_training_ready = false
model_training_started = false
```

## 2. 已确认的数据与环境事实

- 当前项目分支：`agent/selection-holdout-integrity-plan-v1`；
- Qlib Python：3.10.19，`pyqlib=0.1.dev6`；
- Qlib 源码 commit：`d5379c520f66a39953bad76234a7019a72796fd0`；
- Qlib 仓库存在一个用户本地修改：`examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158_csi500.yaml`；该文件不在本次因子生成依赖闭包中，不得覆盖或清理；
- TA commit：`a890410710a6e483c9ba08da7f3dd5089e4b9dff`，工作树干净；
- KunQuant commit：`d4b9e61f729df347730aa921b539b9df3c3fe36d`，工作树干净；
- PIT universe intervals：6,248 行；当前矩阵使用 3,983 个唯一 instrument；
- 原始 OHLCVA parquet：5,208,622 行，约 128.5 MB；
- 30 个矩阵分区均为 2,588,000 行，合计约 7.37 GB；
- 当前可用磁盘空间约 423 GB，足以支持受控重跑与一次 cache-hit 复验；
- 三个 outer split 的 train/validation/test 日期数分别为 688/77/120、808/77/124、926/83/124；
- 当前 FDR 确实形成 3 个 669-hypothesis family，但其日期 receipt 和下游消费语义不完整。

## 3. P0 问题

### 3.1 旧选择读取 outer test

旧 stability role 同时读取 test IC、test coverage 与 test degradation；聚类读取完整日期暴露与 IC；代表打分还使用包含 test 的 coverage。修改 test IC 后，`stable_core` 从 65 变为 1，证明旧 16 因子只能标记为 `test_influenced`。

处理：模型入口 hard-stop 已落地；后续选择 API 不允许接收 `test_*` 字段，outer test 只进入冻结后的独立 OOS diagnostics。

### 3.2 Stability 未真实消费上游 FDR

旧 stability runner 声明 FDR artifact 为 parent，却内部重新 bootstrap/FDR。外部与内部的 2,007 个 q-value 全部不同，112 个 BH pass 判断不同。

处理：改为 outer-split FDR gate；stability 只能读取并按 `(outer_split_id, factor)` many-to-one 合并上游 `fdr_results.csv`，同时发布 `input_receipts.csv`。

### 3.3 精确选择日期未成为正式 artifact

旧 purged split Manifest 没有哈希 `date_assignments.csv` 和 `label_intervals.csv`；FDR 消费未追踪的 runtime 日期。Stability 又使用宽松的 split min/max，可能把 purge/embargo 日期重新纳入。

处理：两份精确日期表迁移为根目录受控输出并纳入 Manifest；所有下游使用 exact allowed-dates artifact 和 SHA256，禁止仅用 cutoff。

### 3.4 Raw/provider/source provenance 不完整

旧 matrix hash 只覆盖目录、universe、日期、factor names 和 key schema；外部 raw parquet、provider bins、Qlib/TA/KunQuant 实际源码与 adapter 没有完整进入直接 lineage。

处理：新增 raw market snapshot 与 factor source provenance；matrix cache key 升级到 v3，旧 v2 partition 不得成为 authoritative cache hit。

## 4. P1 问题

1. split leakage audit 缺少 validation-label 对 test 的独立检查；本 PR 已补充该 contract 和反例测试。
2. FDR Manifest 日期范围错误地取完整 daily-IC 输入，而非实际 train 消费日期；修复时必须输出 consumed-date receipt。
3. FDR、stability 直接写 current 目录，失败时可能混合新旧文件；改为 controlled staging/publish。
4. raw cache 命中前没有 artifact/schema/date/symbol/hash验证；cache key v3 必须先验证 snapshot manifest。
5. Alpha101 commit 在 runner 内硬编码；改为由 source provenance 验证并从配置/manifest 解析。
6. clustering performance pair 缺少最小共同日期数 contract；不得把证据不足的 NaN 相似度静默解释为零相关。
7. 当前 Qlib 仓库并非全局 clean；只允许在实际依赖闭包无 dirty file 且闭包文件 hash 完整时通过 provenance。

## 5. 批量运行前强制顺序

```text
修复本审计问题
  → provenance validator
  → cache key v3 单批/最多5因子 canary
  → raw/test mutation tests
  → 资源与恢复审计
  → clean commit 上生成 review bundle
  → 本次会话 user_session_waiver 精确绑定 hashes
  → 30批 authoritative 重跑
  → 30/30 cache-hit 复跑
```

任一环节出现 unknown difference、hash mismatch、lineage 不完整、canary 失败或资源不足，必须停止扩大规模并先修复。会话授权只豁免等待用户回复，不豁免这些技术门禁。

## 6. 大规模运行不变量

- 不覆盖 PR #4 历史证据；
- authoritative runtime 使用新目录或经 v3 key 判定为 miss 后原子替换；
- v2/legacy hash 永远不能升级为 v3 cache hit；
- 每批输出校验 key grid、factor order、row count、output SHA256；
- 失败批次可独立重试，失败后不得发布 pass Manifest；
- 第二次同命令必须 30/30 cache hit；
- 因子值或覆盖率与历史样本出现非浮点级差异时阻塞选择链；
- 在 PR #4.1 完成前不得训练 Ridge、Elastic Net 或 LightGBM。
