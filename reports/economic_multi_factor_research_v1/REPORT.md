# Economic Multi-Factor Research V1

> 状态：`CLOSED`；证据类别：`post_observation_research / historical_diagnostic_only`。本阶段不产生 fresh OOS、production winner 或 Strategy V2 授权。

## 结论

- 765 个全局物理合格因子被重新映射为经济机制；首代 sleeves 只使用 39 个方向可由机制与文献预先说明的透明 mature factors。其余因子保留在 economic map 中，但不因技术变体数量多而获得组合权重。
- 原 taxonomy 被重写为 Valuation、Fundamentals、Liquidity/Trading、Return Dynamics、Risk/Lottery、Size/Structure、Technical Price/Volume 与 Opaque Multi-input 等研究层。`Multi` 不再被当作经济含义，PriceTrend 与 MomentumTrend 也不再自动等同。
- 共冻结 11 个 sleeves、7 个有限 archetypes；权重均为“因子在 subfamily 内等权、subfamily 在 sleeve 内等权、sleeve 在 archetype 内等权”。没有权重搜索、子集穷举、ML、SHAP 或结果后翻符号。
- Size 没有被预设为 small-cap alpha；它只作为暴露/条件变量。Residual Momentum 有文献先验，但当前矩阵没有可诚实等同的 PIT residual-return factor，因此未用 raw momentum 冒充。
- 三个 outer split 的资格仅使用各自 train+validation 日期。测试期 coverage、IC 或收益没有参与 membership。

## 已观察历史发现

- 已观察历史中，`speculation_reversal` 的跨 split 平均 Rank IC 最高（0.0570，3/3 为正）；`speculative_activity` 也为 0.0492（3/3 为正）。但两者平均单个约半年 test 窗口的 P01 成本拖累分别为 7.78% 与 7.92%，不能把 gross 排序关系直接当作可交易 alpha。
- `illiquidity_premium` 的平均 Rank IC 为 0.0546，但只在 2/3 个 split 为正，且与 Size 的平均秩相关为 -0.7810；它更像带有显著小盘暴露的历史信号，而不是已识别的纯流动性溢价。
- `traditional_momentum` 在 0/3 个 split 为正，平均 Rank IC 为 -0.0474；`trend_anchor` 同样不稳定。相较之下，短期反转和投机—反转组合更符合本样本历史，但预注册方向不会因结果被翻转。
- `value` 平均 Rank IC 为 0.0124，仅 2/3 个 split 为正；profitability、accounting quality 及其 fundamental archetypes 没有显示跨 split 稳定增量。`diversified_economic` 也只是 0.0092、2/3 为正，不能作为默认胜者。
- 6 个预注册增量比较中，同时满足 combined-minus-base 与 residual-added IC 在全部 3 个 split 为正的有 0 个。因此本阶段没有“稳定互补”结论，也没有据此继续调权或搜索新组合。
- P01 表报告的是固定执行规则下的绝对组合路径，不含 benchmark-adjusted alpha。已观察历史市场方向可能使负 IC 的 variant 仍获得正绝对收益；预测力判断以 Rank IC/单调性为主，P01 只用于可投资性、换手和成本诊断。

跨 split 聚合（按平均 Rank IC 排序）：

| variant_id | variant_type | mean_rank_ic | min_rank_ic | max_rank_ic | positive_split_count | mean_quintile_5_minus_1 | mean_turnover_proxy | mean_size_rank_corr |
|---|---|---|---|---|---|---|---|---|
| speculation_reversal | archetype | 0.0570 | 0.0313 | 0.0776 | 3 | 0.0012 | 0.8746 | 0.0097 |
| illiquidity_premium | sleeve | 0.0546 | -0.0048 | 0.0934 | 2 | 0.0159 | 0.2556 | -0.7810 |
| speculative_activity | sleeve | 0.0492 | 0.0270 | 0.0668 | 3 | -0.0022 | 0.9062 | 0.1562 |
| short_term_reversal | sleeve | 0.0411 | -0.0033 | 0.0706 | 2 | 0.0018 | 0.5902 | -0.1390 |
| trading_mispricing | archetype | 0.0401 | 0.0168 | 0.0538 | 3 | -0.0008 | 0.8212 | 0.2245 |
| value | sleeve | 0.0124 | -0.0817 | 0.0832 | 2 | -0.0193 | 0.1052 | 0.3451 |
| value_low_risk | archetype | 0.0096 | -0.0835 | 0.0656 | 2 | -0.0238 | 0.1458 | 0.3854 |
| diversified_economic | archetype | 0.0092 | -0.0832 | 0.0698 | 2 | -0.0211 | 0.5524 | 0.4200 |
| investment_growth | sleeve | 0.0085 | -0.0108 | 0.0299 | 2 | 0.0059 | 0.0603 | -0.1293 |
| low_risk_lottery | sleeve | 0.0025 | -0.0684 | 0.0471 | 2 | -0.0263 | 0.1911 | 0.3594 |
| value_profitability | archetype | 0.0014 | -0.0906 | 0.0603 | 2 | -0.0191 | 0.0951 | 0.4152 |
| fundamental_value | archetype | -0.0033 | -0.0896 | 0.0561 | 2 | -0.0180 | 0.1008 | 0.3905 |
| profitability | sleeve | -0.0063 | -0.0549 | 0.0196 | 2 | -0.0099 | 0.0357 | 0.3149 |
| accounting_quality | sleeve | -0.0094 | -0.0515 | 0.0270 | 1 | -0.0078 | 0.0708 | 0.1901 |
| institutional_flow | sleeve | -0.0276 | -0.0738 | 0.0293 | 1 | -0.0033 | 0.8133 | 0.3396 |
| traditional_momentum | sleeve | -0.0474 | -0.0928 | -0.0177 | 0 | -0.0091 | 0.1783 | 0.1218 |
| trend_flow_confirmation | archetype | -0.0557 | -0.1305 | 0.0306 | 1 | -0.0102 | 0.7637 | 0.3844 |
| trend_anchor | sleeve | -0.0695 | -0.1561 | 0.0289 | 1 | -0.0151 | 0.7124 | 0.3185 |

## Economic map

| primary_family | factor_count |
|---|---|
| TechnicalPriceVolume | 299 |
| LiquidityTrading | 125 |
| RiskLottery | 107 |
| ReturnDynamics | 88 |
| OpaqueMultiInput | 71 |
| TradingBehavior | 49 |
| Fundamentals | 14 |
| Valuation | 8 |
| SizeStructure | 3 |
| CapitalStructure | 1 |

完整 765 行映射见 `economic_map.csv`。大量 Alpha158/360/101 与 TA 公式被归入 Technical Price/Volume 或 Opaque Multi-input 的 exploratory layer；这是对其经济可解释性边界的诚实表达，不是否定其后续模型价值。

## 文献如何影响设计

`literature_evidence_map.csv` 保存机制、A 股与国际证据、预期方向、冗余、互补角色、horizon、turnover 和证据等级。最直接的设计影响是：

1. Liu–Stambaugh–Yuan 促使 Value 保留 earnings/book/sales/cash-flow/payout 多种测量，并让 Size 可见而非机械做多小盘；
2. Jansen–Swinkels–Zhou 将 value/risk/trading/reversal 设为较强先验，将 raw momentum/quality 设为混合证据；
3. Leippold–Wang–Zhou 使 liquidity/trading 被拆成 price impact、speculative activity 与 order flow，并从一开始报告成本；
4. Hsu 等使 traditional momentum、overnight sentiment 与 reversal 分开，禁止看结果后把 momentum 改名为 reversal；
5. Pan–Tang–Xu 预先冻结 abnormal turnover 的负方向；Wan 的中国证据使 IVOL 与 MAX 都保留但在 subfamily 层平衡。

## Split-local eligibility

| outer_split_id | sum | count |
|---|---|---|
| split_001 | 39 | 39 |
| split_002 | 39 | 39 |
| split_003 | 39 | 39 |

`sum` 是在该 split 的 development-only scope 通过资格的预注册成员数，`count` 是候选成员数。完整统计和排除原因见 `split_local_eligibility.csv` 与 `effective_sleeve_membership.csv`。

## Sleeve 与 archetype 历史诊断

| outer_split_id | variant_id | variant_type | mean_rank_ic | positive_ic_fraction | quintile_5_minus_1 | nondecreasing_quintile_steps | top50_five_day_one_way_turnover |
|---|---|---|---|---|---|---|---|
| split_001 | diversified_economic | archetype | -0.0832 | 0.3417 | -0.0607 | 0 | 0.5504 |
| split_001 | fundamental_value | archetype | -0.0896 | 0.3167 | -0.0588 | 0 | 0.0983 |
| split_001 | speculation_reversal | archetype | 0.0620 | 0.7583 | 0.0064 | 4 | 0.8687 |
| split_001 | trading_mispricing | archetype | 0.0168 | 0.5917 | -0.0109 | 1 | 0.8287 |
| split_001 | trend_flow_confirmation | archetype | -0.1305 | 0.2083 | -0.0467 | 0 | 0.7278 |
| split_001 | value_low_risk | archetype | -0.0835 | 0.4083 | -0.0623 | 0 | 0.1609 |
| split_001 | value_profitability | archetype | -0.0906 | 0.3167 | -0.0571 | 0 | 0.1061 |
| split_001 | accounting_quality | sleeve | -0.0515 | 0.3250 | -0.0267 | 0 | 0.0757 |
| split_001 | illiquidity_premium | sleeve | 0.0934 | 0.7917 | 0.0302 | 4 | 0.2617 |
| split_001 | institutional_flow | sleeve | -0.0738 | 0.2167 | -0.0256 | 0 | 0.7974 |
| split_001 | investment_growth | sleeve | 0.0299 | 0.7417 | 0.0131 | 3 | 0.0609 |
| split_001 | low_risk_lottery | sleeve | -0.0684 | 0.4333 | -0.0563 | 0 | 0.2183 |
| split_001 | profitability | sleeve | -0.0549 | 0.2667 | -0.0342 | 0 | 0.0304 |
| split_001 | short_term_reversal | sleeve | 0.0706 | 0.7667 | 0.0156 | 4 | 0.6139 |
| split_001 | speculative_activity | sleeve | 0.0270 | 0.6083 | -0.0113 | 3 | 0.9078 |
| split_001 | traditional_momentum | sleeve | -0.0928 | 0.2833 | -0.0413 | 1 | 0.1991 |
| split_001 | trend_anchor | sleeve | -0.1561 | 0.2417 | -0.0599 | 0 | 0.6504 |
| split_001 | value | sleeve | -0.0817 | 0.3750 | -0.0592 | 0 | 0.1348 |
| split_002 | diversified_economic | archetype | 0.0411 | 0.4758 | 0.0018 | 2 | 0.5708 |
| split_002 | fundamental_value | archetype | 0.0238 | 0.4435 | 0.0035 | 2 | 0.0958 |
| split_002 | speculation_reversal | archetype | 0.0776 | 0.6935 | 0.0099 | 3 | 0.8908 |
| split_002 | trading_mispricing | archetype | 0.0538 | 0.6855 | 0.0081 | 3 | 0.8083 |
| split_002 | trend_flow_confirmation | archetype | -0.0673 | 0.3065 | -0.0076 | 1 | 0.7417 |
| split_002 | value_low_risk | archetype | 0.0468 | 0.4677 | -0.0002 | 2 | 0.1592 |
| split_002 | value_profitability | archetype | 0.0344 | 0.4597 | -0.0000 | 3 | 0.0883 |
| split_002 | accounting_quality | sleeve | -0.0039 | 0.3387 | 0.0007 | 2 | 0.0583 |
| split_002 | illiquidity_premium | sleeve | 0.0753 | 0.7097 | 0.0205 | 4 | 0.2417 |
| split_002 | institutional_flow | sleeve | -0.0382 | 0.3952 | -0.0041 | 1 | 0.8142 |
| split_002 | investment_growth | sleeve | 0.0065 | 0.6290 | 0.0047 | 3 | 0.0592 |
| split_002 | low_risk_lottery | sleeve | 0.0471 | 0.4516 | -0.0015 | 2 | 0.1942 |
| split_002 | profitability | sleeve | 0.0196 | 0.5726 | 0.0047 | 2 | 0.0417 |
| split_002 | short_term_reversal | sleeve | 0.0560 | 0.5403 | 0.0075 | 3 | 0.5625 |
| split_002 | speculative_activity | sleeve | 0.0668 | 0.7581 | 0.0086 | 2 | 0.9125 |
| split_002 | traditional_momentum | sleeve | -0.0318 | 0.3952 | -0.0001 | 3 | 0.1550 |
| split_002 | trend_anchor | sleeve | -0.0812 | 0.2258 | -0.0096 | 1 | 0.6758 |
| split_002 | value | sleeve | 0.0357 | 0.5000 | -0.0018 | 2 | 0.0992 |
| split_003 | diversified_economic | archetype | 0.0698 | 0.7661 | -0.0042 | 2 | 0.5358 |
| split_003 | fundamental_value | archetype | 0.0561 | 0.7581 | 0.0012 | 2 | 0.1083 |
| split_003 | speculation_reversal | archetype | 0.0313 | 0.6048 | -0.0127 | 0 | 0.8642 |
| split_003 | trading_mispricing | archetype | 0.0497 | 0.6613 | 0.0004 | 2 | 0.8267 |
| split_003 | trend_flow_confirmation | archetype | 0.0306 | 0.6210 | 0.0237 | 4 | 0.8217 |
| split_003 | value_low_risk | archetype | 0.0656 | 0.6935 | -0.0091 | 2 | 0.1175 |
| split_003 | value_profitability | archetype | 0.0603 | 0.7581 | -0.0001 | 2 | 0.0908 |
| split_003 | accounting_quality | sleeve | 0.0270 | 0.7097 | 0.0026 | 2 | 0.0783 |
| split_003 | illiquidity_premium | sleeve | -0.0048 | 0.4435 | -0.0029 | 2 | 0.2633 |
| split_003 | institutional_flow | sleeve | 0.0293 | 0.6210 | 0.0199 | 4 | 0.8283 |
| split_003 | investment_growth | sleeve | -0.0108 | 0.3952 | -0.0002 | 2 | 0.0608 |
| split_003 | low_risk_lottery | sleeve | 0.0287 | 0.6048 | -0.0210 | 0 | 0.1608 |
| split_003 | profitability | sleeve | 0.0164 | 0.6452 | -0.0000 | 2 | 0.0350 |
| split_003 | short_term_reversal | sleeve | -0.0033 | 0.4758 | -0.0176 | 1 | 0.5942 |
| split_003 | speculative_activity | sleeve | 0.0536 | 0.6613 | -0.0038 | 1 | 0.8983 |
| split_003 | traditional_momentum | sleeve | -0.0177 | 0.4516 | 0.0142 | 4 | 0.1808 |
| split_003 | trend_anchor | sleeve | 0.0289 | 0.5565 | 0.0242 | 4 | 0.8108 |
| split_003 | value | sleeve | 0.0832 | 0.7661 | 0.0030 | 2 | 0.0817 |

这些是已观察历史 test 上的机制诊断。不能因为本轮 sleeve 定义是新的，就把结果重新称为 unbiased holdout。逐日 IC 和 calendar-year regime 结果分别保存在 `daily_rank_ic.csv` 与 `complementarity_diagnostics.csv`。

## 冗余与互补

绝对相关性最高的 variant pairs：

| outer_split_id | left_variant | right_variant | mean_daily_rank_correlation |
|---|---|---|---|
| split_002 | value_profitability | fundamental_value | 0.9054 |
| split_001 | value_profitability | fundamental_value | 0.9054 |
| split_002 | value | value_low_risk | 0.9049 |
| split_003 | value_profitability | fundamental_value | 0.9031 |
| split_002 | low_risk_lottery | value_low_risk | 0.8992 |
| split_001 | value | value_low_risk | 0.8964 |
| split_001 | low_risk_lottery | value_low_risk | 0.8916 |
| split_003 | value | value_low_risk | 0.8857 |
| split_003 | low_risk_lottery | value_low_risk | 0.8796 |
| split_003 | institutional_flow | trend_flow_confirmation | 0.8721 |
| split_003 | trend_anchor | trend_flow_confirmation | 0.8494 |
| split_002 | institutional_flow | trend_flow_confirmation | 0.8485 |

预注册增量比较：

| outer_split_id | base_variant | added_variant | combined_variant | combined_minus_base_rank_ic | added_residual_mean_rank_ic | base_added_mean_rank_correlation | incremental_positive |
|---|---|---|---|---|---|---|---|
| split_001 | value | profitability | value_profitability | -0.0090 | -0.0370 | 0.2614 | False |
| split_001 | value_profitability | accounting_quality | fundamental_value | 0.0010 | -0.0205 | 0.3932 | True |
| split_001 | speculative_activity | short_term_reversal | speculation_reversal | 0.0350 | 0.0639 | 0.2042 | True |
| split_001 | speculation_reversal | institutional_flow | trading_mispricing | -0.0452 | -0.0540 | -0.2900 | False |
| split_001 | value | low_risk_lottery | value_low_risk | -0.0019 | -0.0296 | 0.5953 | False |
| split_001 | trend_anchor | institutional_flow | trend_flow_confirmation | 0.0256 | -0.0324 | 0.2969 | True |
| split_002 | value | profitability | value_profitability | -0.0013 | 0.0108 | 0.2954 | False |
| split_002 | value_profitability | accounting_quality | fundamental_value | -0.0107 | -0.0181 | 0.3818 | False |
| split_002 | speculative_activity | short_term_reversal | speculation_reversal | 0.0108 | 0.0409 | 0.2014 | True |
| split_002 | speculation_reversal | institutional_flow | trading_mispricing | -0.0238 | -0.0089 | -0.3828 | False |
| split_002 | value | low_risk_lottery | value_low_risk | 0.0111 | 0.0329 | 0.6244 | True |
| split_002 | trend_anchor | institutional_flow | trend_flow_confirmation | 0.0140 | -0.0064 | 0.3633 | True |
| split_003 | value | profitability | value_profitability | -0.0229 | -0.0067 | 0.2827 | False |
| split_003 | value_profitability | accounting_quality | fundamental_value | -0.0043 | 0.0053 | 0.3753 | False |
| split_003 | speculative_activity | short_term_reversal | speculation_reversal | -0.0223 | -0.0217 | 0.2857 | False |
| split_003 | speculation_reversal | institutional_flow | trading_mispricing | 0.0184 | 0.0454 | -0.4261 | True |
| split_003 | value | low_risk_lottery | value_low_risk | -0.0176 | -0.0259 | 0.5593 | False |
| split_003 | trend_anchor | institutional_flow | trend_flow_confirmation | 0.0017 | 0.0266 | 0.4514 | True |

跨 split 增量一致性：

| base_variant | added_variant | combined_variant | mean_combined_minus_base_rank_ic | delta_positive_split_count | mean_added_residual_rank_ic | residual_positive_split_count | mean_base_added_rank_correlation |
|---|---|---|---|---|---|---|---|
| trend_anchor | institutional_flow | trend_flow_confirmation | 0.0137 | 3 | -0.0041 | 1 | 0.3705 |
| speculative_activity | short_term_reversal | speculation_reversal | 0.0078 | 2 | 0.0277 | 2 | 0.2304 |
| value | low_risk_lottery | value_low_risk | -0.0028 | 1 | -0.0075 | 1 | 0.5930 |
| value_profitability | accounting_quality | fundamental_value | -0.0046 | 1 | -0.0111 | 1 | 0.3835 |
| value | profitability | value_profitability | -0.0110 | 0 | -0.0110 | 1 | 0.2799 |
| speculation_reversal | institutional_flow | trading_mispricing | -0.0169 | 1 | -0.0058 | 1 | -0.3663 |

`combined_minus_base_rank_ic` 回答透明 A 与 A+B 的历史差异；`added_residual_mean_rank_ic` 先在每日截面从 added 中去除 base 的线性部分，再衡量剩余排序信息。两者共同用于区分 complementarity 与 redundancy，不做 2^N 搜索。

## P01 固定执行与成本

| outer_split_id | variant_id | net_total_return | cost_drag | annualized_turnover |
|---|---|---|---|---|
| split_001 | accounting_quality | 0.2786 | 0.0120 | 12.3796 |
| split_001 | diversified_economic | 0.0931 | 0.0481 | 52.9118 |
| split_001 | fundamental_value | 0.1640 | 0.0120 | 13.2903 |
| split_001 | illiquidity_premium | 0.3324 | 0.0298 | 27.9826 |
| split_001 | institutional_flow | 0.1566 | 0.0688 | 73.0673 |
| split_001 | investment_growth | 0.4962 | 0.0119 | 11.9334 |
| split_001 | low_risk_lottery | 0.2459 | 0.0220 | 22.8213 |
| split_001 | profitability | 0.1844 | 0.0067 | 7.4925 |
| split_001 | short_term_reversal | 0.2838 | 0.0639 | 58.7889 |
| split_001 | speculation_reversal | 0.2598 | 0.0816 | 80.1004 |
| split_001 | speculative_activity | 0.2134 | 0.0823 | 82.4039 |
| split_001 | trading_mispricing | 0.1127 | 0.0712 | 76.5868 |
| split_001 | traditional_momentum | 0.0338 | 0.0201 | 22.3427 |
| split_001 | trend_anchor | -0.0811 | 0.0509 | 57.0100 |
| split_001 | trend_flow_confirmation | 0.0322 | 0.0589 | 66.0268 |
| split_001 | value | 0.2209 | 0.0156 | 16.5399 |
| split_001 | value_low_risk | 0.2007 | 0.0170 | 18.3937 |
| split_001 | value_profitability | 0.1558 | 0.0125 | 13.7324 |
| split_002 | accounting_quality | 0.1215 | 0.0076 | 8.6049 |
| split_002 | diversified_economic | 0.0475 | 0.0493 | 55.4008 |
| split_002 | fundamental_value | 0.1109 | 0.0102 | 11.5638 |
| split_002 | illiquidity_premium | 0.1893 | 0.0239 | 25.5910 |
| split_002 | institutional_flow | 0.0115 | 0.0669 | 77.1353 |
| split_002 | investment_growth | 0.1852 | 0.0081 | 9.1376 |
| split_002 | low_risk_lottery | 0.0830 | 0.0184 | 20.4543 |
| split_002 | profitability | 0.1413 | 0.0057 | 6.6373 |
| split_002 | short_term_reversal | 0.0694 | 0.0497 | 54.4801 |
| split_002 | speculation_reversal | 0.0867 | 0.0758 | 84.9731 |
| split_002 | speculative_activity | 0.0724 | 0.0777 | 86.6252 |
| split_002 | trading_mispricing | 0.1185 | 0.0695 | 76.8352 |
| split_002 | traditional_momentum | 0.0288 | 0.0151 | 17.6399 |
| split_002 | trend_anchor | 0.0668 | 0.0570 | 63.2514 |
| split_002 | trend_flow_confirmation | 0.0924 | 0.0628 | 70.5680 |
| split_002 | value | 0.1228 | 0.0108 | 12.0279 |
| split_002 | value_low_risk | 0.1194 | 0.0158 | 17.3912 |
| split_002 | value_profitability | 0.0753 | 0.0094 | 10.8822 |
| split_003 | accounting_quality | 0.0857 | 0.0095 | 10.5561 |
| split_003 | diversified_economic | 0.0228 | 0.0450 | 51.7359 |
| split_003 | fundamental_value | 0.0961 | 0.0115 | 12.9100 |
| split_003 | illiquidity_premium | 0.1763 | 0.0251 | 27.6861 |
| split_003 | institutional_flow | 0.2539 | 0.0765 | 77.3870 |
| split_003 | investment_growth | 0.1782 | 0.0089 | 9.5957 |
| split_003 | low_risk_lottery | -0.0186 | 0.0150 | 17.2656 |
| split_003 | profitability | 0.1239 | 0.0055 | 6.1980 |
| split_003 | short_term_reversal | 0.2202 | 0.0551 | 57.8718 |
| split_003 | speculation_reversal | 0.1198 | 0.0761 | 82.3663 |
| split_003 | speculative_activity | 0.0580 | 0.0776 | 85.5264 |
| split_003 | trading_mispricing | 0.2048 | 0.0747 | 78.6722 |
| split_003 | traditional_momentum | 0.1670 | 0.0191 | 20.2134 |
| split_003 | trend_anchor | 0.1666 | 0.0750 | 74.9464 |
| split_003 | trend_flow_confirmation | 0.3455 | 0.0796 | 76.8637 |
| split_003 | value | 0.0518 | 0.0092 | 10.4091 |
| split_003 | value_low_risk | -0.0055 | 0.0117 | 13.4265 |
| split_003 | value_profitability | 0.0545 | 0.0096 | 10.9802 |

跨 split 执行摘要：

| variant_id | mean_net_total_return | positive_net_split_count | mean_cost_drag | mean_annualized_turnover | minimum_fill_count |
|---|---|---|---|---|---|
| investment_growth | 0.2865 | 3 | 0.0096 | 10.2222 | 1160 |
| illiquidity_premium | 0.2326 | 3 | 0.0262 | 27.0866 | 1390 |
| short_term_reversal | 0.1911 | 3 | 0.0562 | 57.0469 | 1821 |
| accounting_quality | 0.1619 | 3 | 0.0097 | 10.5135 | 1054 |
| trend_flow_confirmation | 0.1567 | 3 | 0.0671 | 71.1528 | 1911 |
| speculation_reversal | 0.1554 | 3 | 0.0778 | 82.4799 | 2122 |
| profitability | 0.1499 | 3 | 0.0060 | 6.7759 | 706 |
| trading_mispricing | 0.1453 | 3 | 0.0718 | 77.3647 | 2055 |
| institutional_flow | 0.1407 | 3 | 0.0707 | 75.8632 | 1993 |
| value | 0.1319 | 3 | 0.0119 | 12.9923 | 1163 |
| fundamental_value | 0.1237 | 3 | 0.0112 | 12.5881 | 1077 |
| speculative_activity | 0.1146 | 3 | 0.0792 | 84.8518 | 2152 |
| value_low_risk | 0.1048 | 2 | 0.0148 | 16.4038 | 1113 |
| low_risk_lottery | 0.1034 | 2 | 0.0184 | 20.1804 | 1055 |
| value_profitability | 0.0952 | 3 | 0.0105 | 11.8649 | 933 |
| traditional_momentum | 0.0765 | 3 | 0.0181 | 20.0653 | 1075 |
| diversified_economic | 0.0544 | 3 | 0.0475 | 53.3495 | 1708 |
| trend_anchor | 0.0508 | 2 | 0.0610 | 65.0693 | 1776 |

执行诊断沿用固定 Top50、每 5 日调仓、T+1、A 股佣金/印花税、10 bps 滑点、动态手数、5% participation cap 和既有近似 market semantics。预测排序、换手与成本后绝对组合路径分开解释；这里没有扫描 TopK、调仓频率或费用参数。运行期间既有 Qlib 执行栈出现 empty-slice 与个别 execution-price 缺失后回退 close 的警告；54 个场景均完成且存在成交与成本，但执行结果仍须按 approximate historical diagnostic 使用。

## 针对计划问题的回答

1. **765 如何理解**：它们是物理合格候选，不是 765 个独立经济 bets。透明成员进入 sleeves，技术/opaque 公式保留作 exploratory/model information。
2. **taxonomy 修正**：拆分 liquidity/trading/order-flow，拆分 raw momentum/reversal/anchor，拆分 risk/lottery/downside，`Multi` 降为 unresolved，Size 改为多重角色。
3. **A 股文献影响**：见上文与 evidence map；没有直接照搬美国方向。
4. **机制**：价值、经营盈利、现金/应计质量、保守投资与增长、价格冲击、投机活动、大单流、短期反转/隔夜情绪、传统动量、52 周锚定、低风险/彩票偏好。
5. **为何这些 sleeves**：每个 sleeve 代表一个可叙述机制，而不是原 folder 的平均值。
6. **为何保留多测量**：同一机制的 level/change、PIT/TTM、risk/behavior 和 horizon 由 subfamily balancing 保留，近义变体不会因数量多而增权。
7. **冗余**：以每日 score correlation 报告，不使用“一簇只留一个”。
8. **互补**：以 A、A+B、added residual IC 和成本分散共同判断。
9. **Value/Liquidity/Trading/Risk**：结果见 diagnostics；解释受短样本与已观察历史限制。
10. **Momentum/Residual Momentum/Reversal**：raw momentum 与 reversal 分开；residual momentum 因缺少诚实输入而不伪造。
11. **Fundamentals**：Value→Value+Profitability→+Accounting Quality 是预注册增量链。
12. **Size**：V1 中是 exposure/control/conditioning variable，不是自动做多小盘。
13. **高换手/成本**：见 P01 表；交易与反转类必须以 net 而非 gross 解释。
14. **稳定 incremental value**：只有在多个 split 的 combined delta 与 residual IC 同向时才可称“较一致的历史互补”，仍不是 fresh OOS。
15. **失败组合**：负增量或高相关/高成本组合是有效研究结果，不会继续改权重。
16. **split 一致性**：所有表逐 split 保留，不用 pooled 均值掩盖差异。
17. **research variants**：实际预注册 18 个；无额外搜索 arm。
18. **result-driven iteration**：V1 为 0；manifest 明确记录。未来修改必须另记 post-result iteration。
19. **historical evidence**：仅用于机制、稳定性、失败与假设生成；`unbiased_final_estimate=false`。
20. **是否形成 ML baseline**：形成了 human-structured 输入与诊断基线，但是否进入 ML 由后续单独授权决定。

## Governance 与边界

- Strategy V1、Forward Track、frozen Matrix、历史 prediction 和旧 release 均未修改；
- 本阶段没有启动 LightGBM/XGBoost/神经网络/SHAP/Strategy V2；
- `split_003` 与其他 historical tests 都按 post-observation diagnostic 解释；
- 真正新证据仍只能来自未来另行冻结的 Forward Track；
- 本报告允许“不成立”和 mixed evidence，不选择 production winner。
