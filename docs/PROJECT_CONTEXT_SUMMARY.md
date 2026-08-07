# Project Context Summary

本文件用于在对话很长时快速恢复上下文。

## Project

路径：

```text
E:\qlib_prj\qlib_baseline
```

定位：

- 个人 A 股量化研究项目，用于学习并实践 Qlib 因子、机器学习、组合和 forward
  research；不是机构平台、合规系统或生产交易基础设施。
- 优先级依次为研究逻辑正确、无未来数据、train/validation/test 隔离、可解释、
  易维护、自动化、工程治理；前三项严格，后四项按个人项目成本收益取舍。
- 旧 manifests/validators/lineage/frozen artifacts 保留兼容；新增研究模块默认采用
  Python + YAML + CSV/JSON + Markdown + focused pytest 的轻量设计。

## Current Direction

权威路线为 `docs/PERSONAL_QUANT_RESEARCH_ROADMAP.md`。当前历史状态是 LightGBM
研究与 P01 历史组合回测均已完成；P01 固定为 52 因子、Long Only Top50 等权、每
5 个交易日调仓。`split_003` 已被观察，不能再用于策略选择或声称新的独立 OOS。

当前最高工程优先级是尽快启动轻量 Forward Track：Daily Data Update V1、冻结
Strategy V1 prediction 和 paper portfolio 持久记录，以开始积累 genuine prospective
evidence。历史数据与诊断可以稍后复现；某日若没有用当时可得数据真实产生 feature、
prediction 和 paper decision，未来不能把事后补算结果声称为当天的独立 forward
证据。因此 forward collection 具有时间优先级。

Strategy Diagnostics V1 是重要的并行历史研究任务，但不再是 Forward Track 的前置
条件。它解释 P01 在 `split_003` 的历史弱势，只做 performance、IC、style/industry、
concentration 和 turnover/cost 诊断，不重训、不筛因子、不扫描 TopK/调仓周期、
不修改 Strategy V1。未来只有结合历史诊断与 genuine forward evidence，才判断是否
创建并独立保留 Strategy V2；shadow/small-capital 属于长期方向。本次文档调整不
实施任何业务模块。

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

## Historical Research Status

> **2026-08-06 PR #24 Historical Portfolio Backtest V1 完成：**只消费三份冻结 LightGBM historical test prediction，复用既有 Qlib Exchange/SimulatorExecutor、Market Cache V3、t+1、T+1、动态整手、涨跌停/停牌代理、5% 参与率与固定费用；没有重训、重建 prediction 或改变因子。预注册 6 个 TopK/调仓规则只在 split_001/002 比较，选中 P01（Top 50、5 日调仓），选择时 holdout read/execution 均为 0。P01 两段 development 平均净收益 29.10%、平均年化超额 61.70%、平均成本拖累 7.01%；随后唯一一次 split_003 holdout 净收益 3.57%，但相对 SH000985 年化超额 -30.24%、信息比率 -1.86、最大回撤 -4.33%、成本拖累 5.80%，未支持开发期的相对表现。即使近似加回成本，gross 9.37% 仍低于基准 19.19%；holdout 实际持仓 stale fallback 日期为 0，因此首要研究方向是市场状态稳定性与风格暴露，成本/换手居次，历史可交易性只保留为可信度限制。阶段合同全部通过，artifact 为 `historical_portfolio_backtest_v1:de86a138...`；结论仍是 post-observation / approximate 个人研究证据，`unbiased_final_estimate=false`、`production_model_selected=false`、`live_trading_ready=false`。不得因该回测继续扫描参数；如进入 forward paper portfolio，需另行冻结 P01 规则。

> **2026-08-05 PR #20B Prospective Forward Pipeline MVP：**实现 personal-research-grade 的本地单日入口：严格校验 OHLCVA 与既有 Matrix-v4-compatible 52 因子快照，按冻结顺序加载 Git 内容寻址 preprocessing/LightGBM 并生成 prediction；预测阶段没有 label 输入且读取计数为 0。正式发布采用“两步式”Git blob finalize，复用程序推导的下一交易日 09:25 cutoff 和真实 commit/tree/blob/timestamp 校验。同日正式预测不可覆盖，`--force-dev` 仅限非证据 dry-run。独立标签命令只在 t+21 成熟后读取标签并维护 daily Rank IC、Pearson IC、coverage 与一个 `outputs/forward/status.json`。当前数据仍止于 2026-06-09，因此只验证 dry-run，`forward_data_waiting=true`、`official_forward_prediction_count=0`、primary confirmation/production/live 均 false；没有重训、调参或更换候选。

> **2026-08-02 Forward prediction 入口加固：**`label_start_date` 现只由 admitted raw snapshot 的权威交易日历定位下一交易日，cutoff 由程序固定生成下一交易日 `09:25 Asia/Shanghai`；receipt 的日期、cutoff 和日历哈希只能复述推导结果。commit 必须真实存在，预测路径必须是 commit tree 中的普通 file blob，SHA256 从 blob 原始字节重算，committer timestamp 从 Git `%cI` 读取并要求严格早于 cutoff。此项只建立入口合同，未生成 prediction、未读 forward label，PR #20B 仍停止。

> **2026-08-02 PR #20A.1 Prospective hardening 完成：**审阅确认旧规则可能把“冻结后下载的旧日期”误作 forward，现已改为 `decision_date > candidate_freeze_effective_date_asia_shanghai` 且 `raw_snapshot_first_seen_at > candidate_freeze_effective_time_utc`；有效边界为 `2026-08-02T14:33:38.772344Z` / 上海日期 2026-08-02，故最早可能日期为 2026-08-03，且 first-seen 仍须越过精确时间戳。每份 prediction payload 与 commit receipt 都必须在下一交易日 09:25 前冻结且 label read=0。feature order 改为 V1.1，V1.1 protocol 成为 direct parent；Labels runtime 只经 manifest 解析并校验 SHA `4acdfd...`。模型未重训，原 SHA `c89972d...` 与预处理 SHA `679765a...` 已进入 Git 内容寻址目录并按 hash/size 复验。`forward_data_waiting=true`、production/live/forward confirmation 均 false；PR #20B 继续停止等待严格新数据。下方 PR #20A 的“晚于 2026-06-09”规则已废止，仅保留历史回执。

> **2026-07-26 PR #20A Prospective Forward 协议与候选冻结完成：**现有 2026-02-05—2026-06-09 扩展早于 PR #5D freeze，79 个日期全部隔离为非 prospective evidence；正式 forward 只接受 2026-06-09 后且 freeze 后首次进入 append-only snapshot 的日期。provisional candidate 固定为 LightGBM split_003 的 52 因子顺序、structure_04、200 rounds，不再搜索。5 因子×20 训练日/20 隔离日 canary 生成 40,000 prediction，两次模型与预测哈希一致、隔离标签读取 0。一次 full refit 覆盖 1,273 个 label-mature 日期和 2,538,428 行，耗时 253.1 秒、峰值 RSS 1,860.2 MiB；模型 SHA 为 `c89972d...`。`forward_candidate_refit_complete=true`、`forward_candidate_freeze_ready=true`，但无合法新数据，故 `forward_data_waiting=true`、`forward_prediction_confirmation_complete=false`、`provisional_candidate_confirmed=false`、`production_model_selected=false`、`live_trading_ready=false`。下一步仅在真实新数据到达时启动 PR #20B，不得评价既有隔离区。

> **2026-07-26 PR #5D 五方法历史科研比较完成：**本阶段只消费冻结透明 score 与已发布的线性/LightGBM test evidence，不重新训练或重新释放模型；透明基线标签哈希与 Ridge、Elastic Net、LightGBM release receipt 逐 split 完全一致。15 组 split-method、1,840 条 daily IC、15 组单方法和 30 组两两 moving-block bootstrap 全部发布，最低 coverage 0.995305。三个 split 等权 Rank IC 依次为 LightGBM 0.090936、Elastic Net 0.086887、Ridge 0.086470、Equal Weight 0.073678、Stability Weight 0.072760，因此仅记录 `historical_oos_research_leader=lightgbm`。LightGBM split 排名波动较大且大多数配对区间跨零，不能解释为稳定显著胜出。`historical_oos_model_comparison_complete=true`，但 `production_model_selected=false`、`unbiased_final_estimate=false`、`authoritative_oos_execution_ready=false`；`SZ300280` 的长期停牌估值能力缺口使五方法组合/NAV 比较继续为 `blocked_execution_capability`。

> **2026-07-26 PR #5C LightGBM 研究完成：**按四个预注册结构行 × 100/200/400/800 固定 checkpoint 完成 3 split 共 48 个候选，禁止 early stopping，选参只使用 validation daily Rank IC。三层 canary 和 development smoke 均通过；正式 split_001/002/003 分别选中 structure_03×800、structure_01×100、structure_04×200，峰值 RSS 2,614.8 MiB。3/3 train+validation final refit、pre-test freeze 和 exact-date release freeze 在 test read=0 时完成；随后单次 test release 生成 735,882 行预测，三个历史 test Rank IC 分别为 0.077783、0.143224、0.051802，最低 coverage 0.995305。`lightgbm_model_research_complete=true`，但 historical test 已被观察，故 production、authoritative execution 与 unbiased estimate 均 false。下一阶段为 PR #5D 的五方法 prediction-level 科学比较；`SZ300280` 长期停牌估值阻断使完整组合/NAV 比较继续 blocked。

> **2026-07-25 研究级多因子模型阶段启动：**用户接受并冻结 Historical Instrument State V2 Decision B，明确禁止继续主动搜索、抓取或核实历史公告；除非未来由用户提供新数据源/Tier-0 接口，不再推进 authoritative historical execution。当前主线改为 `RESEARCH_GRADE_MULTIFACTOR_MODEL_V1_PLAN.md`：逻辑 PR #5A 建立 scoped model gate、Selection Lineage Closure 权威输入、45/46/52 split-specific feature order、target/preprocessing/metric/prediction/pre-test freeze 协议；日期 authority 必须消费 `date_split_semantics_v1` 和 Selection Lineage Closure 的日期副本，旧 purged manifest 只能作 legacy payload，禁止成为直接 parent。线性预处理使用 daily-equal weighted median/scaler，Ridge 禁止 `solver=auto`；LightGBM 使用 4 个结构行 × 4 个固定 boosting checkpoints，不用 L2 early stopping。PR #5B 依次运行 Ridge 与 Elastic Net；PR #5C 运行限制为 16 个完整候选/split；PR #5D 完成五方法历史科学比较。研究实验统一标记 `post_observation_research`，可以评价 prediction IC；authoritative execution、无偏最终估计和 production model selection 始终保持 false。

> **2026-07-26 PR #5B 线性模型完成与执行能力阻断：**Ridge、Elastic Net 均完成 3/3 split 的 train-only 搜索、train+validation final refit、6/6 pre-test freeze 和单次 test release，共生成 1,471,764 行 test prediction，提前 test read=0；`linear_model_research_complete=true`。冻结 Qlib/Market Cache V3 辅助诊断中 4/6 场景完成，两个 split_002 场景均在 2025-04-18 对长期停牌的 SZ300280 已持仓估值时超过 20 日 stale 上限，显式阻断为 `blocked_unpriceable_held_position`。其余完成场景的现金、会计、费用、方向性可交易、参与率、动态 lot 与 T+1 合同通过。禁止无限旧价回填、未来知情清仓或伪造终止上市结算；因此 `linear_model_execution_complete=false`、`linear_model_execution_operational_ready=false`。该 Decision B 能力缺口不回滚 prediction-level 研究，并允许 PR #5C 按零泄漏协议继续；但 PR #5D 的五方法组合/NAV 比较保持 blocked，除非未来用户提供新 Tier-0 数据或明确批准新的执行政策。

> **2026-07-25 Historical Instrument State V2 Decision B：**已冻结 735,882 行 decision scope、36,136 行 valuation scope、99 个 Tier-1 状态边界和 8 笔 terminal approximation。13 条人工归一化 Tier-0 事件的官方原文全部成功下载并保存 URL、retrieval time 与 SHA256；fail-closed contract、候选边界对账、3/3 terminal 股票和 3/3 盘中对照通过。但 ST 仅 5/10、全天停牌仅 3/10，before-open 可证明率仅 38.46%，另有 8 条同日 date-only 或事后证据只能标 unknown。结论固定为 Decision B：BaoStock 可用于候选定位，不能授权权威 PIT 状态；没有任何 terminal 证据给出可执行 cash-per-share 处置。不得物化 Instrument State v2、Market Cache v4 或重跑历史 NAV；authoritative OOS readiness 保持 false。该阶段的“继续 source re-evaluation”建议已被用户随后明确撤回；研究模型阶段按上方最新条目推进。

> **2026-07-24 Historical Instrument State V2 启动：**V1.2 执行中的 8 笔 `terminal_event_settlement_approximation` 只涉及 SZ000413、SZ002308、SH600811。代码在 provider lifecycle 结束后的首日按最后估值价和无限容量强制卖出；官方初查表明对应日期首先是不可交易的停牌日，不能视为现金处置或市场成交。当前唯一计划改为 `HISTORICAL_INSTRUMENT_STATE_V2_PLAN.md`：先冻结 decision/valuation/terminal scope，建立 Tier 0 官方事件 evidence schema 和 before-open fail-closed canary，再决定是否全量物化 Instrument State v2。Matrix v4、selection、score 均冻结，模型 hard-stop 不变。

> **2026-07-24 Execution Unit Semantics Correction V1.2 完成（历史阶段记录）：**Market Cache v3 在不改变 Matrix v4、selection、weights 或 score 的前提下，将 Community volume 明确转换为 `provider_volume × factor × 100` shares，将 amount 转换为 `×1000` CNY；三个 split 共 853,936 行，unit unknown=0。冻结 score SHA 仍为 `beb4e4ad...`。3 split × 2 method 修正执行覆盖 730 个会计日，关键合同全通过、unknown execution difference=0；相对旧证据 ending NAV 变化约 -19.1万至 -26.6万元。SZ302132 的独立归因已落盘。中央状态为 `market_cache_v3_ready=true`、`execution_unit_semantics_ready=true`、`execution_semantics_accuracy_ready=true`，旧 `market_cache_v2_ready=false`；历史 ST、盘前停牌和 terminal event 仍无权威 PIT 证据，因此 authoritative OOS、core model、PR5 training、training-started 全为 false，hard-stop 保持 true。该条目当时要求先做 Historical Instrument State V2；该阶段现已以 Decision B 结束，后续方向以上方 2026-07-25 模型阶段条目为准。

> **2026-07-24 Data Source Audit V2 与 readiness 撤回：**Phase A 的 corrected-score lineage closure 已完成：score runtime 1,471,764 行 SHA 保持 `beb4e4ad...`，Universe v2、split、catalog、frame lineage complete；`SZ302132` 的 124 行现全部为 chinext，board coverage=1；当前链 22 个 artifact / 61 条 edge 的 transitive validator 为 0 issue。Phase B 冻结 150 股（main 67 / chinext 53 / star 30）并采集 2024-08-01 至 2026-02-04：Community 52,224 行、BaoStock 52,593 行，52,224 个共同 key 的 close/volume/amount 容差匹配率均为 1.0；AKShare Eastmoney 仅 3/150 成功，147 个 ProxyError，不能作为稳定 provider。确定性 P0 是 Community volume 必须 `provider_volume × factor × 100` 才是 shares，而 Market Cache v2 只乘 factor，participation capacity 缩小 100 倍；amount 还需 `×1000` 变为 CNY。结论为 Decision B（core raw OHLC 可靠，不需要 Matrix v5），但 execution/market-cache readiness 已机器级撤回，状态为 `execution_unit_semantics_correction_required`。下一步严格按 `EXECUTION_UNIT_SEMANTICS_CORRECTION_V1_2_PLAN.md` 修正 cache/freeze/execution；PR #5A、模型训练、因子选择变更仍禁止。

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

> **2026-08-07 Forward-first 路线修正：**当前最高优先级是 Daily Data Update V1、
> 冻结 Strategy V1 prediction 与 paper portfolio 组成的轻量 Forward Track，尽快开始
> 产生无法事后补回的 genuine prospective evidence。Strategy Diagnostics V1 改为并行
> 历史研究任务，复用冻结 predictions、Historical Portfolio Backtest V1 与现有市场/
> 因子/universe 数据解释 performance、rolling Rank IC、Size/Momentum/Volatility/
> Industry、集中度及 turnover/cost；它不阻塞 forward，也不得训练、选择因子、搜索
> 参数、扫描 TopK/rebalance 或修改 Strategy V1。以下旧 `Next Work` 条目仅保留历史
> 时间线，不再代表当前执行优先级。

> **2026-07-24 Accuracy Correction V1.1 / Data Source Audit V2 接管主线：**实现前核验确认 `split_transparent_score_v2` 为 pass 但 lineage inconsistent，根因是 date-only `purged_walk_forward_v1` 仍携带旧 Universe v1，并与 Matrix v4/Universe v2 一起被 policy、mutation、canary 和 score 的无维度 lineage 聚合传播；下游又未统一检查 parent lineage/critical contracts。`instrument_state_v1` 的 124 个 unknown-board 行全部属于合法创业板代码 `SZ302132`（中航成飞由 300114 变更代码），当前推断器漏掉 302 号段；这导致 critical `lot_rule_resolved=blocked`，但 manifest 仍错误为 pass。当前计划先实施维度化 lineage 语义、通用 fail-closed publication/parent/transitive gate、score 数值无损重发和最小执行链；再做 Community/BaoStock/AKShare 100–200 股 canary。不得进入 PR #5A、训练模型、改变选择链或声称 authoritative historical OOS。

> **2026-07-23 PR #7 Execution Accuracy Correction DoD 完成：**Market Cache v2 已显式绑定 Universe v2，三个 split 共 853,936 行，future field=0、禁止估值 bfill，陈旧阈值命中 174/525/199 行。三个 post-observation bugfix freeze 在执行前冻结；corrected OOS 产生 65,582 个订单、61,626 笔成交和 730 个会计日，现金非负、会计守恒、方向性涨跌停、动态整手、费用分项和完整日历关键合同全部通过，unknown semantic difference=0。机器状态为 `research_formula_accuracy_ready=true`、`execution_semantics_accuracy_ready=true`、`market_cache_v2_ready=true`，但历史 ST、盘前停牌和 terminal-event 权威源缺失，故 `authoritative_oos_execution_ready=false`、`core_model_ready=false`、`pr5_model_training_ready=false`、`model_training_started=false`、`unbiased_final_estimate=false`。按用户边界在 PR #5 前停止。

> **2026-07-23 PR #6 Research Accuracy Correction 本地 DoD 完成：**45/46/52 三份 allowlist、六组 weights 与 development-only score policy 已冻结。`selection_mutation_contract_v2:bcfb086a...` 的 36 个 outer-test IC/exposure/labels/raw mutations 均有效，但 development projection 与 FDR/stability/clustering/allowlist/weights payload hash 全部不变；Alpha101 轴重排与 lifecycle impact metamorphic contracts 同时通过。当前 `research_formula_accuracy_ready=true`，但 `execution_semantics_accuracy_ready=false`、`model_research_ready=false`、`core_model_ready=false`；下一阶段只能是 PR #7 execution accuracy，不得进入 PR #5A。

> **2026-07-23 PR #6 合并、PR #7 启动：**PR #6 已 squash merge 为 `3492200`，main 上 161 tests 与 hard-stop validator 通过。研究层现在可诚实标记 `model_research_ready=true`，但 `core_model_ready=false`、`pr5_model_training_ready=false`、`model_training_started=false`。PR #7 首先按 PR #6 冻结的 allowlist/weights/score policy 确定性物化 score，不能修改研究选择；随后才实施 fee/field timing/PIT state/cache/execution，且在 PR #5 前停止。

> **2026-07-23 PR #7 score 输入冻结完成：**clean canary 后，`split_transparent_score_v2:fc2080f0...` 对 120/124/124 个 outer-test 日期和两种透明方法物化 1,471,764 行 score。46 个 Matrix v4 分区哈希、PR6 score policy 与 mutation proof 均验证一致；组件政策覆盖 1.0，最低组件 14/10/12，输出不含 label/return/IC/NAV。下一步仅实施 execution semantics。

> **2026-07-23 Pairwise Spearman IC v2 完成：**真实 5 因子 canary 后完成 30/30 分区、669/669 因子。每个 `(date,factor)` 在 factor-label 共同非空集合内独立 rank，记录 pair/missing/tie evidence；scipy 人工例误差 0、行序与缺失位置 mutation 通过。最少 1,228 个有效 IC 日，有效日最小 pair 102。相对 v1 有 621 个因子、598,072 个日 IC 被修正，最大绝对差异 0.380201；缺失状态无不对称转移。`full_research_daily_ic_v2:3e20d7...` clean/complete/pass，`pairwise_ic_ready=true`。其后的 bootstrap policy 结果以上方最新条目为准。

> **2026-07-23 Labels v2 完成：**`full_research_labels_v2:404fe4...` 在 Matrix v4 的 2,587,671 个 lifecycle-clean key 上按 canonical Qlib calendar 精确连接 t+1/t+21 close，不使用物理行 shift 或价格填充。1,294 个 feature date offset 全部精确；末端 21 个日期、42,000 key 全部按预期缺失；有效 2,538,428 行，coverage 0.980970。重复 key、非法 lifecycle residual、terminal nonmissing 均为 0，Matrix/Universe/raw/key hashes 全绑定，Manifest clean/complete/pass。`labels_v2_ready=true`，其后的 Pairwise IC v2 结果以上方最新条目为准。

> **2026-07-23 Matrix v4 全量完成：**30/30 分区、669/669 因子，每分区 2,587,671 个 Universe v2 key。605 个 non-Alpha101 pure-time-series 因子在所有合法共同 key 上与 v3 位级一致；64 个 Alpha101 按 exact dynamic PIT membership 完整重算，61 个因子发生变化、累计 107,066,948 个值级修正，3 个无变化因子仍按 fallback 风险完成重算。首次 receipt 因同时继承 v1/v2 universe 被正确识别为 lineage inconsistent，未被接纳；runner 与 approval 生成器均修正为显式权威 v2/catalog 绑定，并拒绝非 complete/dirty approval。最终以 30/30 cache-hit 重新核验，Matrix artifact `full_research_feature_matrix_v4:10f6e0...` 与 approval artifact 均 clean/complete/pass。`matrix_v4_lifecycle_clean=true`；其后的 Labels v2 结果以上方最新条目为准。

> **2026-07-23 Matrix v4 canary 完成：**五来源 canary 在完整动态 Top2000 PIT 横截面、2021-09 的 39,981 个合法 key 上运行。Alpha158、Alpha360、TA、project_basic 代表因子与 Matrix v3 逐位一致；Alpha101 mixed/cross-sectional 代表分别纠正 39,859/39,908 个共同 key，证明旧 union-universe 宽表污染不是“只删 329 行”可以修复。Alpha101 轴标签现在要求 exact equality，禁止同长度 positional relabel；returns 使用 `pct_change(fill_method=None)`，不跨 PIT 缺口前向填充。canary Manifest clean/complete/pass，后续全量结果以上方最新条目为准。

> **2026-07-23 因子依赖审计完成：**`factor_dependency_ast_v1` 已覆盖 669 个因子并生成 clean/complete/pass Manifest。605 个 Alpha158/Alpha360/TA/project_basic 因子以逐标的执行证据列为 common-key bit-identical 复用候选；Alpha101 的 2 个 cross-sectional、46 个 mixed、16 个公式 pure-time-series 全部强制重算，原因包括宽表 universe 依赖和历史 pandas 适配器 positional-axis fallback。当前目录无 `unknown`，但 unknown fixture 已证明 fail-closed。`factor_dependency_inventory_ready=true`，其后的 Matrix v4 canary 结果以上方最新条目为准。

> **2026-07-23 Universe lifecycle v2 完成：**生成器现在从源头执行 `rolling_universe_interval ∩ source_lifecycle_interval`，缺失 lifecycle 时 fail-closed。完整 2021–2026、Top2000 物化在 clean commit `e971956` 上运行：准确识别并修正旧 29 个越界 interval、移除 329 个非法 date-instrument key；最终 lifecycle violation=0、overlap=0、removed-key residual=0，Manifest v2 为 clean/complete。`universe_lifecycle_v2_ready=true`，但 Matrix v4、pairwise IC 和 model readiness 仍为 false。其后的 669 因子依赖分类结果以上方最新条目为准，不得把 Universe 或依赖清单完成误解为现有矩阵可直接复用。

> **2026-07-23 PR #6 首个业务门禁实施记录：**`outputs/accuracy_correction_v1/current/` 已成为当前权威治理状态。`selection_holdout_integrity_ready=true`，但 research/execution/model readiness 全部为 false，`model_entry_hard_stop_active=true`；旧 48/46/54 allowlist、weights、scores 已登记为 superseded，历史 execution/NAV 为 non-authoritative。通用 model entry gate 会优先读取该状态，旧 PR4.1 ready receipt 即使被显式传入也不能启动训练。136 tests、历史 receipt validators 与新增 hard-stop validator 已通过；其后的 Universe v2 结果以上方最新条目为准。

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
