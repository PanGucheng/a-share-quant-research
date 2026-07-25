# Documentation Index

本文件是当前开发文档入口。`docs/` 顶层只保留日常推进需要频繁查看的文档；历史计划、阶段审计和一次性验证记录已归档到 `docs/_archive/`。

## Current Working Documents

- `CI_POLICY.md`
  路径感知 CI 与稳定 `ci-gate` 政策：纯文档只跑快速 diff/link/index/大文件检查，普通研究代码跑完整 pytest/validators，只有 Qlib 执行链、相关依赖或 workflow 变化才安装并运行 Qlib runtime。
- `RESEARCH_MODEL_PROTOCOL_V1_IMPLEMENTATION.md`
  逻辑 PR #5A 实施说明：权威 parent、split-specific 输入、零 test-read canary、统一统计/预处理协议、scope-aware research gate，以及继续关闭的生产和 authoritative execution 边界。
- `RESEARCH_MODEL_PROTOCOL_V1_1_CLOSURE.md`
  逻辑 PR #5A.1 收口：artifact-only 模型入口、Canary/config 强绑定、最终样本内 target 排名、validation transform，以及三个 split 的 development-only full dry-run。
- `RESEARCH_LINEAR_MODELS_V1_IMPLEMENTATION_PLAN.md`
  逻辑 PR #5B 的 Ridge/Elastic Net 精确候选、solver canary、资源预算、分阶段运行、预测试冻结与单次 test release 基线；实施回执同时记录 3/3 + 3/3 模型研究完成，以及 split_002 长期停牌持仓估值导致的 fail-closed Qlib 能力阻断。
- `RESEARCH_LIGHTGBM_V1_IMPLEMENTATION_PLAN.md`
  逻辑 PR #5C 的四结构行、固定 100/200/400/800 checkpoint、16 候选上限、train-only 可复现性 canary、逐级资源门禁和单次 test release 实施及完成回执。
- `RESEARCH_GRADE_MULTIFACTOR_MODEL_V1_PLAN.md`
  当前唯一执行计划。Historical Instrument State Decision B 已冻结，不再继续搜索历史公告；模型阶段按 PR #5A 输入协议、PR #5B Ridge/Elastic Net、PR #5C LightGBM、PR #5D 历史科学比较推进。日期 authority 使用 `date_split_semantics_v1` 与 Selection Lineage Closure，旧 purged manifest 禁止作直接 parent；预处理、solver、环境锁和 LightGBM 固定 checkpoint 已精确冻结。研究模型允许产生 post-observation evidence，但 authoritative execution、无偏最终估计和生产模型选择继续关闭。
- `HISTORICAL_INSTRUMENT_STATE_V2_PLAN.md`
  已完成的 source decision 记录。真实 decision/valuation/terminal scope 已冻结，13 条 Tier 0 官方快照与候选边界对账完成；ST 5/10、全天停牌 3/10、盘前可证明率 38.46%，故正式选择 Decision B。除非用户明确提供新源，否则不再继续该方向。
- `outputs/historical_instrument_state_v2/official_canary/`
  Historical Instrument State V2 的 compact evidence：官方原文 receipt/hash、13 条归一化事件、BaoStock 边界对账、覆盖门槛、Decision B 与 fail-closed readiness。原始网页/PDF 仅保存在忽略的 runtime，不进入 Git。
- `EXECUTION_UNIT_SEMANTICS_CORRECTION_V1_2_PLAN.md`
  已完成的单位语义修正与实施回执。Market Cache v3 已显式执行 volume `factor × 100` 和 amount `×1000`，全量 cache/execution、单票归因、transitive lineage 与治理门禁通过；旧 Market Cache v2 永久 superseded。
- `DATA_SOURCE_AUDIT_V2.md`
  Phase B 数据源决策报告。150 股 Community/BaoStock/AKShare canary 支持 Decision B：核心 raw OHLC 可靠、无需 Matrix v5；AKShare Eastmoney 不稳定，BaoStock ST/tradestatus 的 before-open 权威性未获证明。
- `ACCURACY_CORRECTION_V1_1_AND_DATA_SOURCE_AUDIT_V2_PLAN.md`
  已完成的 lineage/gate closure 与数据源 canary 基线。Phase A 的 22 节点/61 边传递 lineage 为 0 issue；Phase B 形成 Decision B，并将单位错误移交 V1.2。
- `ACCURACY_CORRECTION_V1_PLAN.md`
  已完成的 Accuracy Correction V1 实施基线。PR #6 修复研究计算，PR #7 修复执行语义；其后续 lineage/gate cleanup 以上述 V1.1 计划为准。
- `outputs/accuracy_correction_v1/current/`
  当前机器治理状态：research/score、Data Source Audit V2、Market Cache v3 与 execution unit semantics ready；Market Cache v2 永久 false。authoritative OOS、core model、PR5 training 和 training-started 均 false。
- `outputs/accuracy_correction_v1_1/current/`
  Phase A 机器审计：corrected score lineage complete、业务 payload 不变、unknown board=0、22 节点/61 边传递 lineage 0 issue。
- `outputs/data_source_audit_v2/current/`
  150 股 Community/BaoStock/AKShare 隔离 canary。BaoStock 覆盖 100%、AKShare Eastmoney 覆盖 2%；核心 raw OHLC 可靠，Market Cache v2 的 volume `×100` 与 amount `×1000` 单位修正待 V1.2 实施。
- `outputs/instrument_state_v1/current/`
  PIT instrument-state 与 board/lifecycle 证据；缺失的历史 ST、盘前停牌和 terminal event 源以 capability blocker 公开记录。
- `outputs/market_cache_v2/current/`
  历史 Market Cache v2 证据；字段时点与禁止估值回填通过，但成交量单位漏乘 `×100`，已 superseded，不能再支持 execution readiness。
- `outputs/market_cache_v3/current/`
  单位修正后的当前 Market Cache：三个 split 共 853,936 行，volume/amount 分别以 shares/CNY 物化，future field=0，完整 unit audit 为 0 unknown。
- `outputs/execution_unit_semantics_correction_v1_2/current/`
  冻结研究信号上的 3 split × 2 method 修正执行；730 个会计日关键 contract 全通过，unknown semantic difference=0，仍是 post-observation / non-authoritative evidence。
- `outputs/research_linear_model_execution_v1/current/`
  PR #5B 的非权威 Qlib 辅助执行证据：4/6 场景完成；split_002 的 Ridge/Elastic Net 均因 2025-04-18 `SZ300280` 长期停牌后超过 20 日估值上限而 `blocked_unpriceable_held_position`。Artifact/lineage 完整但状态诚实为 blocked，不得解释为完整历史 NAV。
- `outputs/research_lightgbm_v1/current/`
  PR #5C 的 3/3 单次 historical test release：735,882 行 prediction，Rank IC 为 0.077783/0.143224/0.051802，最低 coverage 0.995305；研究完成但 production、authoritative execution 与 unbiased estimate 均保持 false。
- `outputs/execution_unit_semantics_correction_v1_2/governance/`
  V1.2 fail-closed 收口、旧新 artifact supersession、全市场及 SZ302132 单票归因与中央 readiness 回执。
- `outputs/bugfix_research_freeze_v1/current/`
  三个 split 的 post-observation bug-fix freeze，明确历史 test 已观察且不能形成无偏最终估计。
- `outputs/execution_accuracy_correction_v1/current/`
  已 superseded 的 post-observation corrected historical OOS evidence；因 Market Cache v2 participation volume 缩小 100 倍，等待 V1.2 重发，且始终 non-authoritative。
- `outputs/point_in_time_universe_v2/full_research/`
  PR #6 lifecycle-clean Universe v2：29 个越界 interval 与 329 个非法 key 已修正，最终 lifecycle violation、interval overlap 和 removed-key residual 均为 0。
- `outputs/factor_dependency_v1/current/`
  669 因子依赖清单：605 个逐标的因子仅为 bit-identical 复用候选；Alpha101 与 `unknown` 全部 fail-closed 到强制重算审计。
- `outputs/full_research_feature_matrix_v4_canary/current/`
  Matrix v4 大规模计算前的五来源 Top2000 canary：四个纯时间序列代表在 39,981 个共同 key 上逐位一致；Alpha101 动态 PIT 横截面代表分别有 39,859 与 39,908 个值被纠正；严格轴标签和 unknown fixture 门禁通过。
- `outputs/full_research_feature_matrix_v4/current/`
  生命周期清洁的 669 因子矩阵权威 receipt：30 个分区各 2,587,671 个 Universe v2 key；605 个复用因子零差异，64 个 Alpha101 全量重算并产生 107,066,948 个值级修正；Manifest clean/complete/pass。
- `outputs/full_research_labels_v2/current/`
  精确日历 Labels v2：2,587,671 个生命周期清洁 key，按 canonical trading calendar 连接 t+1/t+21 close，不使用物理行 shift 或价格填充；coverage 0.980970，末端 21 个日期标签全部按预期缺失。
- `outputs/full_research_daily_ic_v2/current/`
  Pairwise Spearman IC v2：669 因子逐日先构造 factor-label 共同非空集合，再分别 rank；scipy、行序、最小 pair 与 lineage 门禁通过。相对 v1 有 621 个因子、598,072 个日因子 IC 值被修正。
- `outputs/bootstrap_gap_sensitivity_v1/current/`
  Outer-train-only bootstrap gap audit：3×669 个假设比较 legacy dropna block 与真实日期连续 segment block；p-value、CI、BH、BY 和受控缺口均越过预冻结阈值，正式政策已冻结为 `gap_aware_moving_block`。
- `outputs/factor_multiple_testing_v2/current/`
  Matrix v4 / Labels v2 / pairwise IC v2 派生的 3×669 corrected outer-train FDR；强制绑定 gap-aware 冻结政策和 clean canary。
- `outputs/factor_rolling_stability_v2/current/`
  只消费 corrected FDR v2 与 inner-development IC 的稳定性结果；不内部重算 FDR，不包含 test 字段或 test 日期。
- `outputs/clustering_input_projection_v2/current/`
  将 Matrix v4 stable-core exposure 与 IC v2 performance 严格投影到哈希绑定的 development allowed dates。
- `outputs/factor_clustering_v2/current/`
  三个 split 的 corrected 聚类与 45/46/52 个代表；所有来源、runtime 投影及日期集合均按哈希验证。
- `outputs/split_specific_allowlist_v2/current/`
  由 corrected clustering 冻结的 45/46/52 split-specific allowlist；各自包含独立 payload 与 feature-order hash，模型入口仍关闭。
- `outputs/split_transparent_weights_v2/current/`
  corrected allowlist 的 Equal Weight / Stability Weight；六组权重分别归一化并冻结哈希，不消费 test 字段。
- `outputs/transparent_score_policy_v1/current/`
  约 532 万 development-only 日期—股票行的组件完整性审计；冻结 5 个且 10% 的共同门槛、拒绝/标记重归一化语义和政策哈希。
- `outputs/selection_mutation_contract_v2/current/`
  corrected selection chain 的 36 个 outer-test mutations 与 Alpha101/lifecycle metamorphic contracts；五类 selection payload hash 全部不变。
- `outputs/split_transparent_score_v2/current/`
  仅按 PR #6 冻结的 Matrix v4、weights、score policy 与 mutation proof 物化的 1,471,764 行 prediction-only score。
- `PR5A_MODEL_INPUT_PROTOCOL_HANDOFF_V1.md`
  延后的模型输入协议参考。只能在 PR #6/#7 全部门禁通过后重新启用，不能直接采用当前已被替代的 allowlist、score 或 OOS execution。
- `SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md`
- `SELECTION_HOLDOUT_IMPLEMENTATION_AUDIT_V1.md`
  PR #4 合并后的 holdout 修复计划与实现审计。其 holdout 隔离结论继续有效，但“直接进入 PR #5A”的结论已由 Accuracy Correction 计划接管。
- `FULL_RESEARCH_669_RUN_V1.md`
  PR #4 的 669 因子工程证据与 PR #4.1 的完成增补；旧 16 因子和当前 48/46/54 split allowlist 均只保留历史证据，后者等待 PR #6 重建。
- `FULL_RESEARCH_FACTOR_TRIAL_V1.md`
  PR #3 的 80 因子真实 PIT 特征矩阵、purged/FDR/稳定性/聚类/score、Qlib 执行、readiness 与复现说明。
- `QLIB_EXCHANGE_INTEGRATION_V1.md`
  PR #2 已实施范围、单位/约束语义、合成精确对账、30 股票真实小样本、readiness 和复现命令。
- `QLIB_EXCHANGE_SEMANTIC_AUDIT_V1.md`
  固定 Qlib commit 的 Exchange、Executor、Signal、成本、成交量、T+1 和输出语义源码审计。
- `REFERENCE_PIPELINE_CONSISTENCY_V1_1_1.md`
  V1.1.1 已实施计划与验收结果；已修复全 holdout 与旧下游混用、stale artifact、未生效 lineage gate 和 readiness 假阳性。
- `FACTOR_VALIDATION_HARDENING_V1_1.md`
  V1.1 已实施计划与历史证据；其 `reference_ready=true` 结论已被 V1.1.1 一致性审计更正。
- `Qlib A股因子研究框架完整升级计划 V1.md`
  新一轮研究框架升级总纲，定义阶段目标、约束、输出和最终完成标准。
- `FACTOR_VALIDATION_ROADMAP_V1.md`
  上述升级总纲的详细执行路线图，包含工作包编号、依赖、预计文件、验证顺序、阶段门禁和失败停止条件。
- `outputs/research_data_contracts_v1/current/schema_report.md`
  阶段 1 DataFrame contract 对现有 factor、tradability、screening 与 judgement 输出的兼容审计。
- `outputs/point_in_time_universe_v1/local_smoke/universe_report.md`
  阶段 2 动态股票池真实 provider smoke、PIT 审计与 Qlib instruments 回读结果。
- `outputs/purged_walk_forward_v1/local_reference/purged_walk_forward_report.md`
  阶段 3 date-level Purged Walk-Forward manifest、泄漏审计与 mlfinpy 非依赖语义参考边界。
- `outputs/factor_multiple_testing_v1/local_reference/multiple_testing_report.md`
  阶段 4 block bootstrap、BH/BY FDR、null simulation 与 test-family 审计。
- `outputs/factor_rolling_stability_v1/local_reference/stability_report.md`
  阶段 5 严格窗口选择历史、冻结方向、OOS degradation 与稳定性角色看板。
- `outputs/factor_clustering_v1/local_reference/clustering_report.md`
  阶段 6 当前 blocked reference 输出；无 eligible factor，活动 representatives 为空。
- `outputs/factor_score_construction_v1/local_reference/score_construction_report.md`
  阶段 7 当前 blocked reference 输出；活动 weights 为空且 score parquet 不存在。
- `outputs/a_share_execution_v1/local_reference/execution_report.md`
  阶段 8 执行会计基础设施；当前因无有效 score 被预期阻断，没有沿用旧执行结果。
- `outputs/external_exposure_data_v1/current/exposure_data_report.md`
  阶段 9 AKShare forward-only 快照、PIT 字段契约和当前外部采集阻塞状态。
- `outputs/pre_model_diagnostics_v1/local_reference/final_portfolio_report.md`
  阶段 10 当前 blocked pre-model diagnostics；legacy baseline 仅独立展示，current methods 不再由旧 score 补齐。
- `outputs/legacy_common_scores_v1/local_reference/legacy_common_scores_report.md`
  Alpha158 与旧 V3.5 candidate pool 在相同 purged test windows 下的共同口径等权 score。
- `outputs/factor_model_comparison_v1/gated/model_comparison_report.md`
  阶段 11 V1.1.1 能力门禁；真实 lineage/freshness/semantic gate 已启用，pipeline/reference ready 均为 false，训练未启动。
- `PROJECT_CONTEXT_SUMMARY.md`
  项目当前状态、最新阶段、关键路径和下一步入口。
- `STEP_5_FACTOR_RESEARCH_AND_MODEL_PLAN.md`
  因子研究与筛选主线总线文档。
- `FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md`
  当前因子研究工具链 readiness、能力边界和下一步约束。
- `LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1_PLAN.md`
  V3.39 liquidity residualized factor evaluation 最小实现计划。

## Baseline And Environment

- `ENVIRONMENT.md`
  本地 Python、Qlib、数据路径和运行环境快照。
- `BASELINE_REPRODUCIBILITY.md`
  Qlib baseline 复现说明，包括 Windows tempfile 和 multiprocessing wrapper。
- `DATA_SOURCE_DECISION.md`
  数据源选择、字段口径和数据使用原则。
- `UNIVERSE_POLICY.md`
  股票池与 universe 口径。
- `TRADABILITY_LABEL_LAYER.md`
  可交易性标签层设计；后续因子评估必须复用该层，不绕过 data_quality/tradability。

## Archive

历史文档入口：

```text
docs/_archive/README.md
```

归档文档不是废弃文档，而是阶段性证据和参考材料。需要追溯某个已完成阶段时，优先从归档 README 的主题目录进入。

## Current Stage

逻辑 PR #4.1 的 outer-test 隔离继续有效；PR #6 已完成研究准确性修正，PR #7 已完成执行语义修正，PR #8 已完成 lineage/gate closure 与 Data Source Audit V2，V1.2 已完成 Market Cache v3 和执行单位修正。

```text
docs/EXECUTION_UNIT_SEMANTICS_CORRECTION_V1_2_PLAN.md
docs/DATA_SOURCE_AUDIT_V2.md
docs/Qlib A股因子研究框架完整升级计划 V1.md
docs/FACTOR_VALIDATION_ROADMAP_V1.md
```

Historical Instrument State V2 已以 Decision B 冻结。当前 corrected 45/46/52
allowlist、weights 与 score 可作为研究输入证据，但必须通过
`research_selection_lineage_closure_v1` 消费。机器状态仍保持
`authoritative_oos_execution_ready=false`、`core_model_ready=false` 和
production hard-stop。

当前阶段正式转入 `RESEARCH_GRADE_MULTIFACTOR_MODEL_V1_PLAN.md`。先实施逻辑
PR #5A 的 scoped model gate、模型输入、validation 指标和 pre-test freeze；
只有 `post_observation_research` 实验可以逐步放行，authoritative execution 与
production model selection 不随模型研究解除。
