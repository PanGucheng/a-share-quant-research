# Project Context Summary

本文件用于在对话很长时快速恢复上下文。

## Project

路径：

```text
E:\qlib_prj\qlib_baseline
```

目标：

- 面向量化新手，基于 Qlib 和开源项目整合 A 股量化研究框架。
- 当前重点是因子研究、因子筛选、数据质量和可交易性约束。
- 不急于训练新模型，不做实盘，不替换 Qlib baseline。

## Environment

Python：

```text
E:\anaconda_envs\qlib_env\python.exe
```

Qlib 源码：

```text
E:\qlib_prj\qlib_clone
```

默认数据：

```text
E:/qlib_prj/qlib_data/cn_data_community_20260609_derived
```

重要运行经验：

- 完整 qrun 或长任务应直接用本地普通权限运行，不要在受限沙盒里跑。
- Windows multiprocessing 需要 `freeze_support()`。
- 临时参考仓库放在 `tmp/reference_repos/`，该目录被 `.gitignore` 忽略。

## Current Factor Research Status

V2 / V3 早期：

- 已实现因子注册、IC/Rank IC、分组收益、换手率、覆盖率、相关性、候选筛选。
- 已实现预处理、中性化、切片诊断和暴露相关性。
- 早期结论是 `amplitude_20` 更像风险/流动性暴露，`std_20` 与其高度冗余，`rev_5` 还不足以直接 promote。

Alpha158 reference pipeline：

```text
outputs/factor_catalog_alpha158_v1/alpha158_catalog_full158_runnable.yaml
outputs/factor_candidate_pool_alpha158_v1/full158/alpha158_alpha_candidates.csv
```

- Alpha158 已作为验证研究机器的参照链路，不再作为唯一细挖对象。
- 155 个 Alpha158 因子进入 runnable catalog，14 个进入当前默认 `alpha_candidate`。

Open-source factor sources：

```text
outputs/ta_factor_adapter_v1/smoke/ta_factor_catalog_promoted77.yaml
outputs/alpha101_factor_adapter_v1/batch82/alpha101_factor_catalog_promoted64.yaml
outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml
```

- TA 已有 77 个 promoted runnable 因子、2 个 holdout。
- KunQuant Alpha101 已有 64 个 promoted runnable 因子、18 个 holdout。
- Qlib Alpha360 已有 358 个 promoted runnable 因子、2 个 adapter holdout。

Multi-source toolchain：

```text
outputs/multi_source_screening_v1/current/multi_source_screening_input.csv
outputs/multi_source_judgement_v1/current/multi_source_judgement_board.csv
outputs/new_source_probe_diagnostics_v1/current/new_source_probe_diagnostic_board.csv
outputs/new_source_probe_review_v1/current/probe_review_board.csv
outputs/alpha360_strict_oos_extension_v1/current/strict_oos_contract_status.csv
outputs/alpha360_strict_oos_stability_v1/current/strict_oos_stability_contract_status.csv
outputs/tradability_exposure_attribution_v1/current/tradability_exposure_contract_status.csv
outputs/exposure_data_capability_audit_v1/current/exposure_data_capability_contract_status.csv
outputs/factor_research_toolchain_readiness_v1/current/toolchain_readiness_report.md
outputs/liquidity_residualized_factor_evaluation_v1/current/liquidity_residualized_contract_status.csv
```

- 旧版多来源 factor toolchain readiness 为 `ready`；这只表示 adapter、V4、screening/judgement 等工具链可运行，不代表 V1.1 的 full-research 或 model readiness 已通过。
- total runnable factors: 669。
- new-source runnable factors: 499。
- multi-source screening rows: 679。
- multi-source judgement research candidates: 342。
- new-source alpha probes: 328（TA 15，Alpha101 14，Alpha360 299）。
- new-source probe diagnostics: 328 probes、120 个 frame diagnostics、50 个 portfolio smoke probes、4 次实际调仓，contract pass。
- new-source probe review: 4 个冗余组、19 个 tradability exposure watchlist、3 个严格 OOS extension candidates（`alpha360_HIGH36`、`alpha360_HIGH37`、`alpha360_HIGH40`），contract pass。
- Alpha360 strict OOS extension: 3 个严格候选 recent-OOS frame 286,944 行，min coverage 0.996236，V4 metric index 54 行，contract pass。
- Alpha360 strict OOS stability: main vs recent metric pairs 54 行，recent Alphalens mean IC min 0.063736，recent Qlib IR min 5.025121，signal sign flips 0，contract pass。
- Tradability exposure attribution: 19 个 watchlist 全部归因，主代理均为 `liquidity_value`；14 个建议 holdout/residualization first，4 个 manual review，1 个 residualization candidate review。
- Exposure data capability audit: FactorTest/qlib_factor_platform 参考能力存在；项目 context/tradability/data_quality 可用；当前 provider 缺市值、行业和 Barra 字段。
- `new_source_alpha_probe` 是研究队列，不是默认模型或组合输入。

## Open Source References

已拉取参考：

```text
tmp/reference_repos/jqfactor_analyzer
tmp/reference_repos/FactorTest
tmp/reference_repos/multi-factor
tmp/reference_repos/AlphaTrading
tmp/reference_repos/alphalens-reloaded
tmp/reference_repos/qlib_factor_platform
tmp/reference_repos/GetAstockFactors
tmp/reference_repos/ChinaAShareEquityCharacteristics
tmp/reference_repos/techfactor
```

参考规则：

- 优先借鉴成熟口径和模块边界。
- 不复制无 license 项目代码。
- 不引入复杂 UI。
- 不绕过现有 data_quality/tradability。

## Next Work

> **2026-07-23 PR #6 首个业务门禁已实施：**`outputs/accuracy_correction_v1/current/` 已成为当前权威治理状态。`selection_holdout_integrity_ready=true`，但 research/execution/model readiness 全部为 false，`model_entry_hard_stop_active=true`；旧 48/46/54 allowlist、weights、scores 已登记为 superseded，历史 execution/NAV 为 non-authoritative。通用 model entry gate 会优先读取该状态，旧 PR4.1 ready receipt 即使被显式传入也不能启动训练。136 tests、历史 receipt validators 与新增 hard-stop validator 已通过。下一步才是 Universe lifecycle v2，不得提前运行 Matrix v4、IC 或历史 OOS。

> **2026-07-23 Accuracy Correction 接管当前主线：**逻辑 PR #4.1 的 holdout 隔离仍有效，但实现复核确认研究和执行准确性不足：Daily IC 的 label rank 未限制在 factor-label pairwise-valid 集合；PIT membership 有 29 个越界 interval 和 329 个非法 key，18 个 Alpha101 因子在这些 key 上有 5,922 个非空值，且横截面 rank/scale 可能污染同日其他合法股票；开盘执行读取几乎等同当日收盘收益的 `$change`；2024-08 之后仍按 0.001 印花税；split 1/2 存在最长 110/76 个交易日的陈旧持仓估值；market cache 未绑定字段时点和执行规则；score 非空率掩盖最小组件数仅 5/48、6/46、6/54。当前 48/46/54 allowlist 与透明 score 为 `superseded`，OOS NAV 为 `non_authoritative`。机器目标状态为 `selection_holdout_integrity_ready=true`，但 `research_formula_accuracy_ready=false`、`model_research_ready=false`、`execution_semantics_accuracy_ready=false`、`authoritative_oos_execution_ready=false`、`core_model_ready=false`、`pr5_model_training_ready=false`、`model_training_started=false`。下一步严格按 `ACCURACY_CORRECTION_V1_PLAN.md`：GitHub PR #6 修复 lifecycle、因子依赖分类/Matrix v4、Labels v2、pairwise IC、bootstrap、选择链和 score completeness；PR #7 只修复费率、字段时点、PIT instrument state、涨跌停/lot、陈旧估值、terminal event、cache v2 和历史执行。PR #5A 继续暂停。

> **2026-07-22 逻辑 PR #4.1 本地实施完成：**raw/provider/source provenance 与 cache key v3 已进入 30 批矩阵 lineage；labels、daily IC 和精确 purged split 已刷新；三个 outer-train FDR family 各 669 个假设；holdout-clean stability 的 stable-core 数分别为 461/238/215；按精确 development dates 聚类后生成 48/46/54 个 split-specific allowlist。36 组 test IC/exposure/labels/OHLCVA/row-order/extreme-missing mutation 均不改变 development projection、FDR、stability、clustering、allowlist 或 weights hash。3 份 immutable pre-test freeze 在 test read 前生成，3 份 release receipt 已 consumed；Equal Weight/Stability Weight 共 1,472,000 行 score，3 split × 2 method Qlib execution 的 730 个会计日全部通过 critical contract。当前 `selection_integrity_status=ready`、`core_model_ready=true`、`pr5_model_training_ready=true`、`model_training_started=false`；旧 16 因子仍禁止，权威历史 tradability、历史 OOS 完成与生产模型选择仍为 false。下一步只按 `PR5A_MODEL_INPUT_PROTOCOL_HANDOFF_V1.md` 准备 PR #5A，本轮在任何模型实现前停止。

> 上述 2026-07-22 条目只保留当时的实施记录；其中 Matrix v3 数值等价、48/46/54 allowlist、透明 score/execution 和模型 readiness 结论已被 2026-07-23 Accuracy Correction 审计撤回，不代表当前状态。

> 2026-07-21 P0 hard-stop 已实施：`report_full_research_669_readiness_v1.py` 现在保留 PR #4 工程 evidence，但把 validation/selection/model readiness 诚实标记为 false/blocked；新增 `selection_status.csv` 将 16 个历史代表登记为 `exploratory_global_representatives_v1`、`test_influenced`、`model_input_allowed=false`。通用 model entry gate 已接入现有 Ridge sanity runner，在任何数据读取和训练前同时检查 selection integrity、holdout/FDR/provenance/split allowlist readiness 与 selection registry，旧代表触发非零退出。100 tests 与 669 compact validator 本地通过；下一步进入全仓审阅和 provenance/canary，不启动模型。

> 2026-07-21 执行约束增补：审计时 669 readiness 仍错误为 true，现已由上方 P0 hard-stop 修复。此后先做 provenance/cache key v3 和受限 canary；30 批或其他大批量运行必须先生成 review bundle 与 exact approval artifact。当前持续对话已获用户明确授权，可在完整自审后使用 `user_session_waiver`，无需再次等待；任何 commit/config/input/command/scope 变化都会使 waiver 失效。FDR 语义固定为 outer-train eligibility gate + inner-window development robustness diagnostics；每个 outer test 前必须有 pre-test freeze。PR #5D 只完成历史 OOS 科学比较，保持 `production_model_selected=false`，最终确认依赖之后的新未来数据或 forward paper validation。

> 2026-07-20 PR #4 合并后审计：当前最高优先级改为 `SELECTION_HOLDOUT_INTEGRITY_AND_MODEL_PLAN_V1.md`。只读复核确认 stability role 使用 outer-test IC、test coverage 和 test-vs-validation degradation；clustering 使用完整日期 exposure/daily IC；Stability 未消费声明的上游 FDR artifact，而是内部重算；raw market cache 和外部因子源码未完整进入 batch input hash/lineage。外部与内部 FDR 的 2,007 个 q-value 全部不同，112 个 BH pass 标记不同；仅反转 test IC 即可使 `stable_core` 从 65 变为 1。当前 16 个代表改记为 `exploratory/test-influenced`、`model_input_allowed=false`。治理目标为 `core_model_ready=false`、`pr5_model_training_ready=false`、`model_training_started=false`；机器状态与新增执行约束以上方 2026-07-21 条目为准。

> 2026-07-20 PR #4 历史完成记录：669 runnable 因子按 Alpha158 155、Alpha360 358、TA 77、Alpha101 64、基础因子 15 冻结为 30 批；7.36 GB PIT 矩阵首轮完整物化并以 30/30 cache hit 完成约 32 秒复跑。669 因子 daily Rank IC、3 段 purged folds、3 个 family 各 669 个 hypotheses、稳定性 65 stable_core / 518 conditional / 86 monitor、65→16 聚类代表、三类透明 score 和 Qlib Exchange 均已完成。11 个 evidence stages 的输出哈希、clean-code、lineage 和关键 contract 当时通过，lineage issues=0。该记录保留 PR #4 工程结果；其中 `feature_allowlist_frozen=true`、`core_model_ready=true`、`pr5_model_training_ready=true` 以及“直接进入模型比较”的结论已被上方审计撤回，不再代表当前状态。

> 2026-07-20 PR #3 实施完成：在计算 IC/收益前按来源和类别冻结 80 因子，完成 65 月 PIT Top2000 universe、5 个分区各 2,588,000 PIT keys 的可恢复矩阵、`label_20d_t1`、80 因子 daily Rank IC、3 段 purged walk-forward、240 hypotheses FDR、滚动稳定性、12→9 聚类代表、三类透明 score 和三段 Qlib Exchange。11 个 evidence stages 的配置/输出哈希、clean-code、lineage 和关键合同均通过，lineage issues=0。当前 `full_research_trial_ready=true`、`pr4_scale_up_ready=true`、`model_training_started=false`；历史停牌/方向性涨跌停仍由代理字段推导，所以 authoritative tradability capability 保持 false。下一步只扩大到 669 因子，不在同一 PR 训练模型。

> 2026-07-20 PR #2 实施完成：固定 Qlib commit `d5379c5` 的 Exchange/Executor 链、signal/market adapter、原始与复权单位边界、A 股整手/费用/停牌/方向性涨跌停/T+1/参与率、target-delta、标准化输出、Manifest v2 和独立 CI 已落地。合成 Qlib/reference 对账 unknown difference=0；30 股票、80 交易日真实样本关键执行 contract 全部通过。当前 `qlib_exchange_infrastructure_ready=true`、`qlib_exchange_synthetic_ready=true`、`execution_reconciliation_ready=true`、`qlib_exchange_reference_ready=false`、`model_training_started=false`。reference blocker 为非 PIT 样本 universe 和非权威历史方向性可交易标签。下一阶段为 PR #3 的 50–100 因子 full-research 特征矩阵试运行，不运行 669 因子、不训练模型。

> 2026-07-13 V1.1.1 实施完成：manifest v2、output freshness、真实 lineage gate、受控 staging 发布、空选择阻断、semantic consistency、readiness 拆分、common-period NAV 归一化和路径配置化均已落地。活动 representatives/weights 均为 0，score parquet 已移除，execution/pre-model 已预期 blocked；stale stage count=0。当前 `reference_infrastructure_ready=true`、`reference_pipeline_ready=false`、`reference_ready=false`，74 tests 与 11 validators 通过。

> 2026-07-13 V1.1.1 一致性审计：当前最高优先级改为 `REFERENCE_PIPELINE_CONSISTENCY_V1_1_1.md`。复核确认 hardened stability 为 10 个 holdout、0 eligible windows、120 条 selection 全部 false，但活动 clustering 仍有 3 个旧 representatives，score 仍有对应权重和 2,819,616 行 runtime，execution/diagnostics 继续消费旧结果；当前 model gate 也未实际调用 `validate_lineage_chain()`。因此旧 `reference_ready=true` 是假阳性。

V1.1.1 目标状态：`reference_infrastructure_ready=true`、`reference_pipeline_ready=false`、兼容字段 `reference_ready=false`，其余 full/core/扩展能力和训练状态仍为 false。先完成 lineage/freshness、stale 输出清理、空选择阻断传播、semantic consistency、NAV 归一化和路径配置化；本轮仍不接入 Qlib Exchange、不训练模型、不运行 669 因子。

> 2026-07-13 V1.1 历史完成记录：V1.1 曾通过 60 项仓库轻量测试，但其 readiness 结论已被上方 V1.1.1 一致性审计推翻。以下内容只保留为修复前证据。

V1.1 当时报告的结果（已废止 readiness 部分）：诊断门禁已无环；pre-model 五种方法在统一 486 日公共区间比较；旧低覆盖稳定性输入的 10 个因子全部降为 `holdout`；reference execution 使用最近收盘价处理 2,203 次缺行情估值并披露 230,394,300 股未成交量。九类阶段已有 manifest，但后续确认部分 manifest 只是附加到旧业务结果，不能证明 freshness。`mlfinpy` 仍只作实现语义参考，不更新 Python、不作为仓库依赖。

> 2026-07-13 优先级更新：当前以 `FACTOR_VALIDATION_HARDENING_V1_1.md` 为最高优先级执行计划；它增补并修正 `Qlib A股因子研究框架完整升级计划 V1.md` 和 `FACTOR_VALIDATION_ROADMAP_V1.md` 的收尾门禁。本轮暂停新增因子源、模型训练、669 因子全量运行和 Qlib Exchange 接入。

V1.1 冻结审计：

- 当前阶段 10 要求 `regularized_linear`，阶段 11 又要求阶段 10 先通过，形成循环依赖；V1.1 将拆分 pre/post-model diagnostics。
- 当前模型 gate 混用 `local_smoke`、`local_reference`、目录名为 `full_research` 的 split 和 `current` 外部快照，尚无统一 artifact lineage。
- 当前稳定性仍读取旧 `liquid2000_open_source_eval`；4 个 `stable_core` 的 `coverage_min` 均约为 `0.074074`，不能代表 full-research 稳定性。
- 当前方法日历为 821 日与 486 日两组，公共有效日期为 486 日、差异日期为 335 日；V1.1 后排名只使用 common-period。
- AKShare 历史行业/市值缺口只应阻塞 `historical_exposure_model_ready`，不得作为所有 core model 的全局阻塞。
- V1.1 当时的历史目标状态为 `reference_ready=true`，该结论已被 V1.1.1 审计推翻；当前字段为 `reference_infrastructure_ready=true`、`reference_pipeline_ready=false`、`reference_ready=false`，其余 full/core/可选模型能力和 `model_training_started` 均为 false。

- 升级阶段 0 已完成：冻结 669 runnable / 499 new-source runnable、679 screening/judgement rows、342 research candidates、328 probes 和 V3.39 `0.1495 < 0.80` blocker；现有核心依赖与轻量命令检查通过。
- 升级阶段 1 已完成实现：Pandera DataFrame contracts 覆盖 factor、label、tradability、universe interval、screening 和 judgement；真实 compact output audit 4/4 pass，旧 label/universe 两项兼容缺口显式 warning，新输出不得继承例外。
- 升级阶段 2 已完成实现：实验性月度 PIT 流动性股票池复用 Qlib calendar/instrument interval，按历史 250 日成交额、180 有效日、120 上市交易日和次交易日生效规则生成；2024H1 local smoke 为 5 个可生效月份、1,000 snapshot rows，future reference、invalid interval、historical mutation 均为 0，Qlib instruments round-trip pass。
- 升级阶段 3 已完成实现：唯一交易日层面的 expanding Purged Walk-Forward 使用 20 日标签、T+1、20 交易日 embargo，2017—2026 真实日历生成 split manifest；train/test、train/validation 标签重叠、same-date cross-fold 和 embargo violation 均为 0。mlfinpy 只作 MIT 语义参考，不作为仓库依赖；当前使用自主区间重叠实现并由合成对照测试锁定行为。
- 升级阶段 4 已完成实现：moving-block bootstrap 对现有 10 个 V4 daily Rank IC 序列生成标准误和 raw p-value，statsmodels 统一生成 BH/BY q-value；test family 明确到 source × horizon × window × preprocessing。200 个 null factors 的 BH false-discovery rate 为 0，稳定合成信号检出，seed/order/NaN contract 均通过。
- 升级阶段 5 已有 reference profile：复用旧 V4 daily Rank IC 和阶段 3 split manifest，10 个 factor×horizon 覆盖 4 个窗口，19 个窗口决策入选；输出 4 `stable_core`、3 `conditional_signal`、3 `monitor`。selection API 拒绝任何 `test_*` 列，但 eligibility 仍缺 coverage/valid-IC 强校验，当前不能视为稳定性阶段完成。
- 升级阶段 6 已完成 reference profile：7 个 stable/conditional 因子同时使用 60 个历史截面 exposure Spearman 和 daily Rank IC performance Spearman，SciPy average linkage 得到 3 个簇、3 个代表，duplicate cluster votes=0。Riskfolio-Lib 保持可选未安装，不影响兼容后端。
- 升级阶段 7 已完成 reference profile：3 个 cluster representatives 在 4 个冻结 test 窗口生成 `equal_directional_zscore`、`cluster_equal`、`stability_weight`；权重只读取当前及更早 selection history，单因子上限 0.60 通过 capped renormalization 强制执行。future weight reference、duplicate cluster vote、weight sum error 均为 0，minimum components=3 ≥2；大型 score parquet 仅存 ignored runtime。
- 升级阶段 8 已有 reference profile：订单/成交/持仓/现金会计支持 100 股整手、最低佣金、买卖费率、卖出税、滑点、涨跌停/停牌拒单、T+1 状态、成交量参与率和部分成交。V1.1 仍需修复缺行情零价估值、含费用可承受数量、负现金门禁、完整日历/信号日历标记和未成交汇总；正式 Qlib Exchange 留到下一 PR。
- 升级阶段 9 已完成采集与 PIT contract 基础设施：AKShare 1.18.64 条件依赖安装且未升级核心数值栈；market-cap/float-cap 当前快照强制 `forward_only`，历史回填、缺 effective date、不可追溯来源和非法区间 contract 均为 0。当前东财端点被网络代理断开，`forward_snapshot_collection` 与 `historical_neutralization_ready` 正确保持 blocked，不生成或回填虚假历史暴露。
- 升级阶段 10 已有五种非模型方法的 reference diagnostics，但 Alpha158/旧 candidate 为 821 日，三种稳定性方法为 486 日，当前 `method_comparison.csv` 不能直接用于公平排名。V1.1 将输出 native/common-period 双表，并把当前入口明确重构为 pre-model diagnostics。
- 阶段 11 前置门禁入口当前为 9 个 prerequisite contracts、7 pass/2 blocked，runner 返回 blocked/exit 2 并确认 `model_training_started=false`。V1.1 将其改为五类能力门禁，删除 regularized-linear 循环和外部 PIT 的全局阻塞语义。

已完成历史里程碑（供追溯）：

- 不继续围绕单个 Alpha158、TA 或 Alpha101 因子细调策略。
- V3.28 `qlib_alpha360` source audit 与 adapter smoke 已完成：360 个 Qlib 原生公式全部可用，24 个 smoke 因子已生成 expression frame。
- V3.29 Alpha360 V4 smoke 已完成：22 个非恒等 smoke 因子进入 V4；Alphalens/Qlib eval 全部 pass，jqfactor_analyzer 保留已知 partial。
- V3.30 Alpha360 batch catalog/dry-run 已完成：358 个 batch candidates、2 个 adapter holdouts、72 个 planned dry-run batches。
- V3.31 Alpha360 batch358 factor frame 与真实 smoke batch_001 已完成：358 因子 frame 生成成功，batch_001 pass。
- V3.32 Alpha360 358 因子 batch V4 已完成：358 promoted、0 V4 batch holdout；已接入 multi-source screening / judgement。
- V3.33 new-source probe diagnostics 已完成：328 probes 全量看板、相关性诊断、tradability exposure 代理诊断、TopK portfolio smoke 均已接入 readiness。
- V3.34 new-source probe review 已完成：冗余/暴露复核层已接入 readiness，严格 OOS 候选收缩到 3 个 Alpha360 high-window 代表因子。
- V3.35 Alpha360 strict OOS extension 已完成：3 个严格候选在 2024-2026 recent OOS 窗口重新生成 factor frame，并通过 V4 多评价体系与 contract audit。
- V3.36 Alpha360 strict OOS stability 已完成：主窗口与 recent-OOS 指标对齐，信号指标无符号翻转，候选仍保持研究状态。
- V3.37 Tradability exposure attribution 已完成：19 个高可交易性暴露 probes 已分层，直接 raw training 前需要 holdout、人工复核或 residualization。
- V3.38 Exposure data capability audit 已完成：当前 provider 不支持市值/行业/Barra 字段，不能直接做 FactorTest-style industry/Barra neutralization。
- V3.39 Liquidity residualized factor evaluation 代码链路已完成但 contract blocked：19 个 watchlist probes 通过每日横截面 OLS 残差化（configured proxies: `liquidity_value`, `liquidity_bucket`, `tradability_score`；常数 proxy 会按日自动剔除）。残差列后缀 `__resid_liquidity`，不覆写原始因子。产出了 residualized factor frame、每日诊断、raw-vs-residualized 比较、候选动作决策与 contract status。当前 `residualized_coverage_min=0.1495 < 0.80`，audit 正确失败；downstream default 仍为 0。
  关键输出：
  ```text
  outputs/liquidity_residualized_factor_evaluation_v1/current/
    residualized_factor_frame.pkl
    residualized_factor_summary.csv
    daily_residualization_diagnostics.csv
    raw_vs_residualized_metric_comparison.csv
    residualized_candidate_actions.csv
    liquidity_residualized_contract_status.csv
    liquidity_residualized_factor_evaluation_report.md
  ```
- 下一步：先复核低覆盖来源，暂不把 V3.39 结果用于训练或默认候选；随后设计外部行业/市值数据接入 contract。
- 新增开源因子源、模型训练、策略优化和默认候选变更全部暂停，直至阶段 0 完成且后续对应门禁明确允许。
