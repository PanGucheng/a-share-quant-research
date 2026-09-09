# Research Protocol V3-MVP：长历史 Purged Walk-Forward 正式实施计划

状态：`PLAN DELIVERED / IMPLEMENTATION NOT STARTED`。2026-09-09依据用户提供的《Research Protocol V3-MVP：长历史 Purged Walk-Forward 预研结论与 Codex 规划任务》制定；审计基线为远端 `main` 的 `f1c814d`。本次授权为协议审计与正式计划编写，不包含真实模型训练、feature-pool competition 或近期诊断。

## 1. 决策与交付范围

采用 **2010–2014初始历史、2015–2023九个自然年度、expanding、annual refit、exact label purge、单一冻结LightGBM** 的主方案。先实现并验收时间协议，再在独立实验中比较冻结的因子池。协议成功不以历史收益最高或压缩因子最多为标准。

相对预研，正式计划明确四项修订：

1. 全年预测与标签可评分范围分开。2015–2023可生成2,189个交易日的预测；开发期截止2023-12-29时，只有2,168个日期具有日历上成熟的20D标签。2023年最后21个交易日保留预测、禁止读取跨入2024的标签。
2. Exact purge限制的是**训练标签在下一次fit之前可知**，不是禁止相邻年度的评价标签重叠。2015–2022年末的OOF标签可以在随后开发年度成熟；下一年度训练仍排除尚未成熟的样本。
3. 现有494候选及严格共识候选使用过2010–2023筛选结果。它们可用于本轮回溯性开发比较，但年度模型OOF不证明整个因子发现流程在当年可实现。严格的全流程past-only选择需要另行实施fold-local筛选，不能靠purge或train-only coverage补救。
4. 旧LightGBM配置是16候选与checkpoint搜索协议，并非单一incumbent；本计划提出一个不依据V3结果选择的简单固定基准，另建年度入口，保留旧实现。

本次已完成日历、canonical identity、键轴规模和源代码审计。未读取新的特征值、标签值或模型outcomes；有效标签行数、逐池train-only可用特征数尚未实测，必须作为实施期训练前验收项，不能将键数称为有效训练样本数。

## 2. Authority与证据等级

唯一输入为[Canonical Research Dataset](CANONICAL_RESEARCH_DATASET.md)：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
physical horizon: 2010-01-29 .. 2026-06-09
development value ceiling: 2023-12-29
definitions: 774; research-usable: 765; blocked: 9
```

沿用dated universe、Alpha101 dated PIT rank、causal KAMA、practical reconstructed fundamental PIT及分区effective boundaries。765表示物理资格，不是各折模型白名单；不以全历史coverage决定早期资格。旧Matrix、Primary 20D、Consolidation V0.5/V0.5.1及V1/V2报告保持封存。

后续每份报告同时标记：

- `model_fit_scope = past_only_purged`；
- `pool_discovery_scope = retrospective_development_2010_2023`，历史Baseline另记原发现区间；
- `evidence_class = retrospective_pseudo_oos_development`；
- `unbiased_final_estimate = false`。

“池在本次fit前冻结”是当前实验版本的冻结，不等于它在2015年事前存在。全开发期筛选过的池禁止宣传为selection-past-only；若将来要求该证据等级，必须在每折合法训练历史内重做全部outcome-dependent selection，并登记为不同实验。真正prospective confirmation继续只属于Forward Track。

## 3. Current-State Audit与最小复用方案

| 对象 | 已核实事实 | V3处理 |
|---|---|---|
| [V1日期实现](../research_validation/purged_split.py) | `[t+1,t+21]`日历区间；旧流程另外删除20日embargo | 复用`label_intervals`；保留旧构造器与证据 |
| [V2构造器](../research_validation/research_protocol_v2.py)及[协议](../reports/research_protocol_v2/REPORT.md) | exact purge正确；5个两月环境、固定504安全交易日sliding、评价尾部受下一环境约束 | 复用合法区间与审计思路；新年度生成器不继承短窗口、504日或旧selection rule |
| [Historical Validation Study](../reports/historical_dataset_validation_design_v1/REPORT.md) | 旧标签市场截面均值lag-1约0.954；40D label ESS约2.6，旧V2仅35–43可用日 | 支持一年数量级；这些是旧样本研究结果，不能冒充新OOF的ESS或全部daily IC的自相关 |
| [Canonical reader](../research_validation/canonical_dataset.py) | `read_effective_partition`支持列投影、日期predicate与effective裁剪 | 直接复用底层；V3加角色/日期约束，禁止先读全期再切分 |
| [Consolidation reader](../factor_research/candidate_consolidation.py) | `read_panel`先求开发期交集、逐列键轴一致与slice receipt | 可复用有界读法；不调用绑定494工作集的`prepare_inputs`作为通用池入口 |
| [旧eligibility](../model_research/feature_eligibility.py)及[阈值配置](../configs/ml_feature_eligibility_mvp_v1.yaml) | feature-only统计可复用；旧765日、1,147,396有限行门槛来源于旧样本规模 | 不原样迁移绝对阈值，也不使用旧validation profile作早期资格 |
| [旧LightGBM入口](../model_research/lightgbm_models.py) | `lgb.train`未传outer valid_sets；但runner会扫描候选/checkpoint、选优并train+validation重训 | 复用参数构造、训练库和记录方式；新入口只fit一次、全年预测，不调用旧competition runner |
| [旧目标](../model_research/targets.py)与[预处理](../model_research/preprocessing.py) | 先用池内any-finite筛行再做标签rank；median/scaler具有train fitted state | 固定pool-independent标签rank；V3用原生NaN，取消此模型路径的median/scaler |
| [8T执行配置](../configs/research_lightgbm_full_exact_mt_v2.yaml) | LightGBM 4.6.0、旧工作负载1T/8T exact parity | 沿用8T确定性配置；旧parity不等于V3新数据已有exact证明 |
| 本机Qlib `qlib/workflow/task/gen.py::RollingGen` | commit `d5379c520f66a39953bad76234a7019a72796fd0`；支持expanding/sliding、固定session step与trunc_days | 自然年度不是恒定step；由V3按日历生成精确assignments。无需强行包装RollingGen或引入TaskManager |
| [V0.5.1提案](../reports/candidate_consolidation_v0_5/v0_5_1/REPORT.md) | 494身份保留，近似替代0条，五组精确关系；每层61项暂缓替代 | 不是最终Core；61项也不是统一的模型禁用名单。池构建须分别解释语义、价格尺度、事件和递归缺失限制 |

采用独立小模块和YAML，不建设通用实验平台，不改写冻结模块以兼容新配置。

## 4. Exact Fold Table：实测预览

来源为本机canonical provider的`calendars/day.txt`，先限制物理horizon，再调用`label_intervals(calendar, horizon=20, execution_lag=1)`。以下`usable_dates`只表示日历标签成熟，实际有限标签和每日minimum-pair检查可能进一步减少可评分日。

所有expanding折`train_start=2010-01-29`。`label_end`指本折最后可评分信号的标签结束日；训练标签结束日另表列出。

| fold_id | last_legal_train_signal | evaluation_start | evaluation_end | latest_mature_eval_signal | nominal_dates | usable_dates | label_end |
|---|---|---|---|---|---:|---:|---|
| annual_2015 | 2014-12-02 | 2015-01-05 | 2015-12-31 | 2015-12-31 | 244 | 244 | 2016-02-01 |
| annual_2016 | 2015-12-02 | 2016-01-04 | 2016-12-30 | 2016-12-30 | 244 | 244 | 2017-02-07 |
| annual_2017 | 2016-12-01 | 2017-01-03 | 2017-12-29 | 2017-12-29 | 244 | 244 | 2018-01-30 |
| annual_2018 | 2017-11-30 | 2018-01-02 | 2018-12-28 | 2018-12-28 | 243 | 243 | 2019-01-30 |
| annual_2019 | 2018-11-29 | 2019-01-02 | 2019-12-31 | 2019-12-31 | 244 | 244 | 2020-02-07 |
| annual_2020 | 2019-12-02 | 2020-01-02 | 2020-12-31 | 2020-12-31 | 243 | 243 | 2021-02-01 |
| annual_2021 | 2020-12-02 | 2021-01-04 | 2021-12-31 | 2021-12-31 | 243 | 243 | 2022-02-08 |
| annual_2022 | 2021-12-02 | 2022-01-04 | 2022-12-30 | 2022-12-30 | 242 | 242 | 2023-02-07 |
| annual_2023 | 2022-12-01 | 2023-01-03 | 2023-12-29 | 2023-11-30 | 242 | 221 | 2023-12-29 |

2015首折名义训练1,193日，经exact purge保留1,172日；各折恰好排除21个边界前signal dates，这是当前日历与标签语义的计算结果，代码不把21写成固定gap authority。

### 4.1 股票日期键数与成熟上界

本次仅投影覆盖`alpha158_BETA10`的canonical分区中的`datetime/instrument`列，按effective区间裁剪到开发期；检查无重复键且日期覆盖全部3,382个开发交易日。下表股票数为期间出现过的不同股票数，不是每日股票数；键数不保证该因子有限，更不保证标签有限。其他列的键轴一致性在实施时逐批验证。

| 年份 | 合法训练日 | 最晚训练label_end | 训练键数 | 训练股票数 | 全年预测键数 | 评价股票数 | 日历成熟评价键数上界 |
|---|---:|---|---:|---:|---:|---:|---:|
| 2015 | 1,172 | 2014-12-31 | 2,220,786 | 2,509 | 487,993 | 2,475 | 487,993 |
| 2016 | 1,416 | 2015-12-31 | 2,708,779 | 2,617 | 488,000 | 2,611 | 488,000 |
| 2017 | 1,660 | 2016-12-30 | 3,196,779 | 2,820 | 488,000 | 2,680 | 488,000 |
| 2018 | 1,904 | 2017-12-29 | 3,684,779 | 3,055 | 485,999 | 2,675 | 485,999 |
| 2019 | 2,147 | 2018-12-28 | 4,170,779 | 3,439 | 487,969 | 2,581 | 487,969 |
| 2020 | 2,391 | 2019-12-31 | 4,658,759 | 3,577 | 485,973 | 2,549 | 485,973 |
| 2021 | 2,634 | 2020-12-31 | 5,144,720 | 3,795 | 485,981 | 2,617 | 485,981 |
| 2022 | 2,877 | 2021-12-31 | 5,630,701 | 4,032 | 483,983 | 2,630 | 483,983 |
| 2023 | 3,119 | 2022-12-30 | 6,114,684 | 4,236 | 483,926 | 2,622 | 441,926 |

首折约222万合法日历训练键，末折约611万；从时间与键轴规模看没有必须把首折移到2014或延后的阻碍。**目前不能断言所有池满足有效样本和特征资格**，因为四池名单尚未冻结，且本次没有读取特征与价格值计算finite counts。

### 4.2 可选4自然年sliding

对OOF年份Y，固定训练候选区间为`[Y-4年的1月1日, Y年的1月1日)`与canonical交集，再应用同一exact purge；不是最后4×252行，也不是从purge后末日倒推4年。

| OOF年份 | 4Y实际起点 | purge后训练日 | 训练键数上界 |
|---|---|---:|---:|
| 2015 | 2011-01-04 | 949 | 1,865,332 |
| 2016 | 2012-01-04 | 949 | 1,897,923 |
| 2017 | 2013-01-04 | 950 | 1,899,963 |
| 2018 | 2014-01-02 | 956 | 1,911,988 |
| 2019 | 2015-01-05 | 954 | 1,907,993 |
| 2020 | 2016-01-04 | 954 | 1,907,980 |
| 2021 | 2017-01-03 | 953 | 1,905,941 |
| 2022 | 2018-01-02 | 952 | 1,903,922 |
| 2023 | 2019-01-02 | 951 | 1,901,906 |

该假说为可选secondary sensitivity，默认不执行；如启用，必须在首个模型结果出现前连同适用池一起登记。Expanding始终为primary authority，不按两种历史的收益挑赢家。后验决定增加sliding须另起研究版本并记录已观察结果。

### 4.3 年末成熟与跨年关系

2015–2022年度预测全部可在开发边界内评价，标签允许延伸到下一开发年；下一年模型不能使用这些尚未成熟的年末训练标签。OOF年份是prediction vintage，年度评价按signal year归属。

2023年预测至12月29日，开发评分只至**11月30日**，最后标签于12月29日成熟；12月1–29日共21日标记`unscored_development_boundary`，不算预测失败，不读其未来价格。这样可以保留连续全年预测，同时诚实说明最后一年评价为221日。

近期区间在当前日历上最后可成熟signal date为**2026-05-11**，其label_end为2026-06-09。本次只计算日期，不读取近期特征、价格、coverage或收益。

## 5. 数据访问、purge与预处理合同

令年度首交易日为E，训练样本必须满足`feature_time < E`且`label_end < E`，fit时间记为E首个signal形成前，模型全年冻结；每日signal使用当日允许的数据，执行最早t+1。停牌不把t+21改成该股票第21个有成交日；价格缺失使标签缺失，不跨缺口前填标签。

`extra_same_boundary_embargo = 0`。若发现跨期scaler、未来递归状态或evaluation决定eligibility，应修复具体机制；不通过额外删除20日掩盖问题。角色隔离均相对当前fold：早期OOF样本在标签成熟后可成为后续年度训练样本，这正是expanding的定义。

实施期reader必须在I/O之前同时验证：canonical identity、角色、请求列、requested dates、effective dates和value ceiling。训练特征仅合法train signal dates，训练价格仅对应成熟标签所需端点；预测接口没有label参数，评价器在预测落盘后单独读成熟标签。禁止一次构造全物理horizon的Qlib handler或复用未绑定scope的全期缓存。

全物理日历、schema、lineage、文件hash等元数据允许读取，不能读取2024+值后再声称过滤了它们。Parquet底层row-group可能包含边界外字节，逻辑暴露仍必须列投影和predicate裁剪；记录requested/exposed范围，不承诺底层压缩块完全不含近期字节。

记录每次读取的角色、列、最早/最晚日期、行数、slice hash和parent hash。cache key至少绑定canonical id、fold、角色、精确日期集合、ordered features、pool identity、预处理/标签版本及代码hash。跨fold的纯因果原始特征可复用有界数据，fitted state不得共享。

V3 LightGBM路径：`inf -> NaN`并记录计数，保留部分NaN和有效0值；`use_missing=true, zero_as_missing=false`。不做全局complete-case、median填充、标准化或额外winsorization；不要变更其他模型和Forward的旧预处理。任何后来新增的fitted transform只能fit训练历史，属于独立配置版本。

## 6. Pool identity、fold eligibility与共同样本

协议支持以下四个角色，但**本计划不发布四个最终可训练名单**：

| 池角色 | 冻结前工作 | 禁止的简化 |
|---|---|---|
| Old / Baseline | 选择一个明确的历史factor identity版本，映射到canonical语义，记录发现区间及差异；建议以既有52因子身份作为审阅起点 | 不能把旧split的45/46/52列表随意求union或把旧bug值当基准 |
| Broad Candidate | 明确使用Primary `pass_count>=2`的494工作集，还是物理合格765全集；本轮建议494并写入名称 | 不能用同一个Broad名字指代两个集合 |
| Strict Consensus | 建议从冻结Primary 3/3名单生成；核对332项身份、controls是否另加、数据质量例外 | 不能自动把primary阈值或3/3规则改成表现更好的版本 |
| Human / Economic Diversified | 依据机制、窗口、量纲及V0.5.1未决项逐项形成书面名单 | 不能把聚类簇数、暂缓替代名单或零近似alias直接当最终池 |

五组经验精确重复目前只登记关系。本MVP默认保留身份；若池冻结时决定物理去重，需固定代表映射和列顺序并记为池定义的一部分，不能在年度中按后期相似度动态替换。

逐折eligibility先于读label值计算，只用合法训练日期的feature-only universe键轴；不能先按有标签样本过滤再算资格。建议V3-MVP采用最小、可解释规则：

- factor属于已冻结池且canonical research-usable；执行已登记的dated semantic availability；
- 训练中至少有2个不同交易日存在有限值，且全训练有限值至少有2个不同数值；全空和精确常数列剔除并留原因；
- 不迁移旧0.25 missing、765日、1,147,396样本和imputed variance阈值。不增加任意的有限率硬门槛，finite日期/样本/比例作为质量描述；上述2日/2值只证明最低可估计性，不是可靠性认证；
- 资格整年固定；当年后续才有效的列不在年中新增。若pool全空、所有列不可估计、整个预测日无数据或读入结构损坏，必须失败而非产生常数“成功”模型；
- effective-date不得由evaluation或后期coverage推导；Alpha101、PIT等按canonical因果语义，不能把schema start误认作所有股票的可用起点。

上述最小规则是本计划推荐的统一基准。若数据质量审计显示仍须更强门槛，须在结果出现前给出train-only依据、更新版本与审计记录，不以保留因子数或未来表现决定阈值。

为使比较只改变输入特征，训练target先在**canonical当日universe中有限标签样本**上做`rank(method=average,pct=True)-0.5`，不按池内finite mask重新排名。随后各池仅剔除自身全部特征为NaN的行，使用每日等权权重；记录实际fit keys差异。这样标签定义一致，但缺失导致的训练样本差异仍须披露。

预测不需要label；可预测分母为该日canonical universe全部键，整行无特征者留下缺失原因。评价分母为有限且已成熟标签的共同universe；各池报告自身覆盖，同时在四池共同有prediction的相同股票日期上计算paired IC。每日至少100对才计算Rank IC，沿用旧数值下限；缺失日保留，不静默删掉困难年份。覆盖低于95%标记实验不可胜出，门槛沿用旧研究配置；同时报告共同样本覆盖，避免intersection掩盖覆盖损失。

95%门槛具体作用于每个年度的prediction coverage：有限预测键数除以该年全部canonical universe预测键数；同时报告每日覆盖的等权均值及pooled键覆盖。2023年未成熟标签不减少预测分母，也不算标签故障。每年度任一池全期失效或共同样本无法形成可评分序列时，整体比较不得通过删除该年获得winner。

## 7. Frozen Model Contract

现有16候选表不直接作为incumbent。建议登记`v3_mvp_lgbm_structure01_100`：取旧表第一条低复杂度结构与最小已登记checkpoint，选择理由是工程基准与减少自由度，不是它在旧或新结果中表现最好。

| 项目 | 固定推荐值 |
|---|---|
| estimator | LightGBM 4.6.0，CPU，`gbdt`，regression |
| objective / trainer metric | regression / l2，l2仅训练诊断 |
| num_leaves / max_depth | 15 / 4 |
| min_data_in_leaf / learning_rate | 100 / 0.03 |
| lambda_l1 / lambda_l2 | 0 / 1 |
| feature_fraction | 0.8 |
| bagging_fraction / bagging_freq | 1.0 / 0 |
| num_boost_round | 100，单个终点，不扫描checkpoint |
| deterministic / force_col_wise | true / true |
| seed、feature_fraction_seed、bagging_seed、data_random_seed | 全部20260725 |
| num_threads / feature_pre_filter | 8 / false |
| early stopping / outer valid_sets | 禁止 / 不传入 |
| history / weights | expanding；daily-equal；无year decay |
| missing / dtype | 原生NaN；float64输入；按已固定列顺序 |

实施时冻结完整resolved参数（含max_bin等库默认值）、包版本、Qlib commit、环境/BLAS线程值、target规则、ordered features与参数hash，避免“代码默认”随升级变化。不同feature_fraction造成各池每棵树采样列数不同是同一配置下的固有行为，不据结果调整。

每折一次fit后只predict；不做outer train+OOF refit，不用OOF选boosting rounds。缓存/失败重试必须保持同一输入和配置；损坏输出不接续。后续如需超参数优化，另行规划inner walk-forward；本MVP暂缓Nested CV和CPCV。

## 8. OOF汇总与不确定性

输出唯一按`datetime,instrument`排序的pooled prediction stream，同一pool的键不得跨fold重复。首要模型证据为完整可评分日期上的mean daily Rank IC；报告非年化`mean/std(ddof=1)` ICIR，不能把它当作独立样本t值。另报覆盖、有效日/样本数、年度分布、最差年、负IC年数，以及B=2015–2017、C=2018–2020、D=2021–2023汇总。Pooled为每日等权，不是年度均值再等权，更不是平均annual Sharpe。

Paired delta先在共同股票样本计算同日IC差，再按共同日期聚合；报告每个challenger对Baseline的均值、中位年度差、胜出年数、最差年差及覆盖损失。协议层冻结这些统计口径；**不继承旧V2的3/5胜出规则，也不在本计划中设任意9年赢家门槛**。后续池实验必须在训练前登记胜出/平手/无结论规则与失败处理；若未登记，只能交付描述性比较，不能自动选winner。

20D相邻标签高度重叠，但旧市场平均标签的0.954不能直接当作每条新IC的参数。复用[dataset_design](../research_validation/dataset_design.py)的Bartlett/HAC、ESS及stationary-bootstrap思路，和[bootstrap](../research_validation/bootstrap.py)的gap-aware moving-block工具：

- 主不确定性：HAC带宽20；敏感性40，二者都报告，不能择优引用；对paired daily delta使用同样口径；
- moving-block长度20，敏感性40，1,000次，seed=20260909；各池paired比较共享相同抽样日期索引；
- 保留完整交易日轴及NaN缺口。旧HAC和stationary函数会`dropna`压缩日期，不能直接用于有缺口序列；最小适配按原交易日lag计算有效pair，或明确返回unavailable；
- gap-aware bootstrap不跨缺口，需报告不能提供完整块的短片段比例；若丢失支持导致估计目标变化则不发布总体CI。九个年份本身不宣称IID；年度离散和worst-year是独立描述层；
- 多池显著性若用于判断，冻结Baseline对照家族及校正方法；MVP推荐报告Holm校正，禁止逐次试到显著。区间不覆盖前序因子发现的selection bias。

经济证据分层处理：20D Top/Bottom分组和long-short spread可以作为标签诊断，但不是可融资、可成交NAV。真实turnover、成本后收益、回撤必须来自连续持仓的单一预注册portfolio evaluator，跨年度模型换新时持仓不重置；禁止把重叠20D return直接当daily P&L连乘。

优先复用[历史组合模块配置](../configs/historical_portfolio_backtest_v1.yaml)所对应的执行/记账代码，但不运行其6组合搜索、不直接复用其旧2021+市场缓存或固定税率假定。后续实验可预注册P01 Top50/5D作为唯一研究映射，需先验证2015–2023市场输入、历史交易约束、成本及估值边界。未完成时报告该层`unavailable/pending`，不妨碍纯模型OOF协议验收，也不能声称已有净值证据；Strategy V1/Forward不变。

## 9. Held-aside Recent Contract

2024–2026不是fresh/untouched OOS，因为已在项目其他研究被观察过。V3仍严格局部隔离：development中禁止近期returns、IC、feature importance、coverage和portfolio outcomes影响池、模型、窗口或阈值。

仅当开发结论（winner或no-winner）、候选身份、近期重训与资格规则、报告模板和代码hash冻结，且另有近期重放授权后，打开一次独立diagnostic run。No-winner时预登记只重放Baseline；不能临时选择最好看的challenger。

建议后续近期合同沿用annual expanding、2024/2025/2026年初各fit一次，标签在当年边界前成熟；诊断运行中的前一年近期数据可以按预先冻结规则进入下一年训练，但其outcomes不得反馈修改规则。需在解锁前将这一自动更新语义写明，不能把“允许读近期”解释成可重新选池。近期终端成熟边界为2026-05-11 signal / 2026-06-09 label_end。

一次重放可包含保持同hash的失败恢复，不允许看结果后改配置重来。任何后验修改登记新研究并承认该recent窗口已消耗。真正前瞻确认仍走独立Forward Track，不自动启动Strategy V2。

## 10. 计算预算与执行方式

主实验fit数为`9 folds × P pools × 1 model`。四池全部冻结后为**36次正式fit**；若事前为所有四池启用4Y sensitivity，再加36次，共72次。协议验收的小型合成训练和有界资源canary另记，不计为额外参数候选。近期待解锁时如仅Baseline加一个winner、三个年度，最多另加6次fit，不在本轮36次预算内。

旧[8T计时证据](../reports/performance_execution_v1/full_mt_qualification_v1/runs.csv)中，三个完整工作负载每次约116、201、1,088秒，最高RSS约10GiB；这些含旧池、旧训练期和候选工作，**不是V3单次100轮的耗时**。它只支持复用8T，不支持承诺36次总时长。

按本次键数，最大fold的float64训练特征原始数组约为`6,114,684 × F × 8`字节：F=494约22.5GiB，F=765约34.9GiB，尚未包括DataFrame、bins、labels、临时复制及模型。一次只运行一个8T fit，按年/月投影数据、复用已校验的磁盘中间结果；不要启动8个各自8T的大矩阵fit。

在未实测前，为四池36次fit预留**一个24–48小时执行窗口**，这是调度预留而非测量预测。实施P2对首折与最大fold各做一次既定配置资源canary，记录cold/warm读取、构造bins、fit、predict、落盘与RSS。用`T_total = Σ(T_read + T_dataset + T_fit + T_predict + T_write) + T_aggregate`更新估计；分配重试和I/O余量，不以旧468秒平均值直接乘36。

资源canary不得展示验证IC、收益或feature importance；只检查输入合法性、预测shape/finite与资源。测算超内存时优先减少复制、顺序运行与使用已有spool方式，不能为了快而缩短历史或按表现删列。新数据1T/8T只做小型同输入确定性核对，不重新开启性能工程研究。

长任务在用户自己的PowerShell运行。实施交付必须提供确实存在且已验证的命令、独立run-id、日志、状态文件、失败恢复说明及运行预估；目前没有V3 runner，因此本计划不提供虚构可执行命令。

## 11. 分阶段实施与交付物

以下路径均为**拟新增**，尚未实现。一般实现授权只推进P0–P2；真实四池竞争与近期重放分别按下表条件启动，防止将“按计划实施”误解为同时解锁所有研究阶段。

| 阶段 | 工作及拟交付 | 验收/停止条件 |
|---|---|---|
| P0：时间协议 | `configs/research_protocol_v3_mvp.yaml`、`research_validation/research_protocol_v3.py`、`scripts/run_research_protocol_v3_mvp.py`；输出9折表、逐日assignments、purged dates、label interval、边界receipt | 重现本计划日期；无值读取；不修改V2 |
| P1：canonical输入与资格审计 | `model_research/long_history_inputs.py`；keys、成熟有限label数、universe、逐折feature-only资格与effective-date审计；明示每个尚未冻结池 | 训练reader无法访问OOF、预测reader无法读label、所有开发值≤2023-12-29；各池名单不明确时不能声称pool-ready |
| P2：固定模型接入与验收 | `model_research/long_history_walk_forward.py`、单一resolved model配置、合成测试、获实施授权后的有界资源canary；`reports/research_protocol_v3_mvp/REPORT.md`、实施进度与资源估计 | 无outer feedback；完成finite样本/空列/缺口/资源审计后交付`protocol_ready`或明确blocker；停止供审阅，未运行36次竞争 |
| P3：独立feature-pool MVP | 四个已冻结池、选择规则、可选sliding开关、预算和实验授权；36次fit、pooled预测、年度/Era/paired/HAC报告及可用的经济诊断 | 四池采用同fold/model/metric；冻结winner或no-winner，列出所有失败；停止，不自动读recent |
| P4：独立近期诊断 | 先冻结全部重放规则并获得授权，再一次运行2024–2026 | 不回调development选择，不改Strategy V1，不启动Strategy V2 |

小型tracked报告保存fold表、count audit、配置/输入hash、eligibility汇总、access摘要和检查结论；大型keys、模型、预测、逐样本labels留在`outputs/research_protocol_v3_mvp/<run_id>/`或后续独立pool实验目录。版本已发布不可覆盖；manifest足以绑定输入/输出，不叠加新的registry体系。

## 12. 关键测试与训练前blockers

测试重点为研究语义，不以测试数量作为交付目标：

1. 实际节假日及合成日历上，train label_end等于E时必须purge；严格小于E时保留；原始calendar缺失、乱序或重复失败。
2. 九个年度预测覆盖与无重复；2023年末21日只预测不评分；跨年评价标签不迫使每年丢21个预测日；recent成熟日期准确。
3. 请求2024+开发值在reader调用之前失败；模拟当前fold的evaluation/近期文件不可访问时fit仍完成；mutation改变当前fold的OOF标签不得改变该fold训练输入、资格、参数、模型hash和预测。其标签合法进入后续年度训练时，后续模型允许变化。
4. 后期coverage变化不改变早期eligibility；池列序/键轴变化失败；新列年内不得加入；NaN/零值语义和pool-independent target rank符合合同。
5. 不同池的日标签rank一致，any-finite只影响fit mask；共同样本paired评价可核算；整日数据缺失和不足100对明确失败或不可评分。
6. annual model freeze、无valid_sets/early stopping/选参后refit；按月预测与整年预测结果一致；缓存错误scope及损坏分片不能复用。
7. pooled IC的日期加权正确；缺口不压缩为相邻时间；HAC/bootstrap用合成相关序列核对；经济回测如启用需跨年持仓与交易成本算术测试。

训练前需解决的真实blockers：

- 四池准确名单、来源与未决语义如何处理；Baseline不能只写“旧池”，Human池不能空缺却声称四池就绪。
- 首折及其后每折的finite标签数量、日最低pair、train-only可用feature与missingness审计；本次仅有日历/键轴上界。
- 765资格含旧物理审计背景，不能把其后期质量判断反向解释为早期已知；各fold实际值与dated lineage仍须核验。
- V3输入适配与target/NaN路径尚未实现；8T历史资格不代替新路径资源/确定性验证。
- 若要公布成本后净值，需补历史market/执行输入合同；不以未经验证的组合层阻塞纯预测协议，也不把净值标成已交付。

这些阻碍不会通过改成更有利的年份、扫描sliding窗口、读取近期coverage或调标签horizon解决。日期方案本身已核验成立；正式`protocol_ready`与`pool_experiment_ready`必须分开声明。

## 13. 预研依据与采用边界

本项目[既有validation study](../reports/historical_dataset_validation_design_v1/REPORT.md)是主要依据：40日标签ESS约2.6，支持120–252交易日的长区间数量级。新canonical已扩展历史，因此本计划采用九个自然年度，而非机械继承旧研究4–6环境建议。年度设计不保证九年独立，也不保证任何池获胜。

外部来源于2026-09-09核查：

- [Gu、Kelly、Xiu论文入口](https://www.nber.org/papers/w25398)确认文献身份；本文不把它解释为对本项目5年初始窗口的最优性证明。
- [Machine learning in the Chinese stock market](https://www.sciencedirect.com/science/article/pii/S0304405X21003743)明确采用按时间先后分离训练、验证、测试，年度refit、expanding训练和后续12个月测试。它支持年度设计的实践可行性，不直接验证本项目20D daily标签或取消inner tuning后的具体模型。
- [LightGBM Missing Value Handle](https://lightgbm.readthedocs.io/en/v4.6.0/Advanced-Topics.html)说明原生NaN与zero_as_missing语义；本项目仍固定已资格版本4.6.0，不追随stable网页版本自动升级。

预研中未提供完整题名/DOI的2026年5Y rolling、leakage文章及2024年CPCV比较，不作为本计划参数冻结的必要证据；不用未核对的文献结论宣称5Y、4Y或annual最优。Nested CV、CPCV、cadence sweep、多horizon、SHAP、feature-importance selection、year decay和组合优化均暂缓。

## 14. 本次规划审计的可复核记录

仅修改文档；临时机器计算记录位于`tmp/research_protocol_v3_plan_audit.json`，不作为长期依赖。正式实现P0须重新物化并核对本计划表格。

| 输入 | SHA-256 |
|---|---|
| provider calendars/day.txt | `fd7cf1436bbc2d497171aaae139c2deedaf649c2d6b20b66c8e1a544de305b60` |
| canonical current/manifest.json | `0481785bf512d3f1d04202badae900a41cc0f49d7fb4b50a9219a331a527b837` |
| canonical current/partition_manifest.csv | `ef7bc044a34904159733a7f4540f47c87ce3191a8224757cc2757167cd0cd9af` |
| canonical current/factor_lineage.csv | `1d655cd0b099fdfd4317ec295821f897266ef42d3a0b7e6047e21348d461460b` |

读取分区范围全部≤2023-12-29，仅keys投影；canonical dataset identity通过现有`canonical_dataset_identity`函数重算匹配。本次未重验所有大型分区的物理文件hash，未读取feature/label/price数值，未重跑Primary或Consolidation。报告中的样本可用性限制因此保留。正文列出的拟新增模块、configs与runner不表示已经实现或已获得正式competition授权。
