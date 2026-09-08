# Candidate Consolidation / Redundancy V0.5 开发计划

日期：2026-09-08。状态：**代表提案已交付，STOP FOR HUMAN REVIEW；价格单位与行业暴露缺项显式保留**。实施结果见 [实施进度](../reports/candidate_consolidation_v0_5/IMPLEMENTATION_PROGRESS.md) 和 [代表提案报告](../reports/candidate_consolidation_v0_5/REPORT.md)。以下研究边界继续生效。

本计划依据用户提供的《Candidate Consolidation - Redundancy V0.5 预研与规划任务》，结合当时远端最新 `main` 制定。初版审计基线为 `26715329cb51170b6f47580824137fa97d07565f`，后在 `b4ed882` 收敛复用方案。附件中的算法、阈值和流程作为设计输入评估；初版仅获规划授权，当前实施授权见K及实施进度。

建议采用：**全库存语义审计 → 494 工作因子的精确每日横截面相似性 → 跨时期结构检查 → 数值分组与经济解释 → 不使用收益排名的代表提案 → 人工审阅停止点**。不预设最终因子数量。V0.5 输出信息结构和提案，不发布最终 Core，也不删除库存。

## A. Current-State Audit

### A1. 已冻结交付与工作集核验

依据 [Primary V0 manifest](../reports/long_history_multi_evaluator_screening_v1/PRIMARY_V0_MANIFEST.json)、[Candidate Board](../reports/long_history_multi_evaluator_screening_v1/candidate_board.csv) 和 [因子审阅报告](../reports/long_history_multi_evaluator_screening_v1/review_v0/REVIEW.md)：

| 范围 | 数量 | V0.5 用途 |
|---|---:|---|
| 原定义库存 | 774 | 保留 identity 与 lineage；9 个 blocked 只列原因 |
| research-usable | 765 | 全部做定义、关系与经济语义覆盖审计 |
| 3/3 | 332 | 全部进入工作集，包括已有风险标注的30项 |
| 2/3 | 159 | 全部进入工作集，不以桶单调性分歧另设门槛 |
| incomplete 且 pass_count=2 | 3 | 保留离散/状态专项身份，进入相似性工作集 |
| **active consolidation working set** | **494** | 固定为原 Board 的 `pass_count >= 2` |
| 其余 research-usable | 271 | 保留语义记录；不是本轮全对相似性对象 |

三项 incomplete 为 `kunquant_alpha101_alpha071`、`ta_volatility_bbhi`、`ta_volatility_kchi`。原单体系通过并集是537，原 review queue 是559；两者都不是494工作集。不能用302项“无原有标注的3/3”代替工作集。

494 的来源为 Alpha360 287、Alpha158 85、TA 57、Alpha101 32、mature_public 21、project_basic 12。332项3/3中的226项Alpha360，与494工作集中的287项Alpha360，是不同分母。

当前可确认的是强烈的家族冗余线索，尚未确认多少独立信息组。8对 Alpha158/Alpha360 记录表达式相同，不等于已验证数值及缺失mask完全相等；26对研究可用 proxy/direct-VWAP 对应项也不是26组重复。相关证据见 [formula_overlap](../reports/long_history_multi_evaluator_screening_v1/review_v0/formula_overlap.csv) 和 [proxy_semantics](../reports/long_history_multi_evaluator_screening_v1/review_v0/proxy_semantics.csv)。

输入绑定至少保存：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
Primary candidate rule: 26559c272310fd361fcb0c8de4b658b77946058241e4bf26ede281a71d64950b
Candidate Board SHA256: edca91b2a8f3a5e54ffd9a8c1b69037f70832c1a8ec745a2dae02e2ceec7ca80
```

工作集从冻结 Board 可重建；实施时新增有序成员列表及其hash，不重写原 Board。

### A2. 代码与证据审计：复用到什么程度

| 能力与具体入口 | 实际实现 / 限制 | 本轮决策 |
|---|---|---|
| [canonical_dataset.py](../research_validation/canonical_dataset.py) | identity、分区有效日期、按列过滤读取 | 直接复用；调用前再与2010–2023请求范围求交 |
| [long_history_screening.py](../factor_research/long_history_screening.py) | 日期边界、键唯一性、单因子分区读取；preflight同时绑定label合同 | 复用边界/键检查；新增多列读取，不调用标签生成或照搬整体preflight |
| [inventory.py](../factor_universe_v2/inventory.py) / [duplicate audit](../reports/factor_universe_v2/duplicate_equivalence_audit.csv) | replacement关系、ret_5/rev_5、历史常数排除；部分历史行含hard_delete=True | 仅复用关系线索；历史常数排除不构成本轮删除许可 |
| [factor_dependency.py](../research_validation/factor_dependency.py) | Python AST判定横截面/时序依赖及保守lookback；不是代数等价证明 | 复用依赖证据；没有发现可直接通用的表达式规范化/等价AST引擎 |
| [expression_adapter.py](../factor_research/expression_adapter.py) | `normalize_qlib_expression_output`规范输出列，不规范公式 | 不把函数名误认作公式简化器 |
| [feature_eligibility.py](../model_research/feature_eligibility.py) | `_content_hash`转小端float64、规范NaN、绑定shape；profile按排序键后的内容hash找重复 | 借用数值hash逻辑，补keys/mask/日期绑定及流式计算；不导入ML eligibility入口和阈值 |
| [factor_similarity.py](../factor_research/factor_similarity.py) | `daily_exposure_similarity`按allowed_dates逐日Spearman，取**有符号相关中位数**；不输出pair overlap/Era分布 | 可作小样本参考；本轮需流式汇总、绝对值分布及缺失原因 |
| 同文件 `combined_distance` | 混合feature与performance绝对相关，NaN填0 | 不复用本轮距离构造；未知相似性不得被解释成相关为0 |
| [factor_clustering.py](../factor_research/factor_clustering.py) | SciPy `squareform → linkage → fcluster`，默认average | 复用底层函数；新增单元素、有限性、稳定排序及unknown处理测试 |
| [历史聚类入口](../scripts/run_factor_clustering_v1.py) | stable角色、feature+IC混合、强制一簇一代表；旧调用没有传当前必需allowed_dates | 只作历史证据，不作为本轮入口；不为此次规划修复旧入口 |
| [split-specific入口](../scripts/run_split_specific_clustering_v1.py) / [corrected配置](../configs/factor_clustering_corrected_v2.yaml) | exact development allowed dates；feature/IC权重0.5/0.5，average，distance cut=.30，pair observations100，performance dates40 | 日期审计思想可复用；旧split、stable_core资格、混合相似性和cut均不继承 |
| [representative_selection.py](../factor_research/representative_selection.py) | selection frequency .40、方向一致性 .25、FDR .20、coverage .15加权评分 | 明确含outcome，不复用评分及自动exclusion |
| [economic_sleeves.py](../factor_research/economic_sleeves.py) / [economic map](../reports/economic_multi_factor_research_v1/economic_map.csv) | map覆盖765；旧sleeve成员、方向、global coverage也在表中 | 白名单读取定义/经济解释；不导入历史sleeve选择、方向或全期coverage作为代表依据 |
| [neutralization.py](../factor_research/neutralization.py) / [preprocess.py](../factor_research/preprocess.py) | daily rank/zscore、amount proxy、bucket、日回归残差 | 参考暴露计算及样本检查；本轮不生成中性化新因子或重算IC |
| [external_style.py](../research_validation/external_style.py) | historical effective-date行业join、重叠歧义及schema检查 | 行业有可复用工具，但本轮开发期数据尚不足，见F |
| [style_attribution.py](../model_research/style_attribution.py) | 模型TopK、条件IC及受控收益诊断 | 不能原样调用；需要无模型/无label的日横截面暴露入口 |
| [8进程runner](../scripts/run_long_history_primary_full.py)、[io.py](../qlib_baseline/io.py)、[cache.py](../qlib_baseline/cache.py) | spawn、内层线程1、run lock、分片receipt、原子发布、断点校验 | 复用轻量I/O和执行模式；不用年×单因子任务/价格标签cache；不修改冻结runner来承载新任务 |

已查看相关 clustering、projection、canonical、feature eligibility、external style 测试入口。上述为入口、算法、配置和现有证据审计，不声称重新执行了全部历史研究。

### A3. 经济分类与数据能力纠偏

[原 taxonomy](../reports/factor_universe_v2/economic_taxonomy.csv) 有774行，完整覆盖765研究可用因子；已有经济map也完整覆盖765。覆盖完整不等于解释准确：`_taxonomy_revision`中按名字包含beta解释为systematic risk，会误伤Alpha158 BETA价格斜率；PriceTrend/价格比率也不能直接解释为趋势追随。

旧 exposure capability audit 报告“provider无市值/行业字段”、旧实时快照收集失败，不能推导为今天整个项目没有市值数据。canonical中的市值、换手及波动因子已经有2010–2023数据。反之，后来的 external PIT style产物虽然具备行业join，但日期元数据仅覆盖2024-08-01至2026-02-04的368日，不能拿来填本轮开发期。

### A4. 开源与现有代码的收敛审计（本轮新增）

用户补充方案的核心判断成立：通用算法交给成熟库，项目只维护 canonical 面板语义、pair-specific mask、Era 聚合和证据 provenance。审计后的复用边界如下；这不会改变 765/494、2010–2023 或 feature-only 主路线。

| 能力 | 决策 | 具体边界 |
|---|---|---|
| SciPy `squareform` / `linkage` / `fcluster` / `cut_tree` / `dendrogram` | **直接调用** | 层次聚类、切簇和可视化不自研；继续复用 `factor_clustering.py` 的 wrapper，补齐 complete/average、singleton、有限性、输入排序和未知距离测试 |
| scikit-learn `AgglomerativeClustering` / `FeatureAgglomeration` | **参考，不进主 runtime** | 可用于独立 parity/toy-data 对照；当前 SciPy 已满足距离矩阵合同，不为第二套聚类 API 增加依赖 |
| pandas / SciPy Spearman | **reference/oracle** | 用于 pairwise reference、ties/NaN/constant parity；不能直接替代 pair-specific 交集、Era、coverage 和 effective-date 适配层 |
| Feature-engine `DropCorrelatedFeatures` 等 | **参考/oracle only** | 只借鉴 label-free coverage、缺失、简洁性代表思路；其 samples×features 合同无法表达每日横截面、逐对 mask、PIT 和 Era，不新增 runtime 依赖，也不使用 target correlation/model performance |
| Riskfolio-Lib | **不采用正式依赖** | 其 dependence/cluster diagnostics 可作方法参考；canonical daily panel、pair mask 和 Era 仍由本项目产出，SciPy 已足够完成主聚类，避免扩大依赖面 |
| MlFinLab / Clustered Feature Importance | **仅参考公开方法** | 不复制受限代码；当前不做 cluster-level importance、模型、收益或 SHAP |
| `canonical_dataset.py`、`feature_eligibility._content_hash`、`factor_similarity.py`、`factor_clustering.py`、现有 receipt/atomic/resume | **direct reuse + small extension** | 复用边界读取、键/日期校验、数值 hash、已有日相关和 SciPy wrapper、执行可靠性；仅补多列流式读取、mask/overlap/Era/schema 与新入口，不修改冻结 Primary runner |
| 新增 custom code | **必须自研的最小层** | 一个 bounded multi-factor reader、精确 pairwise daily Spearman adapter/kernel、Full/Era streaming reducer、语义/暴露/代表政策 assembler；不新建 manager、registry、clustering 或 feature-selection framework |

因此，正式依赖仍只使用仓库现有 SciPy/pandas/NumPy 环境；**不新增 Feature-engine、Riskfolio-Lib 或 MlFinLab**。开源库负责成熟数学实现，项目负责金融面板的数据合同，不能为适配库 API 而 flatten 全局 complete-case 或丢失日期等权、PIT 和 overlap 证据。

P1 canary 必须增加三类 oracle parity：①显式交集重排的 reference 与 `scipy.stats.spearmanr`、`pandas.DataFrame.corr(method="spearman")` 在 ties、NaN、binary、constant 上对照；②现有 wrapper 与 SciPy 直接 `linkage/fcluster` 对照 complete/average；③ exact、递减单调、mask 冲突、近似随机列的 duplicate/alias synthetic 对照。Parity 仅验证实现，不改变主研究语义。

## B. Consolidation Research Contract

| 项目 | 合同 |
|---|---|
| 库存 | 774定义保持；765语义审计；494 active pairwise；9 blocked不进入数值任务 |
| 日期 | signal dates 2010-01-29..2023-12-29，共3382日；A 2010–2014、B 2015–2017、C 2018–2020、D 2021–2023 |
| 末端 | 使用2023年最后交易日的可用feature，不套用Primary标签成熟末端2023-11-30；不读取未来价格 |
| 股票集合 | canonical practical raw dated universe，以日期/股票键为准；不套用旧liquid2000新过滤，不改变canonical原始生成mask |
| 主依据 | 仅feature、实现/lineage、开发期feature coverage及预定语义；工作集本身源于已观察20D筛选，须承认是条件化研究 |
| sign | 使用原始feature值；相关的正负号独立保存，不用Primary收益方向给feature重定向 |
| 标签 | 主计算函数禁止接收labels、IC、收益、FDR或模型输出；原Primary状态只说明工作集来源 |
| recent | 不读取2024+因子、价格、收益、暴露值；目录/identity/calendar/date范围元数据可审计，不参与选择 |
| 代表 | 只提出representation建议，不给最终入池资格；不使用Primary IC或其他outcome作tie-break |
| 解释限制 | 全部是回顾开发证据；不证明独立Alpha、可交易增量、因果机制或fresh OOS |

读取分区必须先对 `effective_start/effective_end` 与请求日期求交，再把边界传入parquet过滤。部分parent文件跨越2024+，不能全表读取再过滤。记录所读取的有界列、键、日期及slice hash；完整parent identity可以使用原receipt，不为“验证”重新解析所有recent数值。

## C. Redundancy Taxonomy

关系表采用有类型的pair/组注释，不把所有关系塞进同一个互斥cluster编号。

| relation_type | 最低证据 / 作用 |
|---|---|
| exact_duplicate | 同一有界key axis上值及finite/missing状态逐项相同；hash仅定位，回查相等确认 |
| algebraic_equivalent | 明确变换与定义域证明；记录窗口、字段、单位、PIT和mask条件；实际实现不一致另标conflict |
| rank_equivalent | 固定单调增/减关系及共同mask；实证完全同序与公式证明分开记；有限样本同序不冒充普遍等价 |
| high_numerical_redundancy | 每日相似性、跨Era和overlap支持；只表明数值接近 |
| window_family_variant | 同字段/操作、不同lookback或lag；保留时间尺度，不自动等价 |
| semantic_overlap | 同经济解释但尚无数值重复证明 |
| shared_risk_exposure | 共同规模/流动性/波动/价格暴露；不是等价或删除规则 |
| no_redundancy_detected | 在本合同及观察期未检出；不称“已证明independent signal” |
| insufficient_overlap / unresolved | 样本、定义域、实现或语义不足，不能下结论 |

`evidence_status`区分 hypothesized、formula_supported、empirically_verified、conflict；另保存 `mask_equal`、`sign_relation`、`valid_domain`、`verification_scope`。严格递减关系不能跨不连续定义域推广，例如1/x必须限定同一正值或负值区间；x²在跨零样本上不是严格单调变换。

V0.5不新建通用符号计算系统。先用明确的字段/算子/窗口描述和人工核对的有限规则；无法解析的Alpha101/TA定义保持unresolved。公式相同但mask不同只能叫formula alias with mask conflict，不并入可替代的exact组。

## D. Similarity Design

### D1. 正式建议：精确pairwise每日Spearman

对交易日t与因子i、j，先取canonical当日股票集合内的共同有限值样本 `M_ij,t`，在这个交集内分别用average ties重排秩，再算Pearson(rank_i, rank_j)。共同有效样本少于50、任一列常数或无数据时rho为缺失并记原因。保留binary/tied/state因子，不做qcut，不填零，不抖动打散并列值。

每个pair、每个Full/Era输出：

- mean_signed_rho、median_signed_rho、mean_abs_rho、median_abs_rho、q10_abs_rho；
- positive/negative/zero日期比例，`sign_consistency=max(n_positive,n_negative)/valid_dates`，零相关不计入同号；
- expected_dates、valid_dates、valid_date_fraction、invalid原因计数；
- n_common的min/median/q10；每日n_common/n_universe及Jaccard overlap的mean/median/q10；
- pair只在少量稀疏样本上可比的标志，年度feature coverage供解释。

所有日期等权，Full直接汇总全部日值，不平均Era中位数，不对缺失rho填0，也不把后期较多股票作为更高日期权重。Full是等日期而非等Era；同时展示四Era，防止长时期掩盖短时期。`median(abs(rho))`和`abs(median(rho))`分别代表不同事情，必须区分。

### D2. 其他方案的定位

| 方案 | 判断 |
|---|---|
| pooled date×stock Pearson | 混合跨期量纲、价格水平及股票数量权重；不作主相似性 |
| 每日Spearman再跨日汇总 | 对应横截面排序用途；主方案，但不能覆盖全部数值幅度/非线性信息 |
| 每列先在各自有效股票上rank，再共同样本矩阵乘法 | mask不同时不是上述精确Spearman；只能明确命名为近似，不能默默替代 |
| 同mask组rank+矩阵乘法 | 数学上可精确复用；首选加速路径 |
| pair-mask交集分组 | 对mask组G/H的交集重新rank，再矩阵乘法；能保持精确语义，但mask很多时可能退化 |
| pandas逐日 `corr(method='spearman', min_periods=50)` | 转换inf为缺失后作参考/精确fallback；需要测试版本下与显式交集reference一致 |

实施先做精确reference与同mask分组优化。跨mask分组过多时使用精确fallback，不因为耗时而自行改成抽样日或全局complete-case。rank的平移/缩放不影响相关，但全局预排序后仅删行通常会改变秩间距。

### D3. 时间稳定性及可比性

先计算数值，再按**预先锁定的诊断规则**打注释。建议默认的可比性条件：一个视图有效日比例至少80%，且有效日中共同样本覆盖的q10至少50%，每有效日至少50只；Full和各Era分别判定。这些是研究解释门槛，不是candidate门槛； rationale是避免用少量日期/小样本声称长期可替代。实施canary阶段须检验稀疏与state反例，正式运行前保存配置及理由。

对每个诊断相似性等级L（.995/.95/.85/.70）：

- stable_redundancy_at_L：Full及四Era都可比，median_abs>=L、q10_abs>=L、sign_consistency>=.95，并且各Era主符号一致；只表示此定义下的稳定数值冗余。
- regime_dependent：各Era可比，但不同Era是否达到L不同，或Era主符号变化；保存连续差值，不只给二元标志。
- insufficient_overlap：任一必需视图不满足可比性；不改成弱相关。
- 其余记 no_stable_redundancy_at_L，并保留Full高相关但日内时间波动等具体原因。

门槛是待实施前确认的配置提案，不宣称本次已冻结。near-rank-equivalent只是.995层的描述，绝不是严格rank-equivalent证明。

## E. Clustering Design

推荐 **complete linkage作为主诊断、average linkage作为对照**。Full distance为 `1 - median_abs_rho`；另构造跨Era保守相似性 `min(S_A,S_B,S_C,S_D)`，输出独立的stable structure view。Full高相关簇不能自动获得stable身份。

| 方法 | 采用方式 |
|---|---|
| complete | cut下约束所有成员pair的最大距离，避免链式合并；对噪声更敏感，需Era/q10对照 |
| average | 保留整体相近的窗口家族，但允许某些成员pair不够近；仅对照，不能声称直径保证 |
| single / threshold graph连通分量 | 能描述相邻lag路径，但A≈B≈C不能证明A≈C；作为family邻接图，不作为可替代集合 |
| Ward | 不选为主方案；本轮绝对相关、pairwise缺失及跨日median构造不保证欧氏距离 |
| k-means / community detection | 需要额外嵌入或参数，且无当前必要性；暂缓 |

未知distance在导出矩阵保持NaN及reason。为complete计算可临时置为sentinel=2（合法distance最大1），只解释cut<=.30下已形成的簇；跨unknown合并节点不作研究含义。average对照不能直接平均这个sentinel：只在已确认所有pair可比的主簇内做局部对照，另报告不可比成员，避免unknown被平均稀释。

不确定单一删除cut。固定输出四个诊断层级的distance cut=.005/.05/.15/.30，并展示完整树及成员关系；无“选出最好看层级”的步骤。主展示按这些层级并列，不从中选生产池。若未来要将某个cut用于自动准入，另写rationale、冻结规则并在查看该规则最终数量前锁定，不能据本轮已观察cluster数量倒推。

稳定性输出：Full对各Era及leave-one-era-out的pair co-membership保持率、成员交集Jaccard、可比pair分母、最大簇内距离、最弱pair。label-free的稳定不等于收益稳定。缺失成员不能作为“分组不同”或“完全稳定”的证据，须同时报告eligible subset大小。

用排序后的factor IDs保证输入顺序稳定；cluster ID使用view/level/成员hash，避免把SciPy任意编号当跨Era同一个簇。数值簇与window/economic family多对多关联，允许一个经济机制跨多个簇。

## F. Economic / Exposure Integration

### F1. 语义表必须逐行可追溯

复用旧taxonomy与economic map，但在新的 `economic_semantic_review` 内追加 original_family、proposed_family、mechanism、formula_units、horizon、intended_role、name_formula_mismatch、reason/source、review_status。原始记录不修改。沿用已有上层分类，补充 Reversal/Momentum、ResidualRisk、PriceLevel、TechnicalState、Intraday、RiskControl、Ambiguous 等subfamily或role；不另起一套不兼容的大taxonomy。

重点修订建议：Alpha158 BETA为归一化价格斜率；Alpha360 CLOSE lag为历史/当前价格比，机制方向要与公式解释分开；ATR和原始均线/通道/PSAR标记价格量纲；bbhi/kchi标记事件状态；proxy/direct-VWAP标记字段语义分叉。数字相关不能覆盖这些差异。

每个数值簇生成members、候选机制、成员语义一致性、冲突成员、可能共同暴露和unresolved原因。语义冲突允许提案暂缓，不强制给每簇一个经济名称。

### F2. 无label风险暴露的最小范围

复用D中的每日pairwise Spearman内核，计算494因子相对固定controls的有符号暴露。controls即使不在494也可作为诊断列加入，身份为control_only，不借此扩大active selection set。

| 维度 | 优先control | 当前数据证据及限制 |
|---|---|---|
| Size | mature_log_total_market_cap | canonical2010–2023各年有值，最低年度feature coverage约88.30% |
| Turnover | mature_turnover_mean_20 | 同期各年有值，最低约88.30%；不是完整可交易性判定 |
| Trading activity | amount_mean_20 | 各年有值，最低约72.72%；不能直接叫成交容量 |
| Liquidity | mature_amihud_illiquidity_20 | 各年有值，最低约88.77%；预期机制本身就是流动性 |
| Volatility | mature_realized_volatility_60 | 各年有值，最低约89.10%；与风险控制用途分开解释 |
| Price level | 同日有界provider close | 需要先核对复权/单位语义；若只能得到复权close，命名adjusted_price_level_proxy，不冒充名义股价 |
| Industry | 默认 unavailable_for_development | 已有行业工具和晚期产物，尚无已验证2010–2023覆盖；不调用旧采集任务或把当前分类回填 |

年度数字来自已封存 `primary/evidence_v0/data_quality_by_year.csv`，不是本次重算，不能代替实施时的pairwise overlap。canonical财务PIT为practical reconstructed PIT，不能升级声称原始数据库历史vintage完全可得。

行业只在未来找到并验证开发期effective-date数据后追加有界注释，必须保留coverage、重叠区间歧义和vintage限制；本轮默认不阻塞其他产物，也不为补齐行业开展新数据工程。

输出每个factor-control的Full/Era signed rho、abs rho、overlap及self_comparison；自身作为control时相关1是定义事实，不是风险发现。cluster仅汇总成员分布及异质性，不先合成一个收益导向cluster score。`exposure_dominant`若使用.85等描述等级须与配置绑定，且必须区分intended、possibly_unintended、unresolved。边际相关不等于已剥离共线性的独立暴露，更不证明独立Alpha。

## G. Representative Policy

采用可审计的**分层资格 + 字典序规则**，不设收益综合评分：

1. 是否有未解决的PIT/字段/定义域/实现冲突；有冲突则proposal_deferred，不通过比较IC解决。
2. 是否有明确authoritative semantics及已验证的canonical实现；不同VWAP口径不能因某个过了3/3就优先。
3. 在机制与角色可比的成员内，优先更完整的开发期feature coverage：先最差Era coverage，再全期coverage；不使用IC样本覆盖或2024+global coverage。
4. 更少非预期缺失/数值异常，再比较可解释的公式复杂度、实现稳定性；状态型定义固有NaN单独分型，不按普通坏数据处罚。
5. 同一语义层级内用feature-distance medoid；最后按factor ID稳定排序。medoid不读取收益。

规则顺序、复杂度计数方法与语义冲突名单在全量代表提案前锁定。风险暴露只作为审阅注释，本版不按“暴露低”自动优先，避免把本来有意表达的Size/Liquidity机制筛掉。**不采纳附件中“最后用Primary evidence tie-break”的可选建议**：本轮完全不需要这一步。

按关系分开处理：

- exact / 已证明且mask相同的rank-equivalent：提出一个canonical representation及完整alias表；rank反向只记录representation sign，不改Primary analysis_direction。数值加权用途可能不同，不能宣称替换对所有模型/组合无影响。
- near-exact tight cluster：给一个主提案和必要的语义/样本备选；备选必须有不同信息条件的具体理由，不能预定“一定保留两个”。
- horizon family：保留所有现有horizon标签；先去同horizon的确定性重复，其他窗口只提出分组/medoid与待审阅关系。不从收益选择5/10/20/40/60中的赢家，不强制每family一个代表。
- state、mask不等价或时期不稳定的pair：保留单独身份，标conditional/deferred；不能因Full相似自动折叠。

`representative_proposal_board`对全部494行保留 proposed_representative / alias_proposal / retain_horizon_variant / conditional / deferred 等状态，另提供少量group摘要便于人工审阅。不能只交“被留下的名单”而让其余因子失踪。

## H. Validation Plan

| 验证 | 必须检查的性质 |
|---|---|
| synthetic x/x、x/-x、正值x与1/x、x与exp(x) | exact与monotonic inverse分开；同mask相关±1；符号不依赖Primary方向 |
| x²跨零、不同窗口、独立随机列 | 不误认普遍等价；高相关与机制独立不是二选一 |
| missing-mask反例 | reference先交集后rank；验证全列预rank删行可出错；优化内核精确回退 |
| ties、binary、constant、全缺失、inf | average ties；常数/样本不足有reason；无补零、jitter或qcut |
| key/日期 | 重复键失败、缺失分区失败、effective interval拼接、2024越界在读取前失败 |
| 时间反例 | A/B高相关C/D变弱；全年符号翻转；Full abs高不误标稳定等价 |
| clustering链式三元组 | A-B/B-C近而A-C远，complete不能全并；unknown不能连接成可替代组 |
| 已知8表达式对 | 先按2010/2015/2018/2021/2023有界日期比较mask和值；不因公式字符串一致跳过验证 |
| Alpha360结构 | 对494内287项比较lag与字段结构，连同85项Alpha158的已知映射；不把226当完整规模 |
| ret_20/ROC20/CLOSE20、21D reversal | 公式域、真实mask、精度及window差异；记录冲突而非强行消除 |
| VWAP与状态案例 | proxy/direct独立identity；bbhi/kchi事件有效样本；PSAR mask含义 |
| 执行等价 | 1/8进程相同输出、输入重排不变、kill/resume不重复、损坏receipt被拒、确定性reduce |
| outcome隔离 | 改写/移除IC、FDR、收益及analysis_direction不改变主矩阵/cluster/代表；工作集名单单独固定 |
| 冻结保护 | Primary manifest的所有tracked文件逐hash不变；765/774集合不丢行；不访问recent值 |

数值核心以float64计算，对reference使用 `atol=1e-12, rtol=0` 初始容差并保留误差最大值；分类边界附近不靠四舍五入跨线。分布汇总规定quantile线性插值及有序日期reduce。若版本/并行变化影响边界分类，先修一致性，不挑结果。

先synthetic，再固定日期canary，最后全量。真实canary建议四Era各取该Era首、中、末交易日，每日全494；用于mask/性能/结构校验，报告真实日期，不能按相关结果改抽样。额外已知case允许补查具体日期，需记目的，不能用来选择cut。

## I. Compute Plan

### I1. 已核验规模与本次有限测时

494×493/2 = **121,771 pairs**；3382日上最多 **411,829,522 pair-days**；每列每日基础rank共 **1,670,708 factor-days**，异mask时会增加重排次数。

封存年度质量表中，alpha158_BETA10的参考key规模为6,640,610 date×stock rows；本次尚未逐键核验全部494列的axis一致性。以此估算494列float64裸值约26.24GB，另有keys/mask/ranks及pandas开销；当前机器16逻辑CPU、约27.78GiB物理内存，不能把全期矩阵复制给8个进程。参考日均横截面约1964只，和按“全市场5000只×14年”粗估明显不同；仍以canonical实际键为准。

通过partition manifest筛选有开发期交集且含工作因子的428个parent文件，文件尺寸合计约22.94GB。该数是**完整parent文件大小**，包含部分有效日期以外的字节，不是实际需解析的feature slice大小。仅读取本次所需日期与列，投影cache尺寸须真实canary测量。

本次只做了两个synthetic单日内核测时：本机research Python、固定seed20260908、2000×494独立正态值、内层线程1、pandas Spearman、min_periods50；无真实factor值、无聚类和label：

| 数据 | 单日耗时 | 3382日单进程线性外推 | 理想8进程下限 |
|---|---:|---:|---:|
| 无缺失 | 0.437秒 | 0.41小时 | 约3.1分钟 |
| 独立5%缺失 | 24.293秒 | 22.82小时 | 2.85小时 |

两次单样本测时只说明missing-mask可能是主要成本，未测8进程真实吞吐、I/O、缓存构建和尾部任务，不能承诺“3小时跑完”。安排上先留**数小时至一天**的计算窗口；真实canary后按每Era工作量和实测8进程吞吐报告ETA区间。不能把上次Primary约2.5小时直接当本任务耗时。

### I2. 推荐执行形态

1. 先按月有界读取：每个被引用分区一次读取该月所需多列，按唯一date/instrument键对齐；如果key axis不一致，报出差异，不能默默inner join缩小股票集合。
2. 日为数学计算单位，月为调度/断点单位，共最多168个月；每日同mask组共享rank及矩阵操作，跨mask走精确fallback。8个spawn worker，BLAS/OMP线程1；一次只处理有限月份。
3. raw月矩阵约0.17GB量级（日均1964×约21日×494×8）；考虑多份对齐、rank与临时数组，先给每worker 1–1.5GiB预算，总RSS目标不超过18GiB，保留系统余量。内存超预算按更小日期块处理，不能降低计算精度或丢因子。
4. 8-worker benchmark报告wall time、RSS峰值、读取GB、cache命中、mask组数量、fast/fallback pair比例；把投影、相似性、汇总分别计时。可优化批次和I/O，不改变sample contract。
5. 保存上三角日rho/共同样本计数/状态的二进制分片或Parquet，用整数factor index避免重复长名字。411.8M个float64 rho约3.29GB；加uint32 n_common约1.65GB，另有压缩/状态/coverage开销，预留日证据5–10GB、全部临时及产物约30–50GB磁盘，实施前检查可用空间。
6. Full/Era按pair块从日证据汇总，中位数必须跨所有原始日值精确计算，禁止“中位数再取中位数”。单个494×494 float64矩阵约1.95MB；5视图pair汇总608,855行，宽表不放全部Git。
7. receipt绑定dataset、working set、日期/键/列、算法配置、代码和版本；写临时目录→校验→原子发布。已有run锁阻止双写；损坏分片可单独重建，已完成分片经hash确认后跳过。
8. 非阻塞进度status记录月份、完成日数、pair数、耗时、ETA；完整执行留给用户外部PowerShell，保证不依赖本次对话存活。后续实现完成并验证CLI后再交付确切启动/恢复命令；本计划不提供尚不存在的可运行命令。

不采用121,771个独立pair任务重复读盘，也不沿用Primary的年×单因子Qlib初始化方式。本轮读取canonical feature即可；价格control单独有界构建，不创建未来收益cache。

## J. 实施顺序与交付物

### J1. 工作包与停止条件

| 工作包 | 开发内容 | 验收与后续动作 |
|---|---|---|
| P0 合同/语义基础 | 重建494名单；765语义表；9 blocked；关系编码；保护输入清单；有限公式alias | 数字、hash、成员身份、数据边界一致，未生成最终pool |
| P1 精确内核与canary | 多列有界reader；pairwise reference；same-mask优化；synthetic/固定真实canary；1/8-worker比较 | correctness先通过；记录资源与ETA，固定诊断配置/代表政策；失败则停在修复/评估 |
| P2 全量相似性 | 494开发期所有pairs、Full/四Era、coverage、日证据、exact alias复核 | 可恢复、样本原因完整、reference一致；与原765/494完整映射 |
| P3 结构与解释 | complete主视图、average局部对照、Era/LOO稳定性；经济修订；固定风险controls | 不导入labels；unknown不被称独立；family与cluster分开 |
| P4 代表提案 | 冻结label-free排序、全部494行proposal board、group摘要、原始证据hash复核 | **STOP FOR HUMAN REVIEW**；无自动Core/模型入口 |

开发粒度建议收敛为2–4个可审阅提交：合同与 oracle/synthetic；多列 reader、pairwise kernel 与 canary；全量 runner/汇总；结构解释与提案。新增核心算法代码预计为少量 adapter/kernel 加 reducer，聚类、Spearman 数学、hash、receipt 和 taxonomy 均复用现有实现。依赖安装为零；若仓库环境缺少 SciPy/pandas/NumPy，应修复环境锁定而非在项目内重写算法。

按个人研究项目的成本尺度，实施排期可从原先宽泛的3–5个工作日收敛为约2–4个工作日开发与审阅：P0/P1约半至一天，P2约一天（取决于真实 mask 分布和 I/O），P3/P4约半至一天。该估计不包含全量运行墙钟时间；真实 8-worker canary 前不承诺 full ETA。若 canary 显示 pair-mask fallback 过多，只优化批次/读取和 reducer，不降低精度或改变样本合同。

先用少量新文件承载独立入口：建议 `factor_research/candidate_consolidation.py`、`scripts/run_candidate_consolidation_v0_5.py`、一个YAML及集中测试；复杂度增长后再分离numerical/semantics模块，不引入新manager或注册框架。保留已有历史入口与冻结文件。以上文件名为拟建，不是已存在命令。

### J2. 产物schema

运行时根建议 `outputs/candidate_consolidation_v0_5/<run_id>/`；compact审阅产物放 `reports/candidate_consolidation_v0_5/`。不写入Primary的evidence/candidate/delivery目录。

| 产物 | 主键 / 最低字段 |
|---|---|
| working_set.csv | factor；original_agreement、active_reason、source、input_board_hash；494行 |
| inventory_semantic_audit.csv | factor；research_usable、active、definition、lineage、audit_status；774行，其中765审计、9blocked |
| formula_alias_map.csv | factor_a/factor_b/relation_type；条件、字段/窗口、mask、proof_status、code_reference、核验范围 |
| daily_similarity分片 | month/date/pair_id；rho、n_common、invalid_reason；另存daily factor finite_count和universe_count以重建coverage |
| numerical_similarity_matrix | view、ordered factor axis、median_abs矩阵及availability矩阵；矩阵NaN保留 |
| pair_similarity / era_similarity | factor_a/factor_b/view；D1所有统计、overlap状态、evidence位置 |
| cluster_membership.csv | view/linkage/level/factor；cluster_id、comparable_status；singleton不称independent |
| cluster_stability.csv | view/level/cluster；pair保持率、Jaccard、可比成员分母、worst_pair、Era/LOO关系 |
| economic_semantic_review.csv | factor；原/建议分类、单位/窗口、机制、冲突、依据及review_status；765行 |
| cluster_economic_summary.csv | view/level/cluster；mechanism候选、同质性、horizon分布、冲突及主要暴露 |
| risk_exposure_annotations.csv | factor/control/view；signed/abs统计、overlap、self_comparison、intended/hidden/unresolved |
| representative_proposal_board.csv | factor；group、proposal_role、representative、label-free排序各分量、reason、alternatives、user_decision=pending；494行 |
| run_manifest.json + status.json | 复用项目已有轻量写入模式；输入/配置/代码/输出hash、计数、访问范围、阶段和恢复状态 |
| REPORT.md | 结构发现、未解决项、数据/计算限制、原Primary不变及人工停止点 |

大矩阵、日pair证据放runtime，Git只保留manifest、schema、汇总与便于人工审阅的表；单文件不超过仓库5MiB限制。重要重复必须能从compact提案追到日证据，不靠截图作为唯一证据。

### J3. 非必需增强：默认关闭

**Label-based co-behavior**：若后续启用，独立只读原封存2010–2023的daily IC/jqfactor return/Qlib LS，计算共同有效日上的序列相关及overlap；保存annotation_only。必须先锁定主矩阵、分组及代表提案，再追加这些列，不能反向影响规则、身份或代表；不重跑收益筛选，不打开recent。

**PCA/effective dimension**：本版默认暂缓，不阻塞提案交付。pairwise median/absolute correlation不保证PSD，不能直接把其eigenvalues叫PCA方差解释率。可选增强须明确一致的rank-standardized样本矩阵及缺失策略，用等日期权重的PSD Gram/SVD诊断，报告受限样本覆盖和50%/80%/90%解释率；complete-case若严重缩水则不出一个貌似全494的“有效维度”。不把PC替代原因子，不用PCA维数决定保留数量。

## K. STOP POINT 与成功标准

用户于2026-09-08明确要求“请按照计划开始实施”，已授权按P0–P4推进。长时间全量执行按用户此前偏好交付外部PowerShell命令；P4生成Representative Proposal Board后停止，不自动进入10D、2024+、Core、经济组合、LightGBM、Structured ML、TopK/调仓优化或Strategy V2。遇到数据correctness blocker只诊断并说明影响，不自行改写Primary或重新筛选。

验收按可解释性与可重现性，不按压缩数量：确定性重复/实证同序/近似家族分开计数；全部active成员可追溯；跨Era不稳定及overlap不足显式展示；每簇有机制或明确unresolved；代表规则无label；765库存和Primary冻结字节保持；人工能优先看group摘要并展开每个成员。

## L. 外部预研核验与取舍

以下只支持方法选择，不把其他市场的研究结论当作本项目的实证结论；2026-09-08查阅官方文档、论文发布页及作者资料。

1. [scikit-learn官方示例](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) 确实演示Spearman、绝对相关距离、层次聚类及代表选择。但示例使用的是Ward，并且有看树选cut及模型重训步骤；不是complete linkage的官方推荐，也不是本轮可直接套用的研究合同。
2. [SciPy linkage文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html) 要求Ward等方法使用欧氏距离。本项目的聚合绝对相关距离未满足此保证，因此选择complete是针对本地合同的工程/统计判断。
3. Dong的 [Economic aggregation of return signals in global markets](https://www.sciencedirect.com/science/article/pii/S0927539825000854) 发布页检索摘要支持84信号、5经济组合及经济/数据聚类互补；全文打开失败，本次未独立复算论文。可借鉴经济解释与数值结构对照，不继承五组、组合权重或预测效果。
4. Kozak、Nagel、Santosh的 [Shrinking the Cross Section](https://www.nber.org/papers/w24070) 支持“少量主成分可能概括许多信息，但极少特征的稀疏表示可能不足”；不据此预设494压到20或50。
5. Lettau、Pelger的 [Estimating Latent Asset-Pricing Factors](https://www.sciencedirect.com/science/article/pii/S0304407620300051) 及 [作者研究页](https://mpelger.people.stanford.edu/research) 对应收益定价目标下的潜在因子研究。本计划保留“统计方差解释不等于收益相关信息”的限制；其收益面板方法不直接迁移成特征矩阵的选择标准。
6. Feng、Giglio、Xiu的 [Taming the Factor Zoo](https://www.nber.org/papers/w25481) 强调在既有高维因子之外检验贡献及简单LASSO选择不稳定。本轮借鉴避免把模型选择当去重真理，不运行该label-based方法，也不声称feature-only相似性已经检验了增量定价能力。

## M. 附件25项审计问题索引

| 问题 | 本计划结论位置 |
|---|---|
| 1 active set | A1：494，原pass_count>=2 |
| 2 duplicate/proxy/alias | A1/A2/C：已有关系和8对表达式、26对可用VWAP，须分型验证 |
| 3 AST规范化 | A2：有依赖AST，无通用等价证明器 |
| 4 numerical hash | A2/C：复用内容hash思想，补keys/mask和回查 |
| 5–6 旧聚类位置/合同 | A2/E：mixed IC+feature、average、旧split；不继承 |
| 7 daily correlation | A2/D：已有精确日Spearman，新增abs统计/overlap/streaming |
| 8 exposure/neutralization | A2/F：已有工具，入口包含模型/收益，须分离 |
| 9–10 taxonomy覆盖/误义 | A3/F：全覆盖，BETA/价格比/价格线/事件/VWAP要修注释 |
| 11–12 outcomes/新入口 | A2/B/J：旧流程用outcomes，新feature-only入口必要 |
| 13 多因子读取 | B/I：effective-date按月、多列列裁剪、键对齐 |
| 14 成本 | I：121771 pairs、411829522 pair-days、真实元数据与synthetic测时 |
| 15 rank矩阵加速 | D2：同mask精确，异mask交集重排或fallback |
| 16 分块 | I：月调度/日计算/pair块汇总 |
| 17 8-worker/cache/resume | A2/I：复用执行模式，改变任务粒度，不带入标签cache |
| 18 overlap | D1/D3/E：日交集、多种coverage、unknown保留 |
| 19 Era | B/D/E/J：signal-date、原日值汇总、单独落盘 |
| 20 threshold freeze | D3/E/J：预定诊断层级与rationale，禁止按数量/收益调cut |
| 21 representative防挖掘 | G/H：完全label-free，outcome变异不影响结果 |
| 22 PIT暴露年份 | F：市值等开发期可用；行业晚期368日不满足开发期 |
| 23 Alpha360案例 | H：287工作成员及已知Alpha158交叉关系，非226全替代 |
| 24 关系编码 | C/J：relation_type+evidence_status+mask/sign/domain |
| 25 库存保留 | B/G/J/K：774/765/494分层映射，所有成员保留且无删除 |

初版规划阶段验证（不代表当前实施状态）：远端基线、冻结Board hash、成员数量与来源、taxonomy覆盖、runtime日期/尺寸元数据、既有年度质量数据及两个synthetic单日测时。当时未读取真实factor矩阵进行新consolidation，未运行聚类/代表选择，未读取2024+数据值；初版按纯文档检查路径交付。当前实现和真实canary按代码完整检查路径验证，详见实施进度。
