# Historical Dataset & Validation Design Study V1

> 状态：`RESEARCH COMPLETE`。本阶段研究数据历史与 validation 的统计充分性；未启动 Structured ML，未读取 Structured ML outcomes，未修改 frozen Matrix、Research Protocol V2、Strategy V1 或 Forward Track。

## 结论

当前 Matrix 从 `2021-02-01` 开始，不是已证明的数据源硬限制。Git lineage 显示该日期首次由 2026-07-20 的 full-research 工程配置引入，随后被 raw snapshot、universe、Matrix v4、labels、Factor Universe V2 readiness 和 Research Protocol V2 继承。旧 local-reference research config 从 2017 开始，本地 Qlib provider 的 OHLCV/amount/VWAP 实际从 2000 开始。

当前 1,294 个 Matrix dates 中有 1,273 个成熟 `label_20d_t1` dates。20 日重叠标签的市场截面均值 lag-1 自相关为 `0.954`，HAC(40) variance inflation 为 `15.28`，所以全历史约只有 `83.3` 个 market-level 有效时间观测。40 日 validation 的项目实测 label ESS 约 `2.6`；54 条 frozen sleeve daily-IC 序列在 HAC 20–40 日带宽下的中位 ESS 约 `3.8–4.0`。当前五个 V2 development folds 只有 `35–43` 个可用日期，因此其 leakage safety 是正确的，但 temporal-length design 不应继续作为 Structured ML selection authority。

本研究不冻结一个新的最佳 split。证据支持的候选数量级是：

- `120–252` trading days 的 sequential validation blocks；120 日是后续研究的下界候选，252 日是更强的统计候选；
- 比较 `4–6` 个较长 chronological environments，而不是增加很多短 folds；
- expanding 保留为高样本效率 incumbent；`sliding_504` 没有充分数据依据；历史扩展后最多注册一个有经济含义的 `3–4 年` coarse sliding hypothesis；
- rolling step 与 validation length 分开设计，未来只应预注册少量如 `63/126` 日的 cadence hypotheses，并由 decay、retraining cost 和 label maturity 解释；
- CPCV/blocked bootstrap 只作 secondary robustness，不能替代 past-only chronological authority。

因此：**现在不应启动高自由度 Structured ML competition。应先进行历史数据扩展资格研究与 bounded Matrix extension。** 优先级是先验证/扩展 full-feature history 到 `2018`，再决定是否推进到 `2015`；price-volume representation 可另行研究 `2008/2010` 起点，2000–2007 只作为更深 technical capability frontier，不直接声明 modern-regime training authority。

## 研究边界与复现

本阶段读取：

- frozen Matrix/labels/universe manifests；
- 2,587,671 个 PIT label keys；
- 本地 Qlib provider 的 6,106 个 instrument directories；
- Factor Universe V2 inventory/qualification；
- frozen Economic Multi-Factor Research 的 score 与 daily IC，仅用于 dependence，不用于选 window performance；
- 247 个 bounded Tushare probes，随后补充 2000–2004 年度 probes，总计 267 个 receipts。

关键机器产物：

- [matrix_start_lineage.csv](matrix_start_lineage.csv)
- [source_capability_audit.csv](source_capability_audit.csv)
- [qlib_field_coverage.csv](qlib_field_coverage.csv)
- [tushare_probe_receipts.csv](tushare_probe_receipts.csv)
- [factor_family_historical_depth.csv](factor_family_historical_depth.csv)
- [temporal_dependence.csv](temporal_dependence.csv)
- [effective_sample_size.csv](effective_sample_size.csv)
- [block_bootstrap_sensitivity.csv](block_bootstrap_sensitivity.csv)
- [frozen_signal_score_persistence.csv](frozen_signal_score_persistence.csv)
- [market_regime_descriptors.csv](market_regime_descriptors.csv)
- [feature_distribution_drift.csv](feature_distribution_drift.csv)
- [regime_window_coverage.csv](regime_window_coverage.csv)
- [validation_design_comparison.csv](validation_design_comparison.csv)
- [data_extension_feasibility.csv](data_extension_feasibility.csv)
- [dataset_design_evidence_map.csv](dataset_design_evidence_map.csv)
- [literature_evidence_map.csv](literature_evidence_map.csv)

复现入口：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_historical_dataset_validation_design_v1.py --stage probe
E:\anaconda_envs\qlib_env\python.exe scripts\run_historical_dataset_validation_design_v1.py --stage analyze
E:\anaconda_envs\qlib_env\python.exe scripts\run_historical_dataset_validation_design_v1.py --stage finalize
```

`probe` 会复用已有 probe IDs，只补缺失 receipts；所有 public parameters 都不含 token。analysis seed 固定为 `20260830`。

## 2021 起点 lineage

1. commit `eae3f198...` 在 `configs/full_research_feature_matrix_v1.yaml` 首次设置 `start_date: 2021-02-01` 和 `warmup_start_date: 2020-09-01`；该 commit 同时一次性建立 80-factor full-research pipeline。
2. raw snapshot、PIT universe、Matrix v4、labels v2 将该范围作为上游 scope 继承。
3. Factor Universe V2 readiness 没有重新选择历史起点，而是把已冻结 Matrix range 作为 qualification grid；`2020-01-17` bootstrap start 是从 2021 research start 倒推 252 个 provider sessions。
4. Protocol V2 消费 Matrix boundary，解决 exact label interval purge 和 evidence authority，但未完成 historical-depth 或 ESS study。

结论分类：

```text
数据源客观限制                  否
工程阶段选择                    是
历史 artifact inheritance       是
人为设定                        是（但当时有冻结治理，不等于统计依据）
```

## Historical Data Capability Frontier

| 历史区间 | 已观测能力 | 当前科研判断 |
|---|---|---|
| 2000–2006 | Qlib OHLCV/amount/VWAP、daily_basic 广覆盖；SH000985 从 2005 | price/basic technical frontier；moneyflow 为空，复权/旧制度审计不足，不支持 Full V2 |
| 2007–2009 | price/basic 完整；moneyflow 仅约 50%–56% 的当日股票覆盖 | price-volume extended history；不得称 full-feature common history |
| 2010–2014 | daily/basic/moneyflow 年度 probe 覆盖基本一致；财报样本存在 | Full V2 source-theoretical frontier，但 early PIT revision completeness、adjustment 与 instrument-state 未证明 |
| 2015–2017 | 同上，并覆盖重要市场结构与极端阶段 | full-feature extension candidate；必须先做 market-wide PIT/coverage canary |
| 2018–2020 | 所有主要层均可取；当前 statement snapshot 的 availability 从 2018 开始 | 最低风险的第一阶段 full-feature extension target |
| 2021+ | frozen Matrix 的全部资格审计已通过 | 当前 authoritative common history |

API 可返回旧数据不等于 PIT 可靠。六只长期上市样本的 income/balance/cashflow/fina_indicator 可见 1998–2000 报告期，且 income/balance/cashflow 共观察到大量 `update_flag=1` 行；这证明 revision-aware implementation 有真实对象，但不能证明市场全量、所有早期年份、所有撤回/更正版本都完整。故 fundamental PIT 的 pre-2018 frontier 保持 `medium-low` confidence。

当前 2,000 积分权限足够调用 daily/basic/moneyflow、四张财务表、dividend、stock_basic 和 namechange。权限不是历史扩展 blocker；request volume、revision completeness 和 validation 才是。

### Schema、单位与 adjustment

- Qlib `$open/$high/$low/$close/$volume/$amount/$vwap/$adjclose` 在 2000–2026 每年相对 `$close` 的 finite observation ratio 约为 1.0；这说明本地文件层没有显式 field coverage 断裂。
- 当前 Matrix adapter 已确认 Qlib amount 为千元、Tushare moneyflow 为万元、Tushare total_mv 为万元，并在 V2 中转换为 CNY。
- 但早期 corporate-action 事件和 `$factor/$adjclose` 语义没有达到与 2021+ 同等的独立审计强度。扩展 price history 前必须选取拆分、送转、分红事件验证 return continuity；不能仅因二进制字段存在就判为 PIT-safe。
- Qlib community provider 合并多个上游来源；release snapshot 不等同于 historical source vintages。

## Factor family 历史深度

765 个 research-usable factors 的依赖起点并不一致：

| dependency layer | defined | usable | frontier |
|---|---:|---:|---|
| price_volume_core | 733 | 724 | Qlib technical 2000；研究候选 2008/2010 |
| daily_basic + price/volume | 12 | 12 | probe 2000；受 full comparison frontier 约束 |
| moneyflow + price/volume | 10 | 10 | 2010 stable coverage |
| fundamental PIT + daily_basic | 19 | 19 | technical old history；pre-2018 PIT completeness 未证明 |

因此不应要求 765 factors 机械共享一个未经研究的起点，也不应为了更长历史默默删除 41 个 non-price-core factors。建议保留两条明确命名的数据哲学：

1. `full-feature common-history`：Structured ML 主比较的公平基线；先扩到 2018，再审核 2015。
2. `tiered / representation-specific history`：price-volume 724-factor core 可使用更长历史，但必须作为单独 representation study，在共同重叠期和各自最大历史期分别报告，不能把不同样本期的 raw performance 当成公平 winner comparison。

## Temporal dependence 与 ESS

标签定义：

```text
label_20d_t1 = close[t+21] / close[t+1] - 1
```

如果一日 innovations 独立，20 日 overlapping sums 的理论相关为 `rho(k)=(20-k)/20`（`k<20`）。项目实测：

| measure | lag 1 | lag 5 | lag 10 | lag 20 |
|---|---:|---:|---:|---:|
| cross-sectional mean 20d label | 0.954 | 0.738 | 0.503 | -0.061 |
| SH000985 20d label | 0.940 | 0.711 | 0.465 | -0.000 |
| equal-weight 1d market return | 0.060 | -0.021 | 0.030 | 0.044 |

这说明主要 dependence 确实来自 label overlap，而不是简单的一日市场 return persistence。frozen sleeve scores 也高度持续：跨股票 score correlation 的中位数在 lag 1/5/20 分别为 `0.995/0.971/0.882`，因此候选每日 IC 不会因股票截面很大而变成独立日序列。

### Validation length comparison

| nominal dates | iid 20d-overlap theory ESS | project label ESS HAC(40) | individual sleeve IC median ESS HAC(20–40) | regime terciles average | status |
|---:|---:|---:|---:|---:|---|
| 40 | 2.40 | 2.62 | 3.8–4.0 | 2.25/3 | reject for Structured ML selection |
| 60 | 3.37 | 3.93 | 5.7–6.0 | 2.47/3 | diagnostic / latency-sensitive only |
| 120 | 6.35 | 7.86 | 11.4–12.0 | 2.74/3 | lower-bound candidate after extension |
| 252 | 12.94 | 16.50 | 23.9–25.2 | 2.89/3 | strong candidate after extension |

HAC bandwidth sensitivity没有让 40 日变得充分：label ESS 在 bandwidth 5/10/20/40 下为 `7.4/4.5/3.0/2.6`。stationary bootstrap 对 label mean 的 standard error inflation 在 mean block length 5/10/20/40 下约为 iid 的 `2.68/3.34/3.59/3.64`；SH000985 结果相近。不能用最短带宽或 iid standard error 宣称 40 个独立日期。

一个 future validation block 至少应同时满足：

- exact `[t+1,t+21]` labels 在下一个 authority boundary 前成熟；
- conservative HAC/block sensitivity 下至少约 `10–15` 个有效 IC dates，不能只满足 nominal row count；
- 多数预定义 market descriptors 的 low/middle/high states 有实际覆盖；
- candidates 之间有 paired daily comparison、worst fold、dispersion、negative-fold、coverage/failure；
- block-bootstrap uncertainty 不被 iid uncertainty 替代；
- fold 有足够长度，同时不过度延迟 retraining。

120 日刚接近最低 ESS criterion；252 日更稳健。最终长度仍需在扩展数据上复测，不能把本报告数字直接冻结为 Protocol V3。

## Regime coverage 与 structural drift

regime descriptors 在读取任何 Structured ML result 前定义：broad-market/benchmark return、20 日 realized volatility、cross-sectional dispersion、breadth、total turnover、Amihud proxy、small-minus-large spread。每个 descriptor 使用全期 terciles；一个 window 中某 tercile至少出现 5 日才算 represented。

当前 V2 五个 development windows 的平均 coverage 为 `2.20/3`，最差 window 为 `2.00/3`。固定 40/60/120/252 日候选的平均 coverage 为 `2.25/2.47/2.74/2.89`。长 window 明显减少“完全落在单一短状态”风险。

年度 descriptor 与 feature distribution 均显示漂移，但不支持一个精确的 two-year cutoff：

- 2021–2026 年 market realized volatility 年度中位数约 `0.145–0.257`；
- label cross-sectional mean 年度中位数从约 `-1.5%` 到 `+3.8%`；
- representative momentum、realized volatility、Amihud 因子的年度 median shift 最大分别约为全期 IQR 的 `0.72/0.52/0.53`；
- size、turnover、ROA 和 moneyflow 的 shift 较小但非零。

制度解释只作外部背景，不用于手工切 window：2005 股权分置改革、2014 沪港通、2019 科创板注册制和 20% price limit、2020 创业板注册制与 20% price limit、2023 全面注册制都说明“历史越长越好”并非无成本。研究仍应使用可计算 descriptors 衡量 drift，而不是给年份贴主观牛熊标签。

## Training history、step 与 folds

### Expanding versus sliding

expanding 的优势是最大化有限 temporal information、覆盖更多极端状态、降低小样本估计噪声；风险是旧制度和旧 factor-return relation 稀释当前关系。

sliding 的优势是适应 distribution/relationship drift、降低旧 universe composition 权重；风险是丢掉稀缺 regime、让高自由度模型在更少独立时间样本上训练，并把 window length 变成新的选择自由度。

本研究只证明 drift 存在，没有证明 `504` 是关系半衰期或最优训练长度。因此：

- expanding 仍是方法论 incumbent；
- `sliding_504` 从“已冻结候选”降为“无充分 temporal-length依据的历史 hypothesis”；
- 扩历史后可预注册 `expanding` 与一个 `3–4 year sliding` coarse alternative；不要扫描 252/378/504/630/756/1008；
- 选择窗口必须留到新 protocol 独立冻结后的 development evidence，不能用本阶段的 historical model outcomes。

### Fold count 与 rolling step

股票截面行数很多，但时间 authority 仍按日期。十个 40 日 folds 不会自动提供比四个 120–252 日 folds 更多可靠信息，因为 folds 内部和相邻 folds 的 labels/signals 都高度依赖。

validation length 主要由 ESS、regime coverage、metric discrimination 和 label maturity 决定；rolling step 主要由 expected model decay、retraining/rebalance cadence、compute cost 与证据重叠决定。两者不必相等。当前没有 Structured ML decay evidence，因此只允许在未来协议中把 `63/126` trading days 作为 coarse hypotheses，不能在本报告中选 winner。

## CPCV、blocked resampling 与 Qlib

- exact interval purge 继续由 chronological protocol authority 执行；它解决 leakage，不解决 ESS。
- moving/stationary block bootstrap 适合衡量 daily IC/paired delta 的 uncertainty 与 block-length sensitivity。
- CPCV/CSCV 可在 candidate 已由 chronological development freeze 后，作为 historical path-dependence robustness；不得让未来 blocks 参与过去 candidate selection。
- Qlib official Alpha158/DoubleEnsemble examples 使用 2008–2014 train、2015–2016 valid、2017–2020 test；这是多年 validation 的工程先例，不是本项目的证明。Qlib `RollingGen` 只适合在合法日期生成后 materialize tasks，不能决定 PIT、purge、evidence role 或 validation length。

外部文献的可迁移原则与限制见 [literature_evidence_map.csv](literature_evidence_map.csv)。特别是中国市场 JFE 研究使用 monthly targets、2000–2008 train、2009–2011 validation、rolling one-year tests 和 annual refit；它支持 chronological multi-year validation 的原则，但 monthly non-overlapping target 与本项目 daily overlapping 20d label 不可直接等同。

## Data extension feasibility

当前 V2 raw cache 约 `1.14 GB`，new V2 partitions `1.07 GB`，referenced V1 partitions `7.27 GB`。粗略线性估计：

| candidate start | additional trade dates | daily API requests | statement requests（4 APIs × 5y segments） | additional raw | estimated total matrix |
|---|---:|---:|---:|---:|---:|
| 2018-01-02 | 498 | 996 | 31,864 | 0.34 GiB | 10.27 GiB |
| 2015-01-05 | 1,230 | 2,460 | 47,796 | 0.84 GiB | 13.95 GiB |
| 2010-01-04 | 2,442 | 4,884 | 63,728 | 1.68 GiB | 20.04 GiB |

当前 bootstrap 的 5,280 network statement requests 用约 1,490 秒；线性外推意味着 2018/2015/2010 的 full statement fetch 可能是数小时级，另加 matrix recomputation。估计不含 retries、revision re-fetch、压缩变化和 factor compute overhead。

推荐 staged workflow：

1. 2018 起 50–100 issuer、多行业/上市年代 bounded PIT canary；
2. market-wide annual/quarterly row-count、announcement-delay、revision-duplicate、report-type 与 gap audit；
3. corporate-action/adjustment event canary；
4. 2018 full-feature extension；
5. 在扩展数据上重跑本阶段 ESS/regime/drift study；
6. 再决定是否扩到 2015；
7. review 后另建并独立冻结新 Research Protocol；
8. 最后才考虑 Structured ML。

## Protocol V2 scientific review

继续正确：

- exact `[t+1,t+21]` interval purge；
- train/validation/diagnostic/forward evidence role isolation；
- split-local eligibility 和 preprocessing；
- no diagnostic feedback to selection；
- candidate budget、paired fold views、failure/coverage disclosure；
- Strategy V1、Forward evidence 与 frozen artifacts 隔离。

不再建议作为 Structured ML authority：

- Matrix start 被当作 naturally given 2021 boundary；
- five `35–43` day development folds；
- two-month validation / three-month step 的具体长度；
- `sliding_504` 的具体 cutoff；
- “协议已具备 Structured ML 时间基础”的旧结论。

应保留 V2 作为 frozen historical artifact，并记录：

```text
Protocol V2 leakage safety = supported
Protocol V2 temporal statistical adequacy = not supported
formal_structured_ml_competition_started = false
dataset_window_selected_from_model_outcomes = false
```

## 对 33 个最终问题的回答

1. 2021 起点来自早期 full-research 工程 scope。
2. 它是工程历史选择与 artifact inheritance，不是数据源硬限制。
3. 各层日期见 capability frontier；只有 2021+ 已达到 current frozen full qualification。
4. 765 factors 起点不一致。
5. full history 的 source bottleneck 是 moneyflow stable 2010；authority bottleneck 是 early PIT revision/adjustment/state。
6. full-feature technically 可到 2010；当前推荐先资格化 2018，再研究 2015。
7. price/volume technically 到 2000；research candidate 2008/2010。
8. fundamental rows 到 1998–2000；PIT-reliable pre-2018 尚未证明。
9. moneyflow 2007–2009 partial，2010 起稳定。
10. 值得扩展 Matrix，但必须 staged qualification。
11. 2018/2015/2010 extension 估计见 feasibility 表，约 10/14/20 GiB total matrix，数小时级 bootstrap + recompute。
12. 5.3 年可做低自由度诊断，不足以支撑高自由度 Structured ML selection。
13. 20 日 label dependence 很强，lag-1 约 0.95。
14. 40/120/252 日 individual IC median ESS 约 4/12/25（conservative bandwidth）。
15. 当前 35–43 日 validation 不足。
16. minimum criteria 是 label maturity、ESS、regime coverage、paired uncertainty、coverage/failure 与 practical latency。
17. 合理数量级是 120–252 trading days，待扩展后复测。
18. 倾向 4–6 个长 sequential folds，不用很多短 folds替代时间信息。
19. step 由 decay/retrain cost/rebalance/maturity 决定，与 validation length 分开。
20. expanding 最大化样本和 regime，风险是旧数据 drift。
21. sliding 适应 drift，风险是丢失稀缺信息并增加自由度。
22. sliding length 应由 feature/relationship drift 与 regime coverage 形成 coarse hypothesis。
23. 504 没有充分依据。
24. 当前 development 覆盖 2023-05 至 2024-06 的五个短环境。
25. 有明显 regime diversity 不足：平均只覆盖 descriptor 2.2/3 terciles。
26. 需要更长历史才能同时获得长 folds、多个 regimes 和训练 history comparison。
27. CPCV/blocked bootstrap 值得作为 secondary robustness。
28. Qlib 提供 multi-year split 与 rolling materialization经验，但不能照搬日期。
29. V2 的 leakage/evidence governance 仍正确。
30. V2 的 matrix start、2-month valid、3-month step、504-day sliding 不再建议作为 authority。
31. 应在数据扩展 review 后建立新 protocol。
32. 建新 protocol 前应先至少完成 2018 extension qualification。
33. 当前不具备启动高自由度 Structured ML 的充分科学基础。

## Governance manifest intent

```text
formal_structured_ml_competition_started = false
dataset_window_selected_from_model_outcomes = false
structured_ml_outcomes_read = false
research_protocol_v2_changed = false
frozen_matrix_changed = false
strategy_v1_changed = false
forward_track_changed = false
authoritative_raw_snapshots_changed = false
```

本阶段到此停止，不生成或冻结新 Model Research Protocol，不执行完整历史 bootstrap，不进入 Structured ML。
