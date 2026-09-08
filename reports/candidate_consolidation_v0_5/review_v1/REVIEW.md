# Candidate Consolidation V0.5 结果审阅

审阅日期：2026-09-08。对象：`consolidation_20260908_v2/proposal_v1`，实现提交 `a7d0405`。

**结论：数值证据可继续使用，代表提案需要修订，不能整表接受为可替换关系或最终因子池。** 五组精确重复的证据较充分；其余近似关系应保留为研究线索。此前“P4交付完成”表示文件和计算已交付，本次审阅发现其语义协调与代表资格规则尚未达到计划要求。

这是独立审阅意见，不改变原提案的 `user_decision=pending`。本次复用已有开发期特征汇总，没有重跑筛选、访问2024+数值、读取收益排序或建设Core。

## 1. 需要优先修订的问题

### P1：未解析窗口和量纲，却允许提出替代关系

494个active成员中459项被实现标为 `representative_eligible`；其中87项量纲为 `unresolved`、63项窗口为 `unspecified`，54项的“definition”实际上是 `Generated from ta wrapper smoke; coverage=...` 一类运行说明。这三类计数有重叠。

[语义实现](../../../factor_research/candidate_consolidation_proposals.py) 的 `semantic_review` 只要已有说明和机制字符串非空，就可赋予资格；随后 `propose_groups` 把相同机制、相同窗口字符串作为同一层。这样多个“窗口未知”被当成了“窗口相同”。`formula_token_count` 还把运行说明的分词数当作公式复杂度，不能支持复杂度排序。

具体证据：0.95层级建议 `ta_trend_ema_slow → ta_trend_ema_fast`，两者窗口均记为 `unspecified`。但本地引用库 `tmp/reference_repos/ta/ta/wrapper.py:264–269` 明确为12日和26日。该库HEAD为 `a890410710a6e483c9ba08da7f3dd5089e4b9dff`，与适配器配置一致。同文件256–260行的SMA为12/26日，313–325行的Ichimoku使用9/26/52日参数，也未被当前通用名称规则表达。

**建议：暂停这类替代提案；从实际调用和参数补齐机制、窗口及量纲，未知值不能作为等价分组依据。** 本地wrapper核验支持这一缺陷，但完整修订仍须核对canonical生成链实际绑定的版本与参数，不能只引用库默认值即宣称全部溯源完成。

### P1：跨时期关系状态未进入代表决策

[提案构建脚本](../../../scripts/build_candidate_consolidation_proposals_v0_5.py) 以Full聚类和Full距离调用 `propose_groups`；函数不接收Era、mask或符号稳定性证据。脚本另行输出的 `pair_relations_<level>.parquet` 没有回接到代表决策。

将每条 `conditional_alias_proposal` 与其实际代表配对后，得到：

| 层级 | 替代提案行 | stable_redundancy | regime_dependent | insufficient_overlap | no_stable_redundancy |
|---|---:|---:|---:|---:|---:|
| 0.995 | 13 | 8 | 4 | 0 | 1 |
| 0.95 | 22 | 18 | 2 | 2 | 0 |
| 0.85 | 31 | 22 | 3 | 3 | 3 |
| 0.70 | 38 | 27 | 6 | 4 | 1 |

合计104条跨层级提案，涉及39个不同待替代因子；同一因子可能重复出现在不同层级，不能把104当成待删除因子数。其中29条未获对应层级的严格稳定关系支持。

0.95层级具体例子：

| 待替代成员 → 所提代表 | 已有pair证据 | 审阅建议 |
|---|---|---|
| ta_momentum_ao → ta_trend_macd | insufficient_overlap | 保留身份，核查共同样本 |
| ta_trend_kst → ta_momentum_ppo_signal | insufficient_overlap | 保留身份，核查共同样本 |
| ta_trend_trix → ta_momentum_ppo_signal | regime_dependent | 保留为时期依赖关系 |
| mature_sales_to_price_pit → mature_sales_to_price_ttm | regime_dependent | 分别保留，核对会计口径和PIT |

数值stable也不自动等于经济等价；当前104条均至少有窗口、量纲或说明字段未协调的问题。完整逐条对照见 [conditional_alias_review.json](conditional_alias_review.json)，它是审阅附表，不覆盖原Board，也不新增筛选阈值。

**建议：把每条“成员—代表”的Full/Era共同样本、q10、符号及稳定关系直接展示在Board。未满足原计划稳定条件的关系降为保留/待核查；稳定关系再接受语义审阅。** 不需要重新计算121,771对的日Spearman。

### P1：最大的价格线簇尚不能解释为同一经济信号

0.95层级最大簇有21项；0.995层级最大簇有13项，集中包含均线、通道价格线、VWAP及部分Alpha101。当前把 `ta_volatility_bbh/bbm/dch/dcl/dcm/kcc/kch/kcl` 归入 `realized_or_residual_risk`，容易误读为波动率幅度冗余。

引用库wrapper的175–205行和 `ta/volatility.py` 公式显示，这些列是价格中轨/上轨/下轨；例如Bollinger上轨是均价加若干标准差，带宽则是另一列 `bbw`。它们具有输入价格的量纲，高横截面同序可能包含共同价格水平或provider归一化尺度的影响。这里是基于公式的解释假设，尚无合格价格control证明其贡献大小。

因此此前披露的价格单位/溯源缺项，对这些簇是实质解释限制。建议先修正分类并查清provider价格尺度，再决定是否补开发期价格control。不能直接用未经验证的close做名义价格暴露，更不能据现有价格线簇统一删除成员。

### P2：低覆盖单例的“代表”身份需要明确限制

`ta_volatility_atr` 的Full有效覆盖约35.46%，最差Era约6.90%；`ta_trend_adx_pos/neg` 分别约35.87%和6.97%。三者在四个层级均被标为 `proposed_representative`。

这不证明它们是可用的独立信息来源：共同样本不足本来就可能阻止合并。建议展示单因子质量和pair不可比状态，把单例明确分为“可比下未聚合”和“证据不足”，查明低覆盖是计算链问题还是定义固有行为。此处不以观察结果新增自动剔除门槛。

## 2. 可以保留的结论及其范围

### 五组精确重复：建议接受关系登记

| 建议保留的规范名称 | 等值别名 |
|---|---|
| alpha158_LOW0 | alpha360_LOW0 |
| alpha158_ROC5 | alpha360_CLOSE5 |
| alpha158_ROC10 | alpha360_CLOSE10 |
| alpha158_ROC20 | alpha360_CLOSE20 |
| alpha158_ROC30 | alpha360_CLOSE30 |

[精确重复表](../exact_alias_map.csv)记录了开发期全部168个月的相同键轴、数值和非有限值证据。可据此建议复用一份计算表示并保留别名映射；这只支持当前样本和实现，不是未来任意实现的公式证明。本轮未执行替换或删除。若以后仅落实这五组去重，494个身份对应489份数值表示，不能因此声称已经得到最终Core。

### 聚类数量是结构诊断，不能当有效因子数

Full视图在0.995/0.95/0.85/0.70下分别有390/202/132/89簇。它们依赖既定距离和cut，不代表独立信息维数，也不等于建议保留数量。尤其Alpha360的邻近lag可能高度同序，但不同滞后身份仍应保留，除非后续另行明确家族压缩政策。

名为 `Stable` 的距离视图采用四Era中最小的median(abs(rho))并要求各Era可比；它没有同时施加严格pair关系的q10、符号一致性及Full条件。其计算符合保守结构对照的用途，但名称不能解释成“所有簇都通过严格稳定替代认证”。

每个层级均有6,385对被标记共同样本不足；未知不是弱相关。另有35项deferred主要来自实现规则：32个active Alpha101统一进入实现语义复核，加上PSAR down、BBHI、KCHI。不能把35解释为本次发现了35个失效因子。

### 风险家族已有可解释线索，尚不能自动替换

Full已封存暴露中，amount_mean_20与amount_std_20的signed rho中位数约0.939；总波动率60日与特质波动率60日约0.920；换手均值20日与换手波动20日约0.922。它们分别提示成交额、波动率和换手家族存在较强共同行为，但“水平/变化”“总风险/残差风险”仍是不同经济含义。

`mature_book_to_price` 使用1/PB，`mature_book_to_market_pit` 使用equity/market_cap；`mature_sales_to_price_ttm` 使用1/PS_TTM，而PIT版本使用revenue/market_cap，见 [mature_factors.py](../../../factor_universe_v2/mature_factors.py)。即便某层级数值稳定，也须核对财务期间、更新时点、单位及分母后才能替换。行业暴露缺少开发期覆盖，不能据此宣称已排除行业混杂或获得独立alpha。

## 3. 建议的最小下一步

1. 修订语义协调：优先处理TA价格线、明确窗口及基本面PIT/TTM口径。移除运行说明充当公式复杂度的做法；无法证明同机制同窗口的成员保留身份。
2. 修订代表输出：接入已有pair稳定性/overlap/符号证据；显式标注低覆盖与不可比单例。补窗口不一致、语义未知及时期不稳定的回归用例。
3. 复用当前日证据和汇总，只生成独立的修订版提案，保留本版和receipt。价格control如需新增，先完成单位溯源，再单独估算有界计算任务；不要求用户重跑当前全量命令。
4. 再次人工审阅后才讨论实际压缩政策。本次不选择“最佳cut”、目标数量、Core或模型，也不根据收益表现调规则。

## 4. 本次核验与限制

重新逐文件核验原proposal receipt绑定的11份报告、28份runtime文件、2份代码；原Primary清单20份文件及Board固定hash均通过。逐条连接104条替代提案与对应pair关系，并核对语义资格、覆盖率和部分实际源码。

此前数值验收包括555项测试、26个验证器及canary/独立pandas对照，这些支持工程与数值实现，但不能代替本次经济语义审阅。本次没有重放4.12亿pair-day计算，也没有逐一证明765个公式；五组精确关系沿用已封存的全月等值证据。原封存报告、代表政策、Board、runtime以及Primary均保持不变。

本次交付检查：fast 46项、full 555项测试及26个验证器通过；104条关系连接复核、Markdown链接、文档索引及文件大小检查通过。没有修改计算代码或增添筛选测试规则。
