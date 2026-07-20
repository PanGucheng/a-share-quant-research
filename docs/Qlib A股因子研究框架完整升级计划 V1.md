# Qlib A股因子研究框架完整升级计划 V1

> 本文件是升级目标与阶段门禁总纲。可直接执行的任务编号、依赖关系、预计文件、验证顺序和失败停止条件见 [Qlib A股因子研究框架详细实施路线图 V1](./FACTOR_VALIDATION_ROADMAP_V1.md)。
>
> 2026-07-13 增补：[V1.1 门禁、Profile 与 Lineage 硬化计划](./FACTOR_VALIDATION_HARDENING_V1_1.md) 修正阶段 5、8、10、11 的收尾语义。涉及 pre/post-model diagnostics、能力门禁、Profile 和 lineage 时，以 V1.1 为准。
>
> 2026-07-20 进度：PR #1 已合并并标记 `v0.1-factor-validation-foundation`；PR #2 Qlib Exchange integration 已完成实现与本地验收。三个核心 execution readiness 为 true，完整 reference readiness 因 PIT universe/权威历史 tradability 缺口保持 false。下一步严格进入 50–100 因子 full-research 试运行；仍不得跳到 669 因子或模型训练。实施证据见 [Qlib Exchange Integration V1](./QLIB_EXCHANGE_INTEGRATION_V1.md)。

## 一、项目背景

仓库：

```text
https://github.com/PanGucheng/qlib-baseline
```

本地环境：

```text
项目目录：E:\qlib_prj\qlib_baseline
Python：E:\anaconda_envs\qlib_env\python.exe
Qlib源码：E:\qlib_prj\qlib_clone
Qlib数据：E:\qlib_prj\qlib_data\cn_data_community_20260609_derived
```

当前项目已经具备：

* Qlib LightGBM + Alpha158 基线；
* 数据质量检查；
* 可交易性标签；
* Alpha158、Alpha101、Alpha360、TA 多来源因子；
* IC、Rank IC、ICIR、分组收益、换手率、覆盖率、相关性；
* 批量评价、promotion/holdout、screening、judgement；
* 主研究区间和 recent OOS 对比；
* 流动性暴露归因和残差化实验。

本计划不再继续扩张因子数量，而是把项目升级为：

> 严格时点化、避免未来数据泄漏、控制多重检验、支持滚动验证、自动因子去重、考虑A股交易约束的多因子研究框架。

---

# 二、最终目标

完成以下完整流水线：

```text
原始Qlib数据
→ 数据质量和可交易性过滤
→ 时点化动态股票池
→ 因子批量评价
→ Purged Walk-Forward时间验证
→ Block Bootstrap与FDR修正
→ 跨窗口稳定性评价
→ 因子相关性聚类去重
→ 多因子组合构建
→ A股交易约束回测
→ 成本、容量和压力测试
→ 可选机器学习模型
→ 最终研究候选池
```

最终系统必须能够回答：

1. 因子是否在多个历史窗口中持续有效；
2. 因子是否只是偶然通过大量检验；
3. 因子是否依赖流动性、规模或行业暴露；
4. 因子是否与其他候选高度重复；
5. 多因子组合扣除真实成本后是否仍有效；
6. 结果是否能在严格未参与筛选的测试窗口保持；
7. 所有结果是否可复现、可审计、可追溯。

---

# 三、总体执行原则

## 3.1 不得破坏现有链路

不得替换或绕过：

```text
Qlib baseline
data_quality
tradability
factor_evaluation_v4
batch runner
multi_source_screening
multi_source_judgement
现有candidate pool
```

新模块应作为现有输出的下游消费者。

## 3.2 不做巨型重构

每个阶段必须：

* 独立实现；
* 独立配置；
* 独立输出目录；
* 独立验证脚本；
* 独立审计报告；
* 不改变现有默认结果；
* 通过验收后才能成为新的 downstream default。

## 3.3 不继续扩张因子源

完成本计划前暂停：

* 新TA库接入；
* 新Alpha公式库接入；
* 自动因子生成；
* 遗传规划；
* 深度学习因子挖掘。

当前因子数量已经足够验证研究体系。

## 3.4 第三方项目使用原则

直接依赖：

```text
microsoft/qlib
baobach/mlfinpy
statsmodels
pandera
```

条件性依赖：

```text
Riskfolio-Lib
AKShare
```

只作为设计参考，不复制源码：

```text
ricequant/rqalpha
```

暂缓接入：

```text
cvxportfolio
vectorbt
```

不要把第三方项目完整源码复制进仓库。优先使用正常 Python 依赖和薄适配层。

## 3.5 许可证边界

* mlfinpy：MIT，仅作时间区间 purge 语义参考；因其 Python/NumPy 约束，不作为仓库依赖；
* statsmodels：宽松许可证，可正常依赖；
* Riskfolio-Lib：BSD 3-Clause，可正常依赖；
* RQAlpha：存在非商业限制，只能研究其规则语义和测试思路，不复制源码；
* cvxportfolio：GPL，只能作为隔离的可选模块；
* 不复制无明确许可证项目代码。

## 3.6 输出管理

大型中间文件继续放入：

```text
tmp/
outputs/*/runtime/
```

并保持 Git 忽略。

Git 只保存：

* 配置；
* compact summary；
* manifest；
* contract status；
* audit report；
* 少量候选表；
* 测试代码。

---

# 四、推荐新增目录

在不破坏现有结构的前提下增加：

```text
research_validation/
    schemas.py
    point_in_time.py
    purged_split.py
    bootstrap.py
    multiple_testing.py
    rolling_evaluation.py
    stability.py

universes/
    point_in_time_universe.py
    interval_writer.py
    universe_audit.py

factor_research/
    factor_similarity.py
    factor_clustering.py
    representative_selection.py

portfolio/
    score_construction.py
    portfolio_constraints.py
    execution_assumptions.py
    cost_model.py
    capacity.py

data_adapters/
    akshare_snapshot.py
    point_in_time_fields.py

tests/
    test_point_in_time_universe.py
    test_purged_split.py
    test_no_future_leakage.py
    test_multiple_testing.py
    test_factor_clustering.py
    test_portfolio_accounting.py
    test_trade_constraints.py
    test_output_schemas.py
```

目录名称可根据现有项目风格调整，但职责边界必须保持清晰。

---

# 五、阶段0：现状冻结与兼容性审计

## 目标

在修改任何研究逻辑前，冻结当前基线，确定依赖和输出兼容性。

## 任务

1. 阅读：

```text
README.md
README.zh-CN.md
docs/PROJECT_CONTEXT_SUMMARY.md
docs/DOC_INDEX.md
docs/FACTOR_RESEARCH_TOOLCHAIN_READINESS_V1.md
docs/LIQUIDITY_RESIDUALIZED_FACTOR_EVALUATION_V1.md
```

2. 记录当前关键结果：

```text
total runnable factors
screening rows
judgement candidates
Alpha158 candidates
new-source probes
recent OOS results
readiness状态
V3.39 blocked原因
```

3. 新建：

```text
docs/FACTOR_VALIDATION_ROADMAP_V1.md
outputs/factor_validation_baseline_v1/current/
```

4. 输出：

```text
baseline_artifact_manifest.csv
baseline_metric_snapshot.csv
dependency_compatibility.csv
baseline_contract_status.csv
baseline_audit_report.md
```

5. 检查当前 Python 版本和以下包的兼容性：

```text
mlfinpy
statsmodels
pandera
Riskfolio-Lib
scipy
scikit-learn
```

6. 将核心依赖和可选依赖分开：

```text
requirements-research-validation.txt
requirements-optional-portfolio.txt
```

## 禁止事项

* 不修改任何现有因子结果；
* 不改变 candidate pool；
* 不运行新的策略优化；
* 不直接升级整个环境中的全部包；
* 不因为依赖冲突而重建 Qlib 环境。

## 验收标准

```text
baseline outputs可读取
readiness仍为ready
现有验证脚本没有新增失败
所有依赖均有许可证记录
可选依赖不会影响核心环境
```

---

# 六、阶段1：DataFrame契约与防泄漏基础设施

## 目标

把目前分散在脚本中的隐式要求变成可执行的数据契约。

## 开源复用

使用 Pandera，不自行设计新的 DataFrame schema 框架。

## 需要定义的 Schema

### Factor Frame

必须包含：

```text
datetime
instrument
factor columns
```

检查：

* `(datetime, instrument)` 唯一；
* datetime 可转换且排序可恢复；
* factor 列为数值；
* 不允许正负无穷；
* 重复因子名禁止；
* 覆盖率范围合法。

### Label Frame

必须包含：

```text
feature_time
label_start_time
label_end_time
instrument
label
```

检查：

```text
feature_time < label_start_time <= label_end_time
```

### Tradability Frame

检查：

```text
can_buy和can_sell为布尔值
tradability_score处于合法范围
liquidity_bucket属于规定枚举
```

### Universe Interval

必须包含：

```text
instrument
start_date
end_date
selection_date
effective_date
selection_reason
```

检查：

```text
selection_date < effective_date
start_date <= end_date
同一股票有效区间不得非法重叠
```

### Screening与Judgement输出

检查：

* 因子名唯一；
* role 属于合法枚举；
* coverage 和 missing_rate 在 `[0,1]`；
* holdout 不得进入 downstream default；
* probe 不得被误标为默认交易信号。

## 输出

```text
outputs/research_data_contracts_v1/current/
    schema_inventory.csv
    schema_validation_results.csv
    contract_status.csv
    schema_report.md
```

## 验收标准

* 所有现有核心 compact outputs 可以通过或明确记录兼容性例外；
* synthetic bad cases 必须被准确拒绝；
* Schema 不得修改原始 DataFrame；
* Schema 校验可以单独在 CI 中运行。

---

# 七、阶段2：时点化动态股票池

## 目标

替换当前基于固定历史区间选出的静态 liquid2000 研究股票池。

## 开源复用

复用 Qlib instruments 的：

```text
instrument
start_date
end_date
```

区间机制。

不要重新设计市场加载逻辑。

## 股票池生成规则

实现配置化滚动股票池，默认建议：

```text
更新频率：每月
流动性回看：过去250个交易日
最低有效交易日：180
候选范围：当时已经上市的沪深A股
最低上市年龄：120个交易日
选取方式：成交额排名前N或流动性分位数
生效时间：选池日期后的下一个交易日
```

所有参数必须进入 YAML，不得硬编码。

## 必须避免

在日期 `t` 构建股票池时，只能使用：

```text
<= t 的数据
```

不能使用：

* 未来成交额；
* 未来是否退市；
* 当前最新行业标签回填历史；
* 当前股票状态回填历史；
* 整个研究期统计值。

## 输出

```text
outputs/point_in_time_universe_v1/<profile>/
    universe_membership_snapshots.csv
    universe_selection_metrics.csv
    universe_intervals.csv
    qlib_instruments.txt
    universe_change_log.csv
    point_in_time_audit.csv
    contract_status.csv
    universe_report.md
```

## 必须实现的测试

1. 某个月的选池结果不因之后的数据变化；
2. 新上市股票只能在最低上市年龄后进入；
3. 退市或长期无数据股票能结束有效区间；
4. 连续相同的月度成员应合并为一个区间；
5. 选池日期和生效日期不能相同；
6. 打乱输入行顺序不影响结果；
7. Qlib 能正常读取生成的 instruments 文件。

## 验收标准

```text
point_in_time_audit = pass
future_data_reference_count = 0
invalid_interval_count = 0
qlib_instruments_load = pass
```

在本阶段通过前，不得用动态股票池重新评价全部因子。

---

# 八、阶段3：Purged Walk-Forward时间划分

## 目标

建立适用于未来收益标签的严格训练、验证和测试划分。

## 开源复用

参考 mlfinpy 的以下语义，但使用仓库内自主实现：

```text
PurgedKFold
ml_get_train_times
```

不要直接使用当前 CombinatorialPurgedKFold，除非先针对 embargo 行为完成独立修复和测试。

## 关键设计

你的数据是：

```text
datetime × instrument
```

因此划分必须首先在“唯一交易日”层面完成，而不是直接对所有股票行做普通 KFold。

流程：

```text
交易日序列
→ 定义训练、验证、测试日期
→ 根据标签覆盖区间执行purge
→ 应用embargo
→ 再展开到对应日期的全部股票
```

## 配置参数

```text
split_mode: rolling 或 expanding
train_years
validation_months
test_months
step_months
label_horizon
execution_lag
embargo_trading_days
minimum_train_dates
minimum_validation_dates
minimum_test_dates
```

label horizon 和 embargo 不得写死为20，必须从配置或 label metadata 推导。

## 输出

```text
outputs/purged_walk_forward_v1/<profile>/
    split_manifest.csv
    split_date_ranges.csv
    purged_dates.csv
    embargoed_dates.csv
    sample_counts.csv
    leakage_audit.csv
    contract_status.csv
    purged_walk_forward_report.md
```

## 必须实现的测试

1. 任意训练标签区间不得与测试区间相交；
2. embargo 日期不得进入训练；
3. 同一天所有股票必须进入同一 fold；
4. 输入行排序不影响划分；
5. 重叠标签被正确 purge；
6. 20日标签与1日标签得到不同 purge 范围；
7. 空窗口和样本不足必须明确失败。

## 验收标准

```text
train_test_label_overlap = 0
same_date_cross_fold_count = 0
embargo_violation_count = 0
split_contract = pass
```

---

# 九、阶段4：Block Bootstrap与多重检验控制

## 目标

防止从数百个因子和多个指标中筛选出偶然的“优秀因子”。

## 开源复用

* p-value 修正使用 `statsmodels.stats.multitest.multipletests`；
* 不自行实现 Benjamini–Hochberg 或 Benjamini–Yekutieli；
* bootstrap 优先使用兼容环境中的成熟实现；
* 若必须封装 block bootstrap，只实现薄适配并使用充分的合成测试。

## 统计对象

优先针对以下时间序列计算统计显著性：

```text
daily IC
daily Rank IC
factor long-short return
```

不能把每日样本视为完全独立，应采用时间块 bootstrap。

## 检验族定义

默认检验族：

```text
source_family
× label_horizon
× research_window
× preprocessing_variant
```

不得把所有来源、标签和研究窗口混成一个无法解释的检验族。

## 输出字段

```text
factor
test_family
metric
raw_statistic
bootstrap_standard_error
raw_p_value
fdr_bh_q_value
fdr_by_q_value
fdr_bh_pass
fdr_by_pass
bootstrap_samples
block_length
random_seed
```

## 输出目录

```text
outputs/factor_multiple_testing_v1/<profile>/
    factor_hypothesis_tests.csv
    test_family_summary.csv
    fdr_results.csv
    rejected_hypotheses.csv
    contract_status.csv
    multiple_testing_report.md
```

## 必须实现的测试

1. 纯随机因子不应大量通过 FDR；
2. 构造的稳定信号因子应能通过；
3. 调换因子顺序不影响 q-value 对应关系；
4. 固定随机种子结果可复现；
5. NaN p-value 不得被错误晋级；
6. 每个结果必须记录所属 test family。

## 验收标准

```text
all_selected_factors_have_q_value = true
missing_test_family_count = 0
null_simulation_false_discovery_rate <= configured_limit
multiple_testing_contract = pass
```

---

# 十、阶段5：滚动评价与因子稳定性看板

## 目标

将“某个固定区间表现好”升级为“多个历史窗口中持续有效”。

## 核心原则

因子选择只能使用：

```text
train
validation
```

test 窗口只能用于冻结策略后的最终评价。

选择函数中禁止读取 test 指标。

## 工作流程

每个 walk-forward split 执行：

```text
读取时点股票池
→ 应用data_quality和tradability
→ 运行现有V4评价
→ 生成train指标
→ 生成validation指标
→ 根据预定义规则决定是否入选
→ 冻结因子方向和参数
→ 在test窗口评价
```

尽量复用现有 V4 metric index，不重复计算无必要的大型 factor frame。

## 稳定性指标

每个因子输出：

```text
window_count
eligible_window_count
selected_window_count
selection_frequency
positive_ic_window_ratio
direction_agreement_ratio
median_train_ic
median_validation_ic
median_test_ic
worst_test_ic
median_oos_degradation
maximum_oos_degradation
median_turnover
worst_turnover
fdr_pass_frequency
coverage_min
coverage_median
```

## 稳定性角色

建议角色：

```text
stable_core
conditional_signal
risk_control
monitor
reject
holdout
```

角色规则必须配置化并记录原因。

## 输出

```text
outputs/factor_rolling_stability_v1/<profile>/
    factor_window_metrics.csv
    factor_selection_history.csv
    factor_direction_history.csv
    factor_oos_degradation.csv
    factor_stability_board.csv
    stability_role_summary.csv
    contract_status.csv
    stability_report.md
```

## 验收标准

```text
test_metrics_used_in_selection = false
all_selected_factors_have_multiple_windows = true
all_selected_factors_have_fdr_result = true
stability_contract = pass
```

本阶段完成后，旧 candidate pool 继续保留，但新的 stable pool 可以作为实验性下游输入。

---

# 十一、阶段6：因子相关性聚类与代表因子选择

## 目标

避免多个高度相似因子在组合中重复投票。

## 开源复用

优先检查 Riskfolio-Lib 与当前环境兼容性。

兼容时复用其层次聚类能力；不兼容时使用 SciPy 已有聚类实现，不自行编写聚类算法。

## 构建两种相似度

### 暴露相似度

```text
每日计算因子间截面Spearman相关
→ 对日期进行稳健汇总
```

### 表现相似度

```text
因子daily IC时间序列相关
或
因子long-short return时间序列相关
```

最终相似度应同时保留，不要只依赖一种相关矩阵。

## 聚类后代表因子选择

同一簇内优先保留：

1. test/OOS 稳定性更高；
2. selection frequency 更高；
3. FDR 通过频率更高；
4. 换手率更低；
5. coverage 更高；
6. 流动性暴露更低；
7. 公式更简单、经济含义更清楚。

## 输出

```text
outputs/factor_clustering_v1/<profile>/
    exposure_correlation_matrix.csv
    performance_correlation_matrix.csv
    factor_distance_matrix.csv
    factor_clusters.csv
    cluster_representatives.csv
    excluded_redundant_factors.csv
    cluster_stability.csv
    contract_status.csv
    clustering_report.md
```

## 验收标准

```text
every_selected_factor_has_cluster = true
every_cluster_has_representative = true
default_combination_duplicate_cluster_votes = 0
clustering_contract = pass
```

---

# 十二、阶段7：透明的多因子组合基线

## 目标

先使用简单、透明、可解释的方法组合稳定因子，不立即使用复杂机器学习。

## 必须保留的基线

```text
equal_directional_zscore
```

作为原始对照组。

## 新增组合方式

### Cluster Equal Weight

```text
每个因子簇总权重相等
簇内代表因子等权
```

### Stability Weight

权重只使用历史窗口数据，参考：

```text
selection_frequency
direction_agreement
FDR通过频率
OOS稳定性
turnover惩罚
redundancy惩罚
```

### Regularized Linear

在后续子阶段加入：

```text
Ridge
Elastic Net
```

暂不使用 LightGBM 作为第一版组合器。

## 组合约束

```text
单因子最大权重
单因子簇最大权重
最少有效因子数
单日缺失因子处理
score clipping
权重归一化
方向冻结
```

所有权重只能使用当时之前的数据生成。

## 输出

```text
outputs/factor_score_construction_v1/<profile>/
    score_method_manifest.csv
    factor_weights_by_window.csv
    daily_factor_component_count.csv
    composite_scores.parquet
    score_diagnostics.csv
    contract_status.csv
    score_construction_report.md
```

## 验收标准

```text
future_weight_reference_count = 0
same_cluster_double_counting = 0
weight_sum_error <= tolerance
minimum_component_policy_pass = true
```

---

# 十三、阶段8：A股交易约束与成本模型

## 目标

将当前固定 bps 的 portfolio smoke 升级为更接近真实A股执行的回测。

## 开源复用

使用 Qlib Exchange 作为实际回测引擎。

参考 RQAlpha 对以下规则的处理方式，但不得复制其源码：

* 买卖成本分离；
* 卖出侧税费；
* 最低佣金；
* 涨跌停拒单；
* 停牌拒单；
* 成交量参与率；
* 整手；
* 部分成交；
* 滑点；
* 可卖数量限制。

## 第一版必须支持

```text
100股交易单位
最低佣金
买入成本
卖出成本
卖出侧税费
涨停不可买
跌停不可卖
停牌不可交易
无成交量不可交易
单日成交量参与率上限
部分成交
未成交订单记录
```

## 成本模型

保留固定成本场景作为对照：

```text
5 bps
10 bps
20 bps
30 bps
```

增加流动性相关成本：

```text
base_cost
+ volatility_component
+ participation_rate_component
+ inverse_liquidity_component
```

第一版不追求复杂市场微观结构，但不同流动性股票不能长期使用完全相同的滑点。

## T+1处理

明确记录策略是否可能发生同日买卖。

对于日频长仓策略至少保证：

* 信号时间早于执行时间；
* 当日新买持仓不能在同日卖出；
* 调仓顺序不会产生虚构资金；
* 被涨跌停阻断的持仓正确延续。

## 容量分析

输出：

```text
strategy_capital
order_value
daily_amount
participation_rate
capacity_multiple
estimated_impact_cost
```

## 输出

```text
outputs/a_share_execution_v1/<profile>/
    order_intents.csv
    executed_orders.csv
    rejected_orders.csv
    partial_fills.csv
    transaction_costs.csv
    daily_turnover.csv
    capacity_diagnostics.csv
    execution_summary.csv
    contract_status.csv
    execution_report.md
```

## 必须实现的合成测试

1. 涨停买单被拒绝；
2. 跌停卖单被拒绝；
3. 停牌订单不成交；
4. 101股订单按交易单位处理；
5. 成交量不足产生部分成交；
6. 最低佣金正确；
7. 卖出侧税费不在买入侧重复收取；
8. 未成交持仓不会凭空消失；
9. 组合资产守恒；
10. 无未来价格成交。

## 验收标准

```text
cash_conservation_error <= tolerance
position_conservation_error <= tolerance
invalid_trade_count = 0
future_price_execution_count = 0
execution_contract = pass
```

---

# 十四、阶段9：行业与市值时点数据接入

## 目标

为规模和行业中性化建立可靠的数据基础。

当前 provider 缺少：

```text
market cap
industry
Barra exposures
```

所以不得直接假装已有完整风险模型。

## 开源复用

使用 AKShare 作为数据采集适配器之一，但不能把“当前接口返回值”直接填入历史回测。

## 数据契约

所有外部字段至少包含：

```text
instrument
field_name
field_value
source
source_record_date
announcement_date
effective_from
effective_to
collected_at
raw_snapshot_id
is_point_in_time_valid
```

## 第一阶段

先实现向前采集：

```text
每日或每周保存原始快照
记录采集时间
保存来源信息
生成有效期
```

## 历史回填

只有以下情况允许进入历史研究：

* 数据本身提供历史日期；
* 能从公告或财报发布日期恢复；
* 有明确 effective date；
* 可以证明在研究日期已经公开。

仅提供当前快照的数据不能回填到过去。

## 后续中性化

数据 contract 通过后，再实现：

```text
size neutralization
industry neutralization
industry + size neutralization
```

继续保留：

```text
raw factor
liquidity residualized factor
size residualized factor
industry-size residualized factor
```

不得覆盖原始因子。

## 输出

```text
outputs/external_exposure_data_v1/current/
    data_source_inventory.csv
    raw_snapshot_manifest.csv
    point_in_time_field_table.parquet
    field_coverage.csv
    point_in_time_audit.csv
    contract_status.csv
    exposure_data_report.md
```

## 验收标准

```text
historical_current_snapshot_backfill_count = 0
missing_effective_date_count = 0
untraceable_source_count = 0
point_in_time_exposure_contract = pass
```

---

# 十五、阶段10：最终组合诊断与压力测试

## 目标

比较不同因子筛选和组合方法是否真正改善 OOS 表现。

## 必须比较

模型训练前的 `pre_model_diagnostics` 必须比较：

```text
原Alpha158等权组合
旧candidate pool等权组合
stable factors等权组合
cluster equal组合
stability weighted组合
```

`regularized linear`、Ridge、Elastic Net 和 LightGBM 属于模型产出，只能在模型训练完成后的 `post_model_diagnostics` 中加入。`pre_model_diagnostics` 不得要求任何模型产物，避免形成“诊断要求模型、模型又要求诊断先通过”的循环依赖。

所有组合必须共享：

* 相同动态股票池；
* 相同时间划分；
* 相同交易约束；
* 相同成本模型；
* 相同基准；
* 相同资金规模；
* 相同调仓频率。

## 压力测试

至少包括：

```text
不同TopK
不同调仓周期
不同交易成本
不同资金规模
不同流动性阈值
不同股票池规模
剔除最强单因子
剔除最强因子簇
熊市区间
震荡区间
高波动区间
```

## 重点指标

```text
net annualized excess
net excess IR
maximum drawdown
turnover
win-window ratio
worst-window return
OOS degradation
capacity
factor concentration
cluster concentration
liquidity bucket exposure
```

## 输出

```text
outputs/final_portfolio_diagnostics_v1/<profile>/
    native_period_method_comparison.csv
    common_period_method_comparison.csv
    rolling_performance.csv
    regime_performance.csv
    cost_sensitivity.csv
    capacity_sensitivity.csv
    ablation_results.csv
    exposure_diagnostics.csv
    contract_status.csv
    final_portfolio_report.md
```

兼容入口可以暂时保留 `final_portfolio_diagnostics_v1` 名称，但 contract 必须明确它当前对应 `pre_model_diagnostics`。模型比较和方法排名只能使用所有 required methods 的公共有效日期；native-period 结果只用于诊断展示。

## 晋级条件

不能只按某一个最高收益选择方法。

最终研究候选至少要求：

```text
多数OOS窗口为正
最差窗口可接受
扣除较高成本后仍未明显失效
换手率未失控
容量未严重不足
不是由单一因子或单一簇贡献全部收益
无明显流动性代理依赖
```

---

# 十六、阶段11：机器学习模型比较

## 开始条件

只有在以下全部通过后才能开始：

```text
point-in-time universe pass
purged walk-forward pass
multiple testing pass
stability board pass
factor clustering pass
execution contract pass
pre-model diagnostics pass
full-research profile and lineage pass
```

历史行业/市值 PIT 不是 core model 的通用前置，只阻塞需要该数据的 `historical_exposure_model_ready`；流动性残差化 contract 只阻塞 `liquidity_residualized_model_ready`。任何模型训练仍须由独立 PR 显式启动。

## 模型顺序

按以下顺序逐步增加复杂度：

```text
Equal Weight
Stability Weight
Ridge
Elastic Net
LightGBM
```

暂不优先使用：

```text
深度神经网络
Transformer
强化学习
遗传规划
自动因子生成
```

## 模型输入

只能使用：

```text
stable_core
通过FDR的conditional_signal
cluster representatives
合法的risk_control因子
```

不得把全部数百个因子直接塞入模型。

## 训练要求

* 使用同一 Purged Walk-Forward；
* 超参数只能通过 train/validation 选择；
* test 不参与调参；
* 保存每个窗口的模型参数；
* 保存特征重要性；
* 检查特征重要性稳定性；
* 与简单组合进行公平比较。

## 模型晋级标准

复杂模型只有同时满足以下条件才能晋级：

```text
OOS净表现优于简单基线
多个窗口稳定改善
换手率和成本没有显著恶化
特征重要性不过度集中
结果不是来自单个特殊时期
```

否则保留简单模型作为默认方案。

---

# 十七、测试与CI计划

## CI只运行轻量测试

GitHub Actions 不运行完整 Qlib 大数据任务。

CI运行：

```text
schema tests
synthetic PIT universe tests
purged split tests
FDR tests
clustering tests
portfolio accounting tests
execution constraint tests
import tests
config parsing tests
```

## 本地大数据验证

本地执行：

```text
真实Qlib factor frame
完整walk-forward
完整portfolio backtest
容量与压力测试
```

## Windows注意事项

所有可能使用 multiprocessing 的入口：

```python
if __name__ == "__main__":
    freeze_support()
```

继续遵循项目现有 Windows 临时目录和运行器处理方式。

---

# 十八、建议的PR与提交顺序

每个阶段单独提交，不要一次性实现全部计划。

```text
PR 1  Baseline freeze and dependency audit
PR 2  Research data schemas
PR 3  Point-in-time rolling universe
PR 4  Purged walk-forward splitter
PR 5  Bootstrap and FDR correction
PR 6  Rolling factor stability board
PR 7  Factor clustering and representatives
PR 8  Transparent factor score construction
PR 9  A-share execution and transaction costs
PR 10 External PIT exposure data contract
PR 11 Final portfolio diagnostics
PR 12 Ridge / Elastic Net / LightGBM comparison
```

每个 PR 必须包含：

```text
代码
配置
合成测试
运行脚本
contract status
compact report
README或DOC_INDEX更新
```

不得把多个未验证阶段合并成一个巨大 PR。

---

# 十九、统一阶段门禁

每个阶段必须输出：

```text
contract_status.csv
audit_report.md
```

Contract 至少包含：

```text
check_name
status
observed_value
required_value
severity
reason
```

状态枚举：

```text
pass
warning
blocked
fail
```

规则：

* `blocked` 不得自动进入下一阶段；
* `fail` 必须修复；
* `warning` 必须记录；
* 不得为了让 contract 通过而降低阈值；
* 阈值调整必须有独立说明和前后对比。

---

# 二十、最终Definition of Done

整个计划完成时，项目必须满足：

1. 股票池为时点化动态股票池；
2. 因子评价使用 Purged Walk-Forward；
3. 标签区间不存在训练测试重叠；
4. 因子显著性经过 block bootstrap；
5. 大规模筛选经过 FDR 修正；
6. 每个候选因子有跨窗口稳定性记录；
7. 高相关因子完成聚类和代表选择；
8. 多因子组合不存在重复簇投票；
9. 回测考虑A股涨跌停、停牌、整手和成交量限制；
10. 交易成本区分买入、卖出、税费和滑点；
11. 历史行业和市值数据满足 point-in-time 要求；
12. test 指标不参与因子选择和调参；
13. 简单组合是所有复杂模型的强制对照组；
14. 大型中间文件不进入 Git；
15. 所有关键输出均有 manifest、contract 和 audit；
16. 任何新候选默认仍为研究信号，而不是实盘信号。

---

# 二十一、Codex执行要求

开始工作时先完成阶段0，不要直接实现后续阶段。

阶段0完成后输出：

```text
1. 当前仓库状态总结
2. 拟修改文件列表
3. 依赖兼容性结果
4. 分阶段实施顺序
5. 风险和阻塞项
6. 阶段1的具体实现计划
```

未经阶段0审计，不得：

* 修改默认 candidate pool；
* 更换现有股票池；
* 引入模型训练；
* 更新全部依赖；
* 删除现有输出；
* 重命名现有核心接口；
* 批量重构现有 factor research 模块。

实现中优先复用现有配置、runner、manifest、contract 和 report 风格，不创建第二套平行框架。
