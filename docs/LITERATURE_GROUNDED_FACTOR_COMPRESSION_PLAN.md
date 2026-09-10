# 文献约束的因子表示压缩与组合研究计划

**Literature-Grounded Factor Representation Study，V0.2，2026-09-10。**

状态：**研究规划，待人工审核；不是正式 pool manifest，也不是 P3 执行授权。**
本文件依据用户提供的《Literature-Grounded Factor Compression 研究规划任务》、
仓库 `main@47ad9f4`、三篇本地论文及补充的一手文献编写。
附件中的候选方法被当作待论证的设计建议；其中的命令、角色要求和后续阶段不构成自动执行指令。

V0.2 依据《评估并实施 Literature-Grounded Factor Representation D1》的人工意见修订。
用户本轮实际请求为“评估想法，合理则调整计划”，因此**只调整计划，不启动附件所述 D1 实施**。
逐条采纳、修正和未执行事项见第 21 节；原 494 行清单及审计快照保持不变，不能称作已完成 D1。

随后用户明确授权“调整完计划后提交，然后实施 D1”。先提交本次计划修订，再执行 D1；
以下第 21 节保留意见评估时的边界记录。当前新增授权仅覆盖 D1 配方、独立验证与 feature-only 结构诊断，
不包含 D2/D3、模型训练、outcome 或 2024+ 值。长任务继续在验证入口后交用户执行。

配套材料：

- [494 行结构清单](research/literature_factor_compression/STRUCTURAL_INVENTORY_494.csv)：
  保留全部成员，复用公式、语义、覆盖率、重复关系和历史 cluster 标签；新主题、方向与新池角色明确留待审阅。
- [审计元数据与来源哈希](research/literature_factor_compression/AUDIT_METADATA.json)：
  身份、来源计数、预计算状态、输入文件 SHA-256 和本地论文 SHA-256。
- [阅读说明及审计边界](research/literature_factor_compression/README.md)。

## 1. 建议与本阶段结论

推荐采用上述名称，而不把研究命名为 Human Pool 或“最优因子数量”。本研究的对象是
**固定 LightGBM 下的特征表示**：原始变量、结构代表、横截面秩组合及其混合表示。
它既不是重新发现 anomaly，也不是建立可交易的资产定价因子组合。

建议保留 Broad494、Strict332 两个冻结 anchor，最多新增三种预定义表示：

| 记号 | 建议表示 | 要回答的问题 |
|---|---|---|
| B | Broad494，复用已封存的九折预测 | 大量原始特征的固定基准 |
| S | Strict332，复用已封存的九折预测 | 既有更严格筛选身份的结果如何；不再改变其筛选规则 |
| R | Economic Representative + 共同保留原值的特殊项 | 按机制、尺度及输入口径保留代表，能否减少近似实现 |
| C | Family-Balanced Rank Composite + 同一组特殊项 | 在可组合部分做方向一致的秩平均，是否改善表示 |
| H | C 加上 R 中的原始代表，按身份去重 | 在组合特征之外保留原始尺度和形态信息是否有增量价值 |

**五臂是本计划建议，尚未批准。** 不新增旧 Baseline 重训练臂；旧 Baseline 只保留 provenance。
不同时生成多个相关阈值、多种 bucket、多种缺失阈值或多个 K 作为候选臂。
如无法形成经济含义清楚的组合，应在 outcome 封闭期间缩减或退回设计，而非勉强凑齐五臂。

本计划对附件作三项实质性调整：

1. JKP 的聚类输入包含收益，不能把其算法原样放入本项目的 feature-only 设计路径。
2. C 不强制把一个大主题压成一个特征；组合单位是有清楚方向与测量口径的子机制，必要时保留尺度。
3. 三个新臂共享特殊原始特征，避免把“删除未知信号”的影响误称为“压缩”的影响。
   因而 C 是 **composite core + common raw carry-through**，不是纯 composite；必须如实命名。

当前证据不足以预判 H 最好，也不能承诺 R 或 C 一定大幅降维。
没有单独的“只 rank 不压缩”臂，因此 C 与 R 的差异同时包含 rank 变换、平均、缺失处理和表示维数的变化；
即使后续显著，也不能把改善全部归因于降噪。控制实验数量与完全识别机制之间的取舍，应在审核时接受。

## 2. 仓库状态、证据优先级与复用范围

### 2.1 已核实的状态

当前 Git 基线为 `47ad9f4`，其祖先包含已合并的 `f2f3fc3`。
V3 数值权威仍为该提交体系的 float64、分月磁盘 Sequence 输入路径。
实际论文目录为 `E:\qlib_prj\qlib_baseline\paper`；用户消息中的路径转义未改变实际目录。

本轮仅重读以下预计算元数据：运行合同、状态及两个独立重放结果 JSON，未打开 prediction scores 或模型树。

| 对象 | 年度 folds | prediction 行数 | prediction 日期数 | 独立重放状态 |
|---|---:|---:|---:|---|
| Broad494 | 9，2015–2023 | 4,377,824 | 2,189 | `all_nine_exact` |
| Strict332 | 9，2015–2023 | 4,377,824 | 2,189 | `all_nine_exact` |

合计 18 个模型、8,755,648 行 prediction。运行状态为
`all_precompute_and_replay_complete`；outcome evaluation、pool comparison 和 recent access 标志均为 false。
这证明的是已有工程完成记录，**不证明预测有效，不等于本轮重新执行了 replay**。
上一轮已进行产物完整性核验；本轮以记录和对应来源哈希作计划快照。

运行目录：`outputs/research_protocol_v3_precompute/v3_precompute_broad494_strict332_20260909_v1/`。
[预计算运行说明](V3_PREDICTION_PRECOMPUTE_RUNBOOK.md)中的“真实运行尚未执行”属于入口交付时状态，
已落后于本轮读到的机器证据；不能据此要求重跑，也不能由完成预计算推导出 P3 已授权。

### 2.2 可以复用的已有组件

| 证据或模块 | 复用内容 | 不继承的权力或结论 |
|---|---|---|
| [Canonical authority](CANONICAL_RESEARCH_DATASET.md) 及 `factor_lineage.csv` | 数据身份、effective interval、权威公式和接受的残余限制 | 765 物理资格不等于逐折资格；不开放 2024+ 值 |
| [Primary 20D 计划](LONG_HISTORY_MULTI_EVALUATOR_SCREENING_MVP_PLAN.md)、冻结 Candidate Board | B/S 身份来源、已有筛选事实 | 不导入 IC、收益、FDR 排序、年度表现和收益决定的 direction 供新设计 |
| [V0.5.1](../reports/candidate_consolidation_v0_5/v0_5_1/REPORT.md) | 765 行语义、494 行提案、真实参数、单位、缺失诊断、五组等值登记 | `proposal_only` 不是已批准的替代名单 |
| V0.5 feature-only Full / A–D 证据 | 稳定性、共同样本、符号和 cluster 关系 | 不将相关低称作独立、不将相关高称作经济可替代 |
| [V3 protocol](RESEARCH_PROTOCOL_V3_MVP_PLAN.md)、P0/P1 回执 | 九折日历、purge、合法日期、训练资格、目标与权重合同 | 不继承旧计划的四池/Baseline 名单及未实施评价器 |
| [输入模块](../model_research/long_history_inputs.py)、[预计算模块](../model_research/v3_prediction_precompute.py) | 有界 reader、键轴、原始训练数值循环 | 新的 composite 语义仍须新增验证 |
| [独立重放入口](../scripts/replay_research_protocol_v3_predictions.py) | saved-model、独立过程、keys/score/reason 精确核对方式 | 不能用同一 composite 实现生成并验证自己 |

Canonical identity 固定为：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

源 V3 重算运行：`v3_recompute_audit_20260909_v1`；其规范化合同哈希：
`a73a2a504c7e13d92273837c22d4bc087ac31190d1dc0d1aed7365f74671858e`。
新的研究不得修改旧 manifest、回执、模型或 canonical 数据来迎合新规则。

### 2.3 必须保留的研究范围声明

B/S 身份来自 2010–2023 retrospective screening；V0.5.1 相似性和质量摘要也覆盖同一开发期。
本研究允许在该身份上作事前规则冻结，但不能声称名单、结构选择或语义发现是各历史 fold 的 selection-past-only。

后续模型训练可严格做到 train-label-past-only；同一天全横截面 rank 可使用该日决策时已知特征。
这两者都不消除此前名单筛选和全开发期结构审阅的选择偏差。
统一标记：`pool_discovery_scope=retrospective_development_2010_2023`，
`representation_design_scope=outcome_blind_retrospective_metadata_and_feature_evidence`。
2015–2023 结果至多是条件于上述研究历史的回顾性模型比较，不能称作新的独立 OOS 发现。

## 3. 文献核验与可迁移的方法

### 3.1 四篇核心文献

**[L1] Leippold、Wang、Zhou（JFE，2022）**。
本地主文及补充材料 C.4（PDF 第 29 页）确认十分类。
这些是该文变量集合的分类，不是要求所有技术变量接受同一经济方向的标准。
例如其 momentum 类含多期限收益和 maxret；机械沿用会混淆趋势、反转及彩票型收益。
采用它作为 A 股 taxonomy 的交叉参照，而不按论文重要性为本项目配置权重。
[主文](https://doi.org/10.1016/j.jfineco.2021.08.017)，
[作者补充材料](https://ars.els-cdn.com/content/image/1-s2.0-S0304405X21003743-mmc1.pdf)。

**[L2] Stambaugh、Yuan（RFS，2017）**。
第 2.1 节以 11 个 anomalies 构造两组月度 rank composite；等权平均可用排名，随后构造多空因子。
正文同时讨论异常收益相关与平均横截面排名相关，两种分组在其样本得到同样两组。
可迁移的是多个有同向含义的代理变量作透明平均；不能迁移样本内收益聚类、组合排序断点或其业绩结论。
本文是两位作者的 SY；相关三位作者的 Stambaugh–Yu–Yuan 研究应另称 SYY，避免混淆。
[论文及第 2.1 节](https://doi.org/10.1093/rfs/hhw107)。

**[L3] Jensen、Kelly、Pedersen（JF，2023）**。
正文 III.B 和附录 VII / Figure IA.15 确认：153 因子、13 个 themes，聚类基于按原文方向定号的
美国因子 CAPM residual returns，距离为 1−相关，使用 Ward；13 类结合树状结构与经济解释确定。
因此“JKP 证明应对 494 列做 feature-only Ward 并保留 13 列”是不成立的。
本项目只借鉴经济与统计证据并列的组织方式。
[主文](https://doi.org/10.1111/jofi.13249)，
[附录 VII–IX](https://onlinelibrary.wiley.com/action/downloadSupplement?doi=10.1111/jofi.13249&file=jofi13249-sup-0001-InternetAppendix.pdf)。

**[L4] Gu、Kelly、Xiu（RFS，2020）**。
作者版第 2226 页确认 94 个特征、与 8 个宏观量交互、74 个行业 dummy，共 `94×9+74=920` 个输入。
论文支持非线性与交互的重要性；不意味着重复列越多越好，也不验证当前固定 LightGBM。
保留 H 臂的依据是需要检验聚合丢失的信息，而非预设 H 必胜。
[作者提供的发表版](https://dachxiu.chicagobooth.edu/download/ML.pdf)。

### 3.2 补充文献、方法层次与取舍

| 文献 | 与本研究相关的方法事实 | 建议 |
|---|---|---|
| [L5] Han、Zhou、Zhu，JFE 2016，*A trend factor* | 多种移动平均期限共同刻画趋势；研究对象不是 Alpha360 的连续 lag 列 | 支持区分时间尺度，不把其拟合权重或期限网格直接搬来；见[作者摘要及版本](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2182667) |
| [L6] Liu、Stambaugh、Yuan，JFE 2019，*Size and value in China* | A 股规模、估值构造有本地市场含义 | 保留本地定义与口径；不因该文改变已冻结 universe 或把规模方向视作通则；见[NBER 作者稿](https://www.nber.org/papers/w24458) |
| [L7] Kozak、Nagel、Santosh，*Shrinking the Cross Section* | 收益因子空间的小量 PC 与少量原始 characteristics 的稀疏 SDF 不是同一件事 | 保留过度压缩风险；其 SDF 收益目标及 shrinkage 不直接用作特征选择；见[NBER](https://www.nber.org/papers/w24070) |
| [L8] Kelly、Pruitt、Su，JFE 2019，*Characteristics are covariances* | IPCA 用 characteristics 为时变载荷提供信息，同时利用收益估计潜在因子 | 是独立模型研究，不是无标签预处理的直接替代；见[发表版](https://doi.org/10.1016/j.jfineco.2019.05.001) |
| [L9] Feng、Giglio、Xiu，JF 2020，*Taming the Factor Zoo* | 高维既有因子条件下检验新因子的定价贡献，需处理模型选择误差 | 不运行 supervised selection；不能用 feature-only cluster 代替增量定价检验；见[NBER](https://www.nber.org/papers/w25481) |
| [L10] Giglio、Kelly、Xiu，ARFE 2022，*Factor Models, Machine Learning, and Asset Pricing* | 区分预期收益预测、风险载荷、SDF、因子估计及 alpha 检验 | 按估计对象选择方法，避免把 portfolio factor compression 当作 feature compression；见[作者综述](https://stefanogiglio.org/papers/giglio-kelly-xiu-arfe-2022.pdf) |
| [L11] Dong，*Economic Aggregation of Return Signals in Global Markets* | 经济分类后组合信号，与本问题接近；SSRN 摘要写 85 个 signals、五组，期刊记录另有版本 | 仅作补充线索；全文方法未核实，不用其权重、缺失细则或最终数量制定本版规则；见[作者工作稿摘要](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5105390) |

本轮没有发现能够直接覆盖“当前 A 股 494 个具体实现 + daily 20D target + 固定树模型”的公认 taxonomy，
也未发现一个足以直接授权“每个 Alpha360 字段只留 5/20/60”或“家族平衡平均必然最优”的成熟定理。
这不是证明不存在相关研究，而是本轮已核实文献的适用边界。

多 horizon、基函数、PCA、PLS、autoencoder、characteristic-managed portfolios 都可构造压缩表示，
但它们的拟合对象、状态和超参数不同。尤其 characteristic-managed portfolio 用到收益形成投资组合，
不能作为本轮无 outcome 的 composite feature。
首轮不增加 learned compression 臂。若后续单独批准一个 benchmark，优先考虑仅在合法 train 特征上拟合的
rank-PCA：缺失规则、标准化和解释方差准则必须先锁定，不能用预测表现选组件数；这仍是第二版研究。
不得对 pairwise 中位数绝对相关矩阵直接求 PC 并称解释方差，因为该矩阵未必半正定。

## 4. 494 个因子的真实结构审计

### 4.1 来源与尺度

| 来源 | 成员数 | 对规划的直接影响 |
|---|---:|---|
| Alpha360 | 287 | 五组历史价格/当日收盘价比值，是最主要的 dense-lag 结构 |
| Alpha158 | 85 | 多窗口统计、趋势斜率、位置、价格量关系及当日形态；不能只按名称分类 |
| TA | 57 | 真实参数、价位单位、状态与递归处理有差异 |
| Alpha101 | 32 | 当前实现语义待逐项核对，不能按原论文方向自动组合 |
| mature_public | 21 | 估值、规模、流动性、风险等；有供应商口径与 reconstructed PIT 差异 |
| project_basic | 12 | 明确定义的收益、反转、成交额与波动等 |
| 合计 | 494 | R/C/H 均只从这一冻结父身份派生，不从 765 中补入新成员 |

现有分类为 PriceTrend 292、ReturnDynamics 44、LiquidityTrading 32、RiskLottery 57、
TradingBehavior 10、OpaqueMultiInput 27、Valuation 7、SizeStructure 1、PriceLevelOrPriceDifference 24。
这些是 **旧语义标签计数**，不是本计划的新 economic-theme 分配结果。

### 4.2 Alpha360 的网格不是假设

| 字段 | 数量 | 现有 lag 范围 | 0–59 中缺少的 lag |
|---|---:|---|---|
| CLOSE | 57 | 3–59 | 0、1、2 |
| HIGH | 55 | 5–59 | 0、1、2、3、4 |
| LOW | 60 | 0–59 | 无 |
| OPEN | 58 | 2–59 | 0、1 |
| VWAP | 57 | 3–59 | 0、1、2 |

这里没有 Alpha360 VOLUME 成员。不得按照完整 Alpha360 模板补回缺失 lag，也不得把 287 个输入写成 287 个独立经济想法。
`Ref(field,h)/close_t` 的历史字段、分母与 lag 都影响含义。
LOW0 是当日 low/close；CLOSE20 是历史 close/当前 close；HIGH20 包含历史 high 相对当前 close 的路径位置，
并不自动等于 20 日收益。VWAP 还需保留原始实现与 proxy 的输入身份。

### 4.3 语义已解与替代已获准是不同状态

462 项已有明确的实现语义、窗口和量纲，32 项 Alpha101 未解决。
V0.5.1 的 replacement hold 原因互斥计数如下：

| 状态 | 数量 | 本计划处理原则 |
|---|---:|---|
| 无 hold | 433 | 进入主题、方向和角色审核；不等于已准许组合 |
| unresolved_semantics | 32 | 保留原输入身份，禁止由收益反推方向 |
| provider_price_scale_unverified | 23 | 不用横截面 rank 假装修复 provider 价格尺度 |
| recursive_missingness_quality_review | 3 | ATR、ADX neg/pos；不在新表示里补零或改变递归定义 |
| state_or_event_mask_review | 3 | PSAR down、BBHI、KCHI；区分未触发状态和数据缺失 |

61 个有 hold 的条目与“32 个语义未解”不是同一个集合。
24 个 `provider_price` 量纲也不等于 23 个价格尺度 hold，不能把不同诊断计数混用。
已有质量表中 ADX neg/pos 和 ATR 的 worst-era coverage 约 6.9%，PSAR down 约 34.1%；
这是旧的开发期 feature-only 摘要，不是本轮新扫描或模型覆盖率。

五组已登记精确等值：LOW0 的 Alpha158/360 对，以及 ROC5/10/20/30 与 CLOSE5/10/20/30 对。
证据范围为 2010–2023 的 168 个月及相同 mask；不是跨所有未来样本的公式恒等证明。
旧版跨语义替代不能复活：V0.5.1 复核后没有跨层级 conditional alias 提案。

### 4.4 当前真实公式要求的修正

- `alpha158_BETA* = Slope(close,h)/close`，是价格斜率，不是市场 beta。
- `alpha158_ROC* = Ref(close,h)/close`，与通常正向收益 ROC 的单调方向相反；不能按 ROC 名称赋号。
- `ret_h = close/lag(close,h)-1`；`rev_5` 已带负号；`rev_20_exclude_5` 刻画 5–20 lag 区间，不能再次重复反号。
- `mature_reversal_1m` 的实现 horizon 为 21，不能因目标叫 20D 就改成 20。
- PIT 估值使用最新可得合并报表期，不自动等同 TTM；vendor TTM 版本需另保留口径。
- idiosyncratic volatility 是先估 beta 再滚动计算残差波动；不是一个可用单一“60”概括的窗口。
- KAMA 使用既有 causal anchor 和状态，不以每年起点重新初始化。

这些反例说明 inventory 必须保留完整公式、分子分母、操作符及真实参数。
只保留 `family=momentum, window=20` 会在组合前丢失关键语义。

## 5. Taxonomy：经济概念、测量方法与时间结构分层

建议每列拥有一个主 economic theme，允许多个只作检索的 secondary tags；
但在同一 composite 树中只分配一次权重，避免 multi-label 隐式重复计入。
字段依次为：主题 → 子机制 → 测量家族 → horizon/lag 结构 → 输入/单位/availability 合同。
来源库只作 provenance，不能直接当经济家族。

| 建议主题或维度 | 本库已有实例 | 不应混入的变量 |
|---|---|---|
| Valuation | book、earnings、sales、dividend 对价格或市值的比值 | 不能由 earnings yield 推导 profitability，也不混同 PIT 与 TTM |
| Size / structural conditioning | log total market cap | 不能当作已验证小盘 alpha；不新增行业/ownership 值 |
| Return trend / reversal | ret、rev、价格趋势斜率 | 分开“过去上涨程度”和“未来反转假说” |
| Price path / relative position | 历史 OHLC/VWAP 相对当前价、滚动极值/分位数/位置 | 不把所有路径变量都标 momentum |
| Liquidity cost | Amihud illiquidity 等 | 与交易活跃程度分开，避免方向互相抵消 |
| Trading activity / price-volume relation | turnover、amount、量价相关 | 活跃不必然更流动，相关性本身不是预期收益方向 |
| Volatility / residual risk / asymmetry | total、downside、idiosyncratic、range、skew、max return | total vol、vol change、下行风险及彩票特征不强行一个平均 |
| Within-day shape | KLEN/KLOW/KUP、intraday return | 日 OHLC 构造不称为高频订单簿 intraday 数据 |
| Technical state / oscillator | RSI/PPO、事件指标及状态变量 | 有些只是条件变量，不强制获得单调 alpha 方向 |
| Unresolved / scale-sensitive | 当前 hold 项 | 是明确的审阅状态，不是新的经济机制 |

LWZ 的 ownership、growth、leverage、earnings 等大类允许在此 494 universe 中为空。
不能为凑满十类或 JKP 十三类新增因子；不得把 price trend 当作企业 growth。
最终分配须由逐条公式对照完成，现有 CSV 的 `proposed_economic_theme=pending_review`
是诚实缺项，不代表审计已经完成了 494 个方向与主题的专业定性。

## 6. 同向含义与 direction authority

必须分别保存三种概念：

| 字段 | 含义 | 来源 |
|---|---|---|
| `measurement_orientation` | 数值增大代表什么可观察状态，例如过去上涨、估值更便宜、交易成本更高 | 权威公式与代数关系 |
| `expected_return_direction` | 某个外部研究假说认为该状态对应较高/较低未来收益 | 明确文献、市场/样本/期限适用条件，允许 unknown |
| `representation_sign` | 为同一 composite 的共同轴作统一正负号 | 由前两项及批准的 composite 轴推导，不能读取本库 IC |

默认建议采用 **economic-axis composite**：高值表示同一经济状态，不强制表示高预期收益。
例如波动强度越高可统一为正轴；它对收益正负的非线性关系交给固定模型。
这比把所有技术特征包装成文献已确立的 alpha composite 更适合当前库，也符合“有事前可说明经济方向”的要求。
如用户要求 C 只能是预期收益同向的 SY 式 anomaly composite，则无可信收益方向的家族必须转入共同 raw 项，
这会改变 C 的构成；两种定义不能看结果后切换。

方向证据等级建议固定：A=实现与原文公式一致；B=已有独立于 outcome 的权威定义；
C=可审阅的代数/测量轴推导；U=未知或冲突。A/B/C 可支持 measurement orientation；
expected-return direction 仍须独立注明，不能由 C 自动升级为外部 alpha 证据。
旧 `analysis_direction` 即使已经冻结，只要来源含开发期收益，也不能作为本轮方向 authority。

允许的例子：把历史/当前 close 比值的 rank 反号，使高值表示较强过去涨幅；
把已带负号的 reversal 恢复到统一的“过去涨幅”轴时记录这次符号变换。
不允许的例子：看到 volatility 在某年 IC 为负才反号，或按多数年份/旧 consensus 方向统一。
跨零倒数、非单调变换、不同 mask、binary/state 变量不得仅凭相关符号判定可逆同序。

## 7. Representative：先定义可替代集合，再选择代表

建议顺序为：精确等值处理 → 特殊项隔离 → 语义/输入口径分层 → 同尺度近似证据 → 代表排序。
不要创建多个主观分数并自由调整加权系数。

### 7.1 三种关系分开使用

1. **精确重复**：只在已有等值登记及 mask 证据范围内，为新表示保留 canonical representation，
   所有原身份仍在映射表。跨 source 的同一等值也只能计一次 composite 权重。
2. **同语义近似替代**：须同子机制、单位、输入口径、window/lag 和状态语义。
   建议仅使用 V0.5.1 最严格的 `0.995` 层级作为本版近似资格，
   沿用 Full 和四 Era comparable、median/q10 及 sign consistency 条件。
   这是项目保守约定，不是论文推荐常数。其他层级只作既有证据背景，不生成多个 pool。
3. **有损尺度压缩**：dense lag 的 thinning 是主动放弃部分时间分辨率，单列登记。
   不得因这个规则保留一个代表，就宣称被折叠的跨 horizon 列与代表等价。

复用既有 complete-linkage 关系及 pair 证据，必要时在批准的语义子集合验证全 pair 资格。
不能把 A–B、B–C 相似的 connected component 自动视作 A–C 可替代。
未知 pair、跨 Era 符号不稳或 overlap 不足时，默认不作近似折叠；不降低阈值以满足数量目标。

### 7.2 代表选择政策

优先复用 V0.5.1 的词典序规则：

1. 先通过明确语义、同机制/尺度/单位/口径及 hold 检查；
2. 已有 canonical 等值代表优先，保持原登记的 provenance；
3. 同一合格组内，worst-era coverage 较高、full coverage 较高、infinite fraction 较低；
4. 仍有并列时，使用该合格组内 feature-only medoid；最后按 factor ID 稳定排序。

这里的全开发期 coverage 排序属于已披露的 retrospective 结构设计，不冒充逐折 past-only。
公式复杂度暂不进入排序：V0.5.1 已发现运行说明/元数据 token count 不能代表真实公式复杂度。
文献权威用于解释和资格审核，不允许在看完结果后把自己喜欢的来源调到更高优先级。
若两种实现有不同 availability 或 mask，就保留区别；不为了简短公式牺牲可用信息。

## 8. Dense lag 与多时间尺度的预冻结规则

本节为 **待审核的项目规则**，不是从文献直接得到的唯一答案。
目标 20D 决定 label/purge，不决定所有特征必须使用 20 日回看。
当前 0–59 trading-day grid 只到约一季，不足以代表经典 6–12 个月 momentum 或多年 reversal；
不得把 22–59 叫作那些文献意义上的 long-term momentum。

### 8.1 建议的一次性网格划分

仅对已确认同字段、同分母/参照、同算子、同 normalization、同 availability 的 Alpha360 连续 lag 家族，
建议使用固定 trading-session buckets：`{0}`、`[1,5]`、`[6,21]`、`[22,63]`。
含义分别为当日、一周内、约一月内、约一季内。
63 是 bucket 边界，不能由此新增 60–63 lag；空 bucket 不产生特征。
这不是 `5/20/60` 端点保留，也不是按 label 的 20D 选最佳 lookback。

R：对每个非空“字段 × bucket”的去别名、去重复 lag 网格排序，取**较低的中位 lag**；
奇数项取中位项，偶数项取中间两项中较小者，再由精确别名政策确定其 canonical ID。
这精确实现 V0.1 的 `sum_j abs(log(1+h)-log(1+h_j))` 最小化及“并列取较小 lag”，
避免对浮点 log 求和的理论并列误差作额外容差判断。
这是只依赖离散网格的中心代表规则，不读取相关、IC 或收益来决定 lag。
先在结构节点上处理已登记跨库精确重复，别名不能因换库而漏掉相应的 horizon 节点。
若实际公式核对显示字段或分母不一致，则拆分家族，不应用本条。

C：在相同字段和 bucket 内对合格 rank 作固定层级平均，保留字段差异；
不把 HIGH/LOW/OPEN/VWAP 任意平均成一个“Momentum”。
H：同时保留该 bucket 的 composite 与 R 的原始 lag 代表。
低频轮廓被保留，细粒度 lag 形态会损失；H 也不能完全恢复原始 287 列的信息。

按已审计的网格，这一局部规则有 16 个非空“字段 × bucket”结构单元；
这是纸面结构计数，不是批准的最终 16 列名单，不包含跨库重用、特殊项或其他 207 个成员。
因此不能把全池 feature count 从这里直接外推。

D1 获授权后，先逐式确认只有 lag 不同，再验证节点重排、重复 alias、缺失 lag、奇偶网格及桶边界。
四桶仅是唯一默认候选，未通过公式和 availability 审阅前不升级为 freeze。
结构报告逐 family 列出原始列数、实际 bucket、R 代表、C/H 输出和丢弃的 lag 分辨率；
不得把仅在小样本日期验证过的公式/缺失行为称为全部年份已验证。

### 8.2 其他 multi-window 与状态家族

Alpha158 的 5/10/20/30/60 是窗口统计，不是单点 lag；本版先保留不同窗口的代表，
只在同窗口做合格去重，不因为同落一个月 bucket 就把 STD5、STD20 视为重复。
TA 的 fast/slow/signal、多层平滑、KAMA anchor、PSAR 状态、PIT/TTM 更新节律单独编码。
不把 JSON 参数压缩为最大的一个 window 后套 Alpha360 规则。

固定基函数、对数均匀节点、feature-only clustering 和网格中点都是可行候选，但首轮只批准一种。
本版倾向网格中心是因为无需拟合，也无需重新挑相关 cut；其缺点是对局部尖峰与端点不敏感。
若人工不接受这种有损假说，则保留 dense grid 原值并收缩研究问题；
不要先试一轮业绩再改 bucket。对更激进的跨尺度主题平均，留作新版本，而非本轮隐含 sensitivity。

## 9. Family-balanced rank composite 的明确数学合同

### 9.1 每日横截面 rank

在信号日 t 的 canonical dated universe 中，对每列 j 的有限值独立排序；
不使用未来存活名单、该日 label 是否有限、池内完整案例或最终评价交集来定义 rank universe。
Inf 视为无效并保留原因；既有 NaN 不补零。
建议采用 average ties，令 n 为当日该列有限值个数：

```text
u(i,j,t) = (average_rank(x(i,j,t)) - 0.5) / n(j,t) - 0.5
z(i,j,t) = representation_sign(j) * u(i,j,t)
```

rank 为从 1 起的升序名次。average ties 保留为推荐规则；binary 不加 jitter，不按 ID 打破相同取值。
全缺失、全列常数（包括 n=1）不产生有区分度的测量，输出 NaN 并记录独立原因。
**feature rank 的 `n_min` 尚待 D1 结构审核，100 仅是诊断参考线，不是已冻结阈值。**
V3 的每日 IC pair 门槛解决评价有效样本问题，不能据此证明特征横截面 rank 也应同样设为 100。
数学上可排序也不代表经济代表性足够；最终须根据第 9.4 节的样本覆盖及轴稳定性选择一个明确规则，
不得按 fold/source 分别调阈值。发布候选 recipe 前写入唯一整数；未决则标 blocked，不暗中默认 100。
未知方向不靠取绝对值或 PCA 载荷符号消除，而是保留 raw 或停止该组审核。

### 9.2 防止 dense family 隐式加权

定义三个层级：唯一信号节点 j → 测量家族 f → 获批准的 composite 子机制 g。
同一精确别名先去重；家族定义基于公式、数据输入与 horizon，而不是 `alpha360/ta` 等来源库名字。

```text
a(i,f,t) = mean(z(i,j,t) over valid unique nodes j in family f)
c(i,g,t) = mean(a(i,f,t) over valid measurement families f in group g)
```

所有层级均固定等权；在家族集合与有效性不变的条件下，一个家族增加近似 lag，不增加其在组 g 的名义总权重。
例如 50 个同家族 lag、3 个第二家族变量、2 个第三家族变量：
feature-equal 平均使第一家族占 50/55；三级定义下家族各占 1/3，家族内部再平均。
若 50 个 lag 已按四个经济尺度拆分，尺度权重必须在 g 的树上先固定，不能因某尺度列更多而增加权重。
本版对 Alpha360 默认保留“字段 × bucket”输出，不额外叠加一个全路径平均特征。

recipe 的 DAG 必须显式说明 bucket 在哪一层；不能实现时把 bucket 当家族、统计时又当主题。
当前 Alpha360 的输出节点是“字段 × bucket”，其叶子为唯一 lag；若其他 composite 同时包含多个尺度，
先按批准的测量家族分配权重，再按预定义尺度分配，不能由库名或节点数决定父层权重。

验证区分两种不变性：**精确 alias** 在同值同 mask 的去重后，输出值、有效 mask、分母与权重均应不变；
**近义但不相同的 lag** 可以改变组内均值和子节点可用性，只要求固定有效家族条件下父层名义权重不变。
新增真实节点还可能改变 `ceil(q×children)`，进而改变有效家族和实际归一权重；必须单列诊断，
不能要求或声称任意增列都保持输出及有效权重不变。任何增列都产生新的 recipe hash，不是冻结后可自由追加的操作。

跨主题只为 taxonomy 汇总，默认不再平均成一个总 alpha。
一个仅有一个唯一节点的组可输出 rank-transformed singleton，但必须标记 singleton，
不宣称它已经获得多代理降噪。
R 中保留其 raw 版本；H 中允许 rank 与 raw 同时存在，因为二者不是数值相同的重复列。

### 9.3 缺失、家族有效性与固定权重

**50% 暂保留为 D1 诊断候选，不作为已批准的最终缺失政策。**
诊断候选在每个聚合层要求至少 `ceil(0.5 × 冻结子节点数)` 个有效子节点；达不到就输出 NaN。
分母使用预冻结成员数，不能按当日缺失情况先缩小成员表。
达到门槛后对有效节点重新归一等权，输出有效节点数/有效家族数/缺失原因作为审计旁表，
不默认把这些计数加入模型，以免新增一套 missingness features。

50% 是工程折中，不是文献最优阈值；本轮不扫描任何值；未来 D1 不跑 25/50/75/100% 候选网格。
其代价是缺失造成有效权重随股票和日期变化，可能改变同一 composite 的含义。
必须分别审核叶节点→family 与 family→composite 两层的有效性，不能只用总体有限率判定合格。
尤其三家族组在该政策下至少需要两个有效家族；“只有一家族但仍有效”是实现/计数/层级定义错误，
不是一个可接受的高 coverage 现象。两家族组则可能合法退化为一家族；须报告这种语义退化的频率。
名义家族数、实际 family 数及多个高度相似家族的经济信息重叠也不同，不能混用一个计数。

财务指标使用 canonical 决策时可得事件，不把报告期末当发布时间，也不重新全期前填；
已经按合法 availability carry-forward 的值可以在当日参与 rank，其横截面排名随 universe 变化是允许的。
市场/日频特征和会计比率默认不在同一 composite 内混合；TTM 与非 TTM 分开。
状态掩码无效、尚未触发和真的缺测必须分别记录，不能用“缺失=中性排名”替代。

### 9.4 待授权 D1 的结构诊断与唯一规则收敛

先完成可追溯的 provisional DAG、叶节点及 family 定义，再登记固定日期采样、统计口径、资源预算与
什么现象会触发人工审核，之后才运行 feature-only canary。记录全部失败组，不按诊断结果反复换抽样日期。

| 层级 | 必须输出的结构证据 | 防止的误判 |
|---|---|---|
| 叶节点 × signal date | canonical universe 大小、有限 n、不同取值数、n<100 日期数/比例、all-missing/constant/Inf | 把 IC 门槛移植为 rank 门槛，或把所有缺失都归因于早期财务项 |
| family × stock/date | 有效唯一节点数、冻结节点分母、有效率和原因 | 去重前后门槛变化被掩盖；dense grid 只剩少数 lag |
| composite × stock/date | 有效 family 数、冻结分母、最终 mask、single-family 频率、可用轴/尺度 | 名义多家族但实际变成单代理 |
| 实际权重 | 各家族名义/有效权重、最大权重及相对完整观测状态的偏移；缺失输出单列 | 只看总体 coverage，不看经济含义漂移 |
| 输出列 × year/fold | finite/constant/Inf、早期可用性、parent dependencies、R/C/H 输出数 | 某些年份不可用，却用全期均值掩盖 |

可定义 `N_eff=1/sum_f(w_f^2)` 描述有效权重分散度，w 为合计 1 的实际 family 权重。
它不是“独立经济信息数”；等权有效家族下仅等于有效家族个数，相关 family 不因此变独立。
频率同时给完整 universe 分母与 composite 有效键分母，避免缺失输出被分母悄悄移除。

按 2010–2023 signal year 汇总，并明确九折的 train/predict 角色；同一训练日期会进入多个 expanding folds，
各折统计不能再相加当作独立观测。n 在原始叶列定义，composite 另报输出有限数，不把二者混称“composite n”。
抽样 canary 只能报告抽样结果；若要声称每年全部 n<100 日期数，必须复用匹配合同的全日证据或另做有界完整扫描。
耗时较长的扫描仍在批准、轻量验证后交用户运行，不由本轮文档修订触发。

审阅时先判断轴是否由足够的测量家族/尺度支撑，再判断可用性是否足够；不能选“coverage 最高”的门槛。
没有证据证明 100/50% 合适，就不得把它们写成 finalized；也不能为绕过失败把全部成员塞入 U。
如需修正规则，写明具体结构失败及机制理由，经审核确定一个替代规则，再作确认性结构验证；
保留失败版本和变更记录，但只提交一个当前候选，不循环试阈值、不向 D2 提供 variants。
如无法给出有依据的唯一规则，D1 返回 `BLOCKED_FOR_HUMAN_REVIEW`，而不是为了完成 freeze 强行选择。

## 10. 特殊项、共同 raw 部分及混合表示

建议在三种新表示中定义相同集合 U：当前有 hold 且经逐项审核允许保留 raw 的成员，以及完成逐项审核后仍不适合
共同方向或平均的 conditioning/state/raw-only 成员。U 的身份须在 outcome 前冻结。
当前 61 个 hold 是 U 的初始审阅依据，不是本轮已生成的正式 U manifest。

采用 U 的理由是控制信息删除这一混杂因素。它不表示这些变量已具备经济解释，
也不表示可任意变换其单位。它们以 canonical 原值、原 mask 和原资格合同进入三个新表示，
已有 anchor 的工程资格提供可用依据；一旦发现明确未来泄漏或错误，必须停下整个研究处理数据正确性，
不能以“共同保留”绕过 correctness blocker。

D1 须先为全部 494 项区分：未解语义、未解价格尺度、递归缺失、状态/事件、binary/conditioning、
measurement orientation 未定、语义有效但 raw-only，以及 correctness blocker。
`expected_return_direction=unknown` 本身不是进入 U 的理由：只要 measurement axis 明确，仍可能适合 C。
每项附证据引用和处理原因；允许的去向是 `U_RAW`、`G_REPRESENTABLE`、
`EXACT_ALIAS_OF` 或 `BLOCKED_FOR_HUMAN_REVIEW`，并分别记录 raw/composite 资格。
精确 alias 的原身份留在清单，表示权重只计 canonical 节点。blocker 不计入 U 或“已就绪”的 recipe。

共同 U 只控制特殊项被单独删除的混杂，不消除有损压缩自身的信息损失，也不能保证 R/C/H 与 B 信息等价。
若共同 U 大到 C/H 只改变很小的一部分，报告实际改变范围并在 outcome 前审核研究问题，不能按希望的压缩比例缩小 U。

令 G 为其余经过审核的可表示部分，R(G) 为其结构代表，C(G) 为其组合输出，则：

```text
R = U ∪ R(G)
C = U ∪ C(G)
H = U ∪ R(G) ∪ C(G)
```

精确相同的输出只保留一次；相同经济概念但不同数值表示不是自动 duplicate。
H 的定义直接来自 R/C，不能看模型重要性后只留“有用”的 raw。
这样 H−C 是加入冻结 raw representatives 的增量检验，R−B 是结构收缩的整体检验。
只允许报“固定表示的增量”，不把它等同于因果证明某个 horizon 或交互机制。

32 个 Alpha101：先逐项对照 canonical override、原论文表达式、PIT rank 和输入口径；
未解但无 correctness 疑点且具有保留 raw 依据者可进入 U，其余明确 blocked；不按 alpha 编号继承方向。
23 个价格尺度 hold：逐项审阅 raw 保留依据，不能自行除 close、重建复权或 z-score 修补。
3 个递归问题和 3 个状态问题：分别审阅 raw 的资格或 blocker，不改变 canonical；新增有界诊断必须另授权。
对 no-hold 成员仍要审核 direction/测量含义，不能把 433 直接等同 composite eligible。

这种设计可能使 C 的 raw 部分相当大。若“纯经济可解释的池”才是用户真正目标，
应批准另一个不同问题的方案，并承认它混合了信息排除与压缩；不要把本版 C 静默改名为纯 composite。

## 11. 不预定 K：数量与归因的报告方法

数量是唯一成员节点、合格代表组、组合组、raw carry-through 和精确输出去重的结果：

```text
F_R = |U| + |R(G)|
F_C = |U| + |C(G)|
F_H = number_of_distinct_output_columns(U, R(G), C(G))
```

真实实现需要额外扣除三者间的精确重复；不得为得到漂亮比例而增删列。
freeze packet 同时报父特征使用数、最终模型列数、raw/composite/singleton 数、
每个 composite 的 unique-node 数/家族数、保留 horizon 和丢失的时间分辨率。
若 F_H 不小于 494，H 是 feature augmentation，不能称为降维成功。
如果 R 几乎等于 B，说明本规则只允许有限近似替代，不构成放宽语义标准的理由。

不得预报 87/19/124 之类具体终值。当前尚缺逐列 direction、measurement-family 分组和 availability 审阅，
任何“预计最终有多少列”的精确数字都会让规则变成向目标 K 靠拢。

## 12. 计算公平性与既有 anchor 的复用条件

继承 [V3 冻结配置](../configs/research_protocol_v3_mvp.yaml)：LightGBM 4.6.0、
100 rounds、num_leaves=15、max_depth=4、min_data_in_leaf=100、learning_rate=0.03、
lambda_l2=1、feature_fraction=0.8、8 threads、固定 seed、CPU deterministic/force_col_wise、
float64 Sequence、无 early stopping。其余参数以完整合同为准，不以这段摘要覆盖配置。

保持 expanding、annual refit、T+1/20D、exact label purge、daily-equal 权重和相同训练目标。
先在共同合法 universe 上构造每日 centered label rank，再按本池合法 feature mask 选择训练行；
不可为了 C 缺失较多而在剩余子样本重算 label rank。
原始与 composite 均按固定序列顺序输入；不按不同 pool 单独调整 rounds、leaves、bins 或 seed。

同一 `feature_fraction=0.8` 不代表同样数量的列被抽取；高度相关列多的家族被模型见到的概率也会不同。
R/C/H 的学习难度、可用 split、训练样本 mask 和缺失路线可能不同。
因此研究估计的是 **固定 learner/config 下整个 representation pipeline 的效果**，
不是各表示各自最佳调参后的理论上限，也不是完全等价的有效模型容量。

新臂资格仍只用该 fold 合法 train features，不能用 2015–2023 评价覆盖率挑选它的 constituent。
列的全 missing/常数等不合格情况应停止并审阅；不得自动删列、换代表或按年度改变组内权重来续跑。
单只股票整行无特征遵守原 prediction reason 合同，不静默移除日期/股票。

已有 B/S 只有在 target、键轴、日期、label maturity、训练权重、模型合同、输入数值/顺序都兼容时才可作为 anchor。
如果需要修改这些公共合同，不能沿用其预测宣称公平；先停止，解释是否需要新运行和额外授权。
R/C/H 新增最多 27 个年度 fit，顺序执行并各自独立 replay。
H 可能比 B 更宽，资源资格须重新做有界 canary；不能假设压缩研究必然更省内存。
用户仍负责长运行；本阶段不提供尚不存在的正式 PowerShell 执行命令。

## 13. 后续 P3 的评价方案：仅作预注册建议

**本节定义未来可能批准的 outcome evaluation，不在本轮执行。**
获准实现新表示、获准预计算和获准打开 outcome 是三个不同动作；全部新池冻结和预计算/replay 完成前，
B/S 的 outcome 始终封闭。

### 13.1 固定主估计量与共同样本

Primary：2015–2023 可评分日期上，每日横截面 Spearman Rank IC 的等日期均值。
不能按年度先均值再等权作为 pooled primary；不能取 absolute IC；预测正负不在评价时翻转。
full-year prediction 保留 2,189 个日期；截至 2023-12-29 日历上最多 2,168 个日期有成熟 20D 标签。
2023 年末最后 21 个交易日保留 prediction，不能读 2024 端点去评分；实际有限样本还会减少可评分日期。

先定义共同合法 universe、已成熟且有限的原始 label，再取全部获批臂 prediction 有限的共同股票键集合。
每一日对所有臂使用同一股票集合，至少 100 对，重新计算用于评价的 Spearman ranks。
这一重排只属于评价，不回写训练 label rank 或 composite feature rank。
所有正式 contrasts 使用相同日轴；某日不足则全部标 unavailable 并保留原因。

同时报告每臂自身覆盖率、共同交集覆盖率、每年有效日数、缺失原因和对应 universe 分母。
沿用 V3 每年 prediction coverage ≥95% 的资格门槛，并建议共同交集也逐年至少 95%，
分母明确为该年 canonical prediction keys；label 有限率另列，不能将它混入预测覆盖率。
低于门槛不能通过只报高覆盖子样本宣布某臂胜出。
成对交集结果可作附录描述，不替代预注册的全臂共同样本 primary。

### 13.2 预先限定的 contrasts 与 multiple comparisons

建议只注册以下六个正式差值方向；方向是“前者减后者”，检验仍为双侧。
四个 anchor contrasts 和两个表示机制 contrasts 共用一个校正 family：

| 对比 | 研究含义 |
|---|---|
| S−B | 既有严格筛选身份相对 Broad anchor |
| R−B | 结构代表压缩的整体改变 |
| C−B | 组合表示能否直接替代完整 Broad raw anchor |
| H−B | 整体混合表示相对完整 raw anchor |
| C−R | 秩组合表示相对原始代表；包含变换和平均的共同作用 |
| H−C | 在同一 composite core 外加 raw representatives |

使用 paired daily delta `d_t = IC_A,t − IC_B,t`，不是对两个各自 IC 序列分别估计标准误后相加。
六个检验构成一个 family，alpha=0.05，Holm 校正；所有结果连同未通过者一起发布。
不再自动跑十个全两两 contrasts、每年九次显著性、每 Era 显著性或 worst-year 显著性作为新发现。
若某臂不可评分，该 contrast 按不可拒绝处理并保留在原 family 中，不因删去失败臂缩小校正范围。

增加 C−B 的代价可接受：它回答现有 C−R 无法单独回答的直接替代问题，例如 B>C>R。
同一共同样本上 `delta(C,B)=delta(C,R)+delta(R,B)`，但均值的代数关系不使其标准误或显著性可以直接相加。
无需新增臂或 fit，仅新增一个预定义检验。Holm 第一步阈值由 0.05/5=0.0100 变为
0.05/6≈0.00833；这说明检验更严格，不代表功效按固定比例下降，实际代价在揭封前不能从本项目数据估计。
Holm 可处理相依检验，因而不为这六个相关 contrasts 另拆 family；前提仍是各个输入 p-value 有效，
它不能修复小样本 HAC 近似误差或此前的选择偏差。
方法依据：[R stats 对 Holm/FWER 及相依性的官方说明](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html)。
H−R 未列为正式对比；不在结果出现后因为方向有利才补入。

### 13.3 时序依赖、区间与稳健性

沿用 V3 的 HAC/Bartlett 主带宽 20、敏感性 40；对原始交易日 lag 上的 paired delta 计算，
不能 dropna 后把相隔数月的观测当相邻。既有工具如压缩 NaN 日轴，必须先修适配并用 synthetic oracle 验证。
HAC 主带宽对应的双侧 p-value 用于 Holm；敏感性不得替换主结果。

保留 gap-aware moving-block bootstrap：block length 20、敏感性 40，1,000 次，seed=20260909，
所有臂共享抽样日期索引，在无缺口连续段内抽块，不跨 gap，不按最有利长度选区间。
bootstrap 区间是支持性不确定性证据；普通 95% 区间不冒充经过 Holm 的同时置信区间。
短片段无法提供完整块时报告其质量占比；如截去后估计目标改变，返回总体 CI unavailable。
九个年度不是九个 IID 样本；年度 pooled predictions 也不是独立标签观测。

### 13.4 Secondary 与明确不纳入的指标

Secondary 描述：非年化 ICIR=`mean/std(ddof=1)`、年度 IC、worst-year、负 IC 年数、
B=2015–2017/C=2018–2020/D=2021–2023 的 Era 均值、有效日/对数与覆盖率、特征维数、
原始依赖列数、fit/replay 时间与资源、表示缺失/有效家族数。
保留覆盖量纲，不能把 worst-year 改成“删去坏年后的稳定性”。

本版正式 P3 建议只评价预测，不纳入 portfolio、TopK、收益曲线、交易成本、Sharpe、回撤、
importance 或 SHAP。它们既未获本轮授权，也会扩大假说和可调自由度。
若将来需要经济回测，另冻结连续持仓的 evaluator；重叠 20D return 不得作为日 P&L 连乘。
本节不为未来 portfolio 阶段预设任何池胜者或策略参数。

### 13.5 什么结论可以成立

- 数量减少且 hash/重放通过：只能说工程降维实现有效。
- R−B、C−B 或 H−B 在上述统一校正后显著为正，且对应模型列更少、覆盖达标：支持该固定配置下的压缩表示改善，仍是回顾性条件证据。
- H−C 显著为正：支持新增冻结 raw 的增量价值；不能仅凭这一项定位到非线性交互还是尺度信息。
- C−R 显著为正：支持组合 pipeline，不单独证明 rank averaging 的降噪机制。
- 未拒绝差异：不等于相等或非劣；worst-year 更好但 primary 未支持，只能描述。

若要宣布“更小而基本不损失”，须在 outcome 前额外批准有业务含义的非劣 margin，并明确单位是绝对 daily Rank IC。
本版不凭空规定 0.001/0.002 或相对百分比，也不从 B 的未开封 IC 推算容忍度。
未批准 margin 时，不发布非劣声明，只报告差值及不确定性；拒绝无差异不能反向证明等价。
不自动选一个 winner，更不从当前开发样本推动 Strategy V2；可能的结论是 no-winner 或设计信息不足。

## 14. 封存、访问隔离与设计污染防护

### 14.1 规划路径的最小权限边界

建议实施时让 design 入口只接收经过列投影的 metadata bundle，不接收整个输出根目录。
允许文件：冻结 factor identities、canonical lineage、公式/参数、V0.5.1 semantic/alias、
2010–2023 feature quality 与 feature-only pair 证据、P0 日历和 P1 资格元数据。
Candidate Board 仅在一次性身份提取中读取 `factor/pass_count` 等必要列；随后只用身份快照。
deny：prediction scores、model.txt 的 split gain/count、importance、SHAP、IC/FDR/收益表、label caches、portfolio evaluator。
不要给 planning 入口导入通用 research runner 再依赖调用者“别点评价”。

保留哈希/回执校验独立的审计路径。只按 receipt 中的哈希或纯字节散列核验预测完整性，
不解析 scores；saved-model replay 由独立工程入口执行，结果只释放 exact/计数/边界结论给设计者。
模型文件本身可能含 gain 等信息，规划阶段连模型文本也不应浏览。
checksum 可证明文件未改，不能证明研究者从未观察过 outcome；应同时保留访问记录和人工声明。
应用级 reader guard 也不是对全权限用户的安全沙箱，不作这种承诺。

### 14.2 2024+ 持续封闭

所有研究值请求先验证 role、列、requested interval、effective interval 和截止日，再 I/O。
研究特征、标签、价格、prediction、coverage 值不得超过 `2023-12-29`。
沿用 protocol 允许的 metadata/hash/date 边界；不因 parent 文件跨年就扫描整个 Parquet 或 provider 全期价格。
跨 2021–2026 的 parent 只能通过有日期 predicate 的必要列投影访问。
如物理 row group 横跨边界，区分底层解码与向研究流程暴露的请求行；不得先读全表再过滤。

本轮没有调用 canonical 值 reader；后续 feature canary 也不允许顺手生成近期 coverage。
任何错误请求须在读取之前失败，不能先读出来再写 `recent_access=false`。

### 14.3 无结果反馈的规则

在揭封前同时冻结 taxonomy、direction、U、组成员、horizon thinning、排序、缺失、训练资格、臂数与评价合同。
设计版本每次修改写明 metadata/公式/文献依据，禁止用模型结果修改成员或符号。
若意外观察了项目 outcome，立即记录看过什么、影响哪些假说并停止；
不删除日志或换 RunId 后继续称 blind design。
2024+ 一直是另行授权事项，本计划批准任何阶段都不自动解锁它。

## 15. Inventory 的字段复用与待补项

| 要求字段 | 当前复用来源 | 尚需补充/审核 |
|---|---|---|
| factor_id/source/formula | working_set、V0.5.1 semantic、canonical lineage | 不改父身份；逐列完整算子核对 |
| theme/subtheme/measurement family | 已有 proposed_family/mechanism | 文献 crosswalk、组内共同轴、跨 source 同机制关系 |
| direction | 仅记录未导入 Primary 方向 | orientation、expected-return sign、证据等级、文献页/公式、审核理由 |
| horizon/window/units | V0.5.1 真实参数及公式单位 | lag 与 window 分型、分子/分母、递归 anchor、会计更新周期 |
| dated availability | canonical authoritative semantics/已接受限制 | 逐类事件字段、信息可得日期、warmup、状态连续性；不可把 schema_start 当首个可用值 |
| coverage | 旧 Full/四 Era feature-only 质量表 | 后续仅用合法 train 做新表示资格与缺失旁表 |
| unresolved | semantic_resolved/hold reason | 是否 raw-only、是否 correctness blocker；不能以 unknown 字符串建同类 |
| exact duplicate | V0.5.1 五组登记 | 作用域、mask、表示类型及跨库节点权重去重 |
| statistical cluster | V0.5 原 Full 四层级标签 | 仅作证据索引；使用时须补对照具体 pair/Full/Era 合同 |
| dense lag family | 根据真实 factor_id 与公式表核实的五组 | bucket 与 thinning 拟议规则、输出依赖映射 |
| R/C/H 角色与原因 | 本轮明确 pending | 审核后记录 include/raw/aggregate/alias/defer，全部 494 行均有去向 |

当前清单中的 `measurement_type` 复用了已有单位分类，只是起始字段，不是已完成操作符分类。
`dated_availability` 是待细化的引用，`proposed_*`/`candidate_*` 是 pending；
不把表格填满的形式误称为已完成全部人工语义审核。
本轮不把 Strict 成员身份、旧 pass_count 或 outcome 排序加入代表选择字段，防止二次筛选。

## 16. 冻结文件、哈希和 provenance

沿用仓库的普通 JSON/CSV/YAML、Git 和原子发布方式，不新建注册平台。
建议未来独立运行根 `outputs/literature_factor_representation/<run_id>/`；正式文件名待实施批准。

| 拟议产物 | 最低内容 |
|---|---|
| `design_config.yaml` | 规则版本、截止日、dataset、scope、U 政策、rank/missing、horizon、代表政策、固定臂数 |
| `factor_inventory.csv` | 全部 494 身份、来源、主题与方向审核、角色及理由 |
| `representation_manifest.json` | 有序模型列；每列 raw/composite 类型、依赖 DAG、唯一节点/家族权重/符号、availability、精确 alias 作用域 |
| `freeze.json` | 父身份哈希、完整 design/列序哈希、文献版本/文件哈希、Git/runtime、批准人/日期、outcome 尚封闭声明 |
| `evaluation_contract.json` | primary/secondary、共同样本、六 contrasts、Holm、HAC/bootstrap、覆盖门槛、`noninferiority_enabled=false`、停止条件 |
| `access.json` 与工程回执 | 请求文件/列/角色/日期、边界检查、输入 slice hash、输出 hash、replay exact、失败原因 |

对 JSON 采用确定性的 UTF-8、键排序及有限数字规范；feature order 是显式数组，不靠 dict 排序代替。
因子身份哈希、表示配方哈希和实际值哈希分开，不能用“成员相同”冒充 composite 数值合同相同。
先写临时目录，验证后原子发布；已发布产物只追加新版本，不覆盖旧回执。

正式 freeze hash 只有人工批准具体名单/配方后才出现。
候选 recipe 可以并且必须有内容哈希，但其状态为 `candidate_for_human_freeze`；
哈希只说明内容可复核，不授予 D2 权限，也不意味着阈值/语义已获人工批准。
本轮 `AUDIT_METADATA.json` 是来源快照，**不得被 runner 当作正式 pool 授权**。
论文 PDF 保留本地，不将用户提供的全文自动推送到公共仓库；文档只发布出处、摘要和哈希。

## 17. 必须新增或复用的验证

本轮不编写生产代码；下表是实施验收要求，优先复用既有测试与数值 oracle。

| 测试组 | 必须抓住的反例 |
|---|---|
| 身份与确定性 | 494 行不丢失；B/S hash 不变；输入文件/列重排不改 recipe；相同配置生成完全相同有序列 |
| 方向 | close ratio 与 return 反向、已有负号、跨零倒数、unknown direction、收益/IC 列注入均不影响设计 |
| 相似关系 | A–B/B–C 近但 A–C 远；相同 unknown 不当同机制；Full 高但 Era 不稳；mask 不同拒绝等值 |
| family 权重 | 精确 alias 同值同 mask 时输出/分母不变；库名改变不变；近义 lag 在家族有效性固定时不增加名义组权重，但允许值改变；新增节点导致门槛变化须被捕获 |
| rank/reference | ties、binary、n_min−1/n_min、n=99/100 诊断点、constant、all-missing、Inf、单组、不同 mask；先全合法截面 rank 再按标签/训练 mask，与错误顺序明显不同 |
| 缺失 | 候选及最终唯一门槛的临界、固定分母、两家族可退化为一与三家族至少二的区别、状态 NaN 不补零、PIT 未发布不能出现；有效权重审计可复算 |
| horizon | lag0 与 window0、1/5/6/21/22/59 边界；空 bucket；同字段不同分母；不同 TA 多窗口不套单 lag 规则 |
| 日期与泄漏 | train label_end 恰等于 refit 边界必须 purge；2024 请求在 I/O 前失败；跨期 parent 不能无 predicate；禁止全期缓存 |
| 固定训练数值 | float64 Sequence、100 轮、列序、每日目标 rank、daily-equal 权重、any-finite mask；对不变 raw 配方与既有 authority 一致 |
| 独立 replay | 独立朴素公式实现重建 composite；再用 saved Booster 比较全部 keys/score/reason；不能共用生产 composite 函数作为唯一 oracle |
| 结果封存 | design 入口访问 prediction/model/evaluator 被拒；打乱/替换 IC、收益、importance 不改变 recipe；只有批准后的 evaluate 入口能读 labels+scores |
| 未来评价 | paired 同键同日、NaN 日轴不压缩、共同 bootstrap 索引、Holm family 固定、覆盖不足无 winner、末 21 日不评分 |

数学表达式的 reference 可用小型 synthetic 单日/多日数据做独立重算。
生产实现和朴素 oracle 可共享冻结常量/schema，不能共享 rank、orientation 应用、层级归约、
缺失门槛及 alias 处理的核心函数；关键结果还需手算小例子，避免两份代码重复同一理解错误。
故意改变 sign、ceil/分母、mask 或 alias 路径应使测试失败；比较包括全部值和 mask，不仅比较最终相关性。
真实 canary 应固定取样规则，不按相关性或模型表现挑日期；报告 CPU/RSS/临时磁盘和 missingness，
先做新表示的数值与资源资格，再交付用户自行执行的长运行命令。
若 runtime/精度改变，先证明等价或换版本，不能降低精度以通过资源门槛。

## 18. 分阶段授权、交付与停止点

| 阶段 | 工作内容 | 交付及停点 |
|---|---|---|
| D0：本轮 | V0.1 证据复核、人工意见评估与 V0.2 计划修订 | 保留原 494 行 inventory；**PLAN REVISED / D1 NOT STARTED** |
| D1：另行批准设计实施 | 逐列主题/方向/availability；U/R/C/H 配方；独立 oracle；rank/missing 结构诊断；唯一规则收敛 | `candidate_for_human_freeze` packet、全部成员去向、真实输出数；仍不开 outcome，仍未授权 D2 |
| D2：另行批准冻结与预计算 | 人工批准具体 recipe；资源 canary；用户运行最多 27 次新 fit 与独立 replay | 新池 prediction sealed；全部记录完整后再停 |
| D3：另行批准 outcome evaluation | 同时打开已冻结全部臂的成熟开发期 outcome，执行冻结 paired 评价合同 | 完整结果、失败/不确定性、无选择偏差粉饰；停止，无 2024+ |
| D4：本计划不授权 | 新时期研究、learned compression、portfolio、Strategy V2 | 各自独立问题、freeze 和用户授权 |

本版建议 D1 先形成数个可审阅的小批次：taxonomy/direction → dense-lag 与 U → composite/reference → freeze packet。
若共同 raw 部分过大，或需要在多个方案中凭主观偏好选一个，应先审核问题定义，而不是开展小规模 outcome pilot。
开发投入以少量函数、配置、集中测试为原则；耗时主要是不明语义和公式映射，不能靠增加框架替代。

### 18.1 D1 获授权后的验收包（本轮不生成）

- 494 行逐因子 audit：主题、子主题、measurement family、三种 direction 字段、方向证据、
  lag/window 类型、单位、分母、availability、hold/blocker、alias、统计证据及 U/R/C/H 去向。
  不以表格行数冒充语义完成；unknown 有明示处理，未决项列对象/数量/原因，不保留无解释的 pending。
- U 的逐项 raw 保留依据，R/C/H 各自有序输出、DAG、唯一成员权重、最终唯一 rank/missing 规则；
  H 严格来自 U+R(G)+C(G)，不由 importance 选择子集。
- 自然列数 F_R/F_C/F_H，拆分 U、raw reps、composite、rank singleton、精确去重、父依赖、主题/家族/尺度；
  Alpha360 单列结构分解。遇到 blocked 不能报一个假定其已通过的最终数。
- 第 9.4 节结构诊断、访问记录、资源估计与所有规则修订理由；抽样/全量边界明确，未运行的统计不能填零。
- `candidate_for_human_freeze` 配置和 manifests、recipe/content hashes、文献/来源、direction authority、
  拟议六对比评价合同与访问合同；tests/validators 报真实执行结果，不把本轮文档检查算作 oracle 测试。

D1 只有在规则唯一、所有相关资格已处理、独立验证通过时才可报告
`D1 IMPLEMENTED / REPRESENTATIONS READY FOR HUMAN FREEZE / D2 NOT AUTHORIZED`。
否则报告 `D1 BLOCKED / HUMAN DECISION REQUIRED`，保存未完成范围及候选内容；
不能自动剔除 blocked 成员、改 B/S 或调整模型以取得 ready 状态。

以下任一情况立即停止并请求针对具体问题的人工审核：

- 实现与论文公式、单位、PIT 口径或状态来源冲突；疑似未来泄漏/数据错误；
- 方向只能通过开发期收益决定；需要改变 canonical 或父池身份；
- 规则无法唯一决定一个成员的去向，或需要为压到某 K 放宽条件；
- 新表示未通过 train 资格、独立 replay、资源预算或访问边界；
- 需要改变固定模型/target/权重才能使小池或大池可用；
- 已观察到项目 outcome 或任何未授权近期研究值；
- 新增方法、margin、指标或 contrasts 会扩大预注册假说家族。

## 19. 人工审核应分别确认的决定

1. 是否接受五臂上限及旧 Baseline 仅作 provenance。
2. 是否接受 R/C/H 共享 raw 特殊项 U，从而 C 并非纯 composite。
3. 是否采用 economic-axis orientation，而不是要求所有组合都具有文献预期收益方向。
4. 是否以四尺度 bucket 和较低中位 lag 作为 D1 唯一默认候选，在真实公式/availability 验证后再冻结。
5. 是否采用单一 0.995 的高置信同语义同尺度替代资格，并保留 Full/Era、全 pair 和 mask 边界。
6. 是否采用 family-balanced 及显式尺度层级，并区分精确 alias 不变性与近义节点的名义权重不变性。
7. 是否采用 average ties、无 jitter、常数截面单列无效原因。
8. 是否接受 n_min 暂不冻结，以 100 作诊断参考线，按第 9.4 节结构证据提出一个最终规则。
9. 是否接受 50% 仅为缺失诊断候选，独立审阅各聚合层的语义稳定性后提出唯一政策。
10. 是否接受六个 primary contrasts、统一 Holm、现有 HAC/bootstrap 设置及本版不作非劣声明。
11. 是否单独授权 D1 的配方/工程实现；D2 和 D3 仍须分别批准。

这些是可评审的具体默认方案，不要求一次批准所有未来研究。
下一步若仅批准 D1，表示允许完善配方与工程验证，**不表示允许新模型训练或打开 B/S outcome**。

## 20. V0.1 交付边界与检索限制（历史记录）

本轮完成本地三篇论文正文提取、LWZ 补充材料 C.4 表格核对、JKP 附录 VII/IX 定位、
GKX 作者发表版及补充一手资料检索；没有把未获全文的补充论文细则当作已核实方法。
本地论文顺序及 SHA-256 见审计元数据；LWZ 附录临时副本仅用于本轮核对。

仓库只读取代码、文档、身份/语义/质量/关系元数据及既有运行状态；
没有读取 canonical feature/price/label/prediction scores，没有新增模型、pool、评价或 Strategy 修改。
既有 2010–2023 feature-only coverage 被明确标注为复用证据。

外部检索有一项范围说明：为定位 GKX 论文，作者主页的工具返回中夹带了与本项目无关的近期市场展示。
它未被用于本研究、未保存为研究数据，后续改用论文直链；因此本轮能确认的是
**未访问仓库 2024+ 研究数值**，不作“互联网返回内容绝无任何近期数值”的过度保证。
所有方案与经验结论仍只来自所列方法文献及允许的仓库证据。

正式池身份、新模型训练、prediction outcome、P3、近期数据和 Strategy V1/V2 均未解锁。
交付后等待人工审核与单独实施授权。

## 21. V0.2 人工意见评估与修订记录

结论：附件主要意见合理，尤其纠正了两个门槛被过早绑定及 C 缺少直接 anchor contrast 的问题。
本轮按用户实际请求只调整计划；附件第九节“现在开始实施 D1”和末尾代码/manifest 交付要求未执行。
这不是否定 D1 的内容，而是区分评估材料和本轮行动授权。

| 附件意见 | 处理 | 理由及对应章节 |
|---|---|---|
| 一：JKP、分层平均、economic-axis 三项原则 | 保留，补强 | 区分文献收益聚类与本地 feature-only；补精确/近义不变性边界；第 3、6、9 节 |
| 二：最多五臂、无最佳 K、不重训旧 Baseline | 采纳并保留 | 明确研究假说而非列数优化；六 contrasts 不增加第六臂；第 1、11、13 节 |
| 三：U 须逐项审核、blocker 不能保留 | 采纳，修正原文 | 撤去 61 hold 自动进入 U 的读法；未知收益方向不等于未知测量轴；第 10 节 |
| 四：dense family 核对、中心确定性、分辨率报告 | 采纳并精化 | 同 normalization/availability；较低中位 lag 免去浮点 log 并列误差；16 格仍是纸面计数；第 8 节 |
| 五：拆开五项决定 | 采纳 | 原第 5 项拆开；0.995 保守资格、family 平衡、ties 与两个待诊断门槛分开；第 7、9、19 节 |
| 五：新增近义 lag 的“不变性” | 部分采纳 | 保证固定有效家族下名义父权重，不承诺输出值或缺失归一权重不变；第 9.2 节 |
| 五：n<100、50% 的结构审计 | 采纳，修正计数与验收口径 | 叶 n 与输出 finite 数分开；三家族只剩一仍有效是错误；采样不能声称全年计数；第 9.3–9.4 节 |
| 六：增加 C−B、统一六项 Holm | 采纳 | 直接替代问题值得增加一次预定义检验；不增加模型臂；依赖与代数关系不取消检验成本；第 13.2 节 |
| 七：HAC/bootstrap 不再搜带宽 | 保留 | 原 20/40、1000 次、固定 seed 与日轴规则不变；不在本轮执行 evaluator；第 13.3 节 |
| 八：无 margin 不作非劣 | 采纳并显式化 | 本版 `noninferiority_enabled=false`；如将来改变需独立预注册；第 13.5、16 节 |
| 九：D1 具体工作内容 | 纳入待授权验收要求 | 全量 taxonomy、U、R/C/H recipes、结构 canary 及唯一规则；本轮不实际生成；第 18.1 节 |
| 十：独立 composite oracle | 采纳并补反例 | 不共享核心计算函数；手算例子、mask 和故意错误检查；第 17 节 |
| 十一、十二：outcome sealing 与 2024+ 封闭 | 保留 | 隔离 design 输入，边界在 I/O 前验证，疑似污染即停；第 14 节 |
| 十三、十四：D1 交付和完成/blocked 状态 | 纳入未来验收，不宣称完成 | candidate hash 不等于批准；全列状态/真实 counts/tests 必须实际产生；第 16、18.1 节 |
| 十五：允许基于结构证据修订 | 采纳但限制循环 | 可解释失败→审阅→单一修订→确认验证；不能借 feature-only 名义追 coverage/列数；第 9.4 节 |

本轮重新核验 V0.1 审计快照所绑定的来源文件哈希，未发现变化；没有重新解封预测或扫描特征值。
`STRUCTURAL_INVENTORY_494.csv` 和 `AUDIT_METADATA.json` 仍是原 V0.1 metadata-only 快照，
其 pending 保持原样，不作为 D1 完成证据；未来 D1 应另发布新候选附件，保留原快照。
本轮新增的一手方法核对仅为第 13.2 节 Holm 官方说明，未访问近期市场数据。

意见评估完成时状态：PLAN V0.2 REVISED / D1 NOT STARTED / D2–D3 NOT AUTHORIZED。
随后用户授权先提交计划、再实施 D1；实施状态由单独交付记录更新，不追改原审计快照。
