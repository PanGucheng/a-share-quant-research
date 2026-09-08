# 长历史多体系筛选 Primary V0：人工审阅报告

状态：**COMPLETE / STOP FOR HUMAN REVIEW**，2026-09-08。已交付 2010–2023、765 因子、20D 的 Evidence Board 与 Candidate Board V0；本轮停止于候选审阅，不继续 Core、组合、近期诊断或模型训练。

文件哈希与完成状态见[交付清单](PRIMARY_V0_MANIFEST.json)。完整检查538 tests、Fast 46 tests、Qlib runtime 6 tests通过。

## 结果与阅读入口

| 三体系候选意见 | 因子数 | 含义 |
| --- | ---: | --- |
| 3/3 | 332 | 三个已冻结原生规则均通过，仍需人工审阅 |
| 2/3 | 159 | 两个规则通过，一个不通过 |
| 1/3 | 43 | 一个规则通过 |
| 0/3 | 206 | 三个规则均可判断且均不通过 |
| incomplete | 25 | Alphalens 缺少可定义五分桶证据；其中3个在另两体系通过，22个在另两体系不通过 |
| 合计 | 765 | 固定研究库存全部保留 |

- [Candidate Board V0](candidate_board.csv)：完整765行、原始指标、方向、三个状态及逐条件原因。
- [Evidence Board V0](factor_evidence_board.csv)：冻结规则之前的原始证据快照，候选字段仍为 not_evaluated。
- [Alphalens 候选](alphalens_candidates.csv) 336个；[jqfactor 候选](jqfactor_candidates.csv) 492个；[Qlib 候选](qlib_candidates.csv) 535个。
- [候选并集](candidate_factors.csv) 537个，仅表示至少一个规则通过，不是最终因子池；[审阅队列](review_queue.csv)另纳入 incomplete。
- [全部774定义与9个blocked](factor_inventory.csv)、[首轮经验分布](primary_metric_distributions.csv)、[完整765家族FDR](multiple_testing.csv)、[稳健性与未运行项](robustness_annotations.csv)。

各来源结果如下；不赋予某个来源额外资格。

| 来源 | 3/3 | 2/3 | 1/3 | 0/3 | incomplete |
| --- | ---: | ---: | ---: | ---: | ---: |
| Alpha158 | 38 | 47 | 4 | 68 | 1 |
| Alpha360 | 226 | 61 | 39 | 32 | 0 |
| Alpha101 | 19 | 12 | 0 | 48 | 18 |
| TA | 32 | 23 | 0 | 18 | 6 |
| mature_public | 10 | 11 | 0 | 37 | 0 |
| project_basic | 7 | 5 | 0 | 3 | 0 |

**3/3 中有226个来自 Alpha360，不能视为226份独立信号。** 历史定义/代理关系已附在证据表中，本轮未做全量数值去重和聚类，也没有自动删别名或挑选代表因子。三体系共享样本且指标高度相关；agreement 不是独立统计确认。

## 研究合同与实际执行

Canonical identity：`canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`。

研究区间为2010-01-29至2023-12-29，primary使用canonical practical raw样本；标签是 `close[t+21]/close[t+1]-1`，不填补缺价。最后成熟信号为2023-11-30，最多3361个信号日。分组按signal date；跨年度的标签尾部保留，但价格退出日不超过2023-12-29。

10,710个因子×年度单元全部落盘；16个年度单元无可定义IC样本，保留 unavailable，其余通过原生parity，最大差异 `1.1102230246251565e-16`，无required native运行失败。25个因子全期无五分桶有效日，不能据此删除其可计算的IC及其他原生结果。全期765个Rank IC假设均可检验。

用户八进程续跑完成10,608个剩余单元的计算约耗时8873秒（2小时28分钟）；最终状态时间为2026-09-08 01:52:58。时间包括进程与计算IO，但该计时不包括后续Board及最终汇总/FDR。此前耗时估算偏保守，以实际运行记录为准。

全部完成单元已重新逐文件验证hash，访问审计日期、日样本计数与FDR观测数一致。六个预先选定的跨来源代表因子，从原始日序列重算13指标×19时期及原seed bootstrap，均在 `atol=1e-15` 内一致；765行BH/BY校正全部重算核对。详见[原始序列重算](BOARD_RAW_RECOMPUTE.json)。Canonical大分区本身仍继承assembly认证，没有在此重新逐字节验证所有parent。

完整长表见本地 [Factor Evidence Table](../../outputs/long_history_multi_evaluator_screening_v1/primary_full_20260907/primary/delivery_v0/factor_evidence_table.parquet)，含188,955行（765×13×19）、单位、原始方向、时期、最大退出日、样本数和raw路径。分桶指标的样本数明确指五桶共同mask，不伪装为单桶样本数。[年度及Era质量表](../../outputs/long_history_multi_evaluator_screening_v1/primary_full_20260907/primary/delivery_v0/data_quality_by_period.csv)为不依赖标签的全development覆盖，包括末端未成熟信号日。

## 一次性候选规则

规则在首次完整经验分布和不含候选判断的evidence snapshot之后冻结，没有按候选个数调节。规则ID：`26559c272310fd361fcb0c8de4b658b77946058241e4bf26ede281a71d64950b`。

[冻结规则](../../artifacts/long_history_multi_evaluator_screening_v1/26559c272310fd361fcb0c8de4b658b77946058241e4bf26ede281a71d64950b/candidate_rules.yaml)与[阈值理由](../../artifacts/long_history_multi_evaluator_screening_v1/26559c272310fd361fcb0c8de4b658b77946058241e4bf26ede281a71d64950b/candidate_rule_rationale.md)绑定证据、配置和代码hash：

- 所有backend使用同一个全期Qlib Rank IC符号；232个负方向、533个正方向，均明确为development数据导出，不是事前经济方向。
- 共享要求：至少1260个IC有效日、五个各有至少126日数据的年度，绝对mean Rank IC≥0.02、至少70%合格年度方向一致、BH q≤0.05。
- Alphalens：至少1260个五分桶有效日、同方向Q5−Q1>0、同方向五桶平均收益单调性Spearman≥0.8。
- jqfactor：同方向factor_returns均值>0、至少1260日与五个合格年度、至少60%合格年度的收益方向一致。
- Qlib：同方向Pearson>0、同方向原生long-short>0且至少1260个有效日。

各backend至少有一个非共享Rank IC条件真正参与判断。缺少必需指标时为unavailable，其余已知条件不满足为fail；有unavailable时agreement为incomplete。没有Era全通过的硬AND、加权总分、TopN或horizon搜索。详细数值比较见本地[逐条件解释表](../../outputs/long_history_multi_evaluator_screening_v1/primary_full_20260907/primary/candidate_v0/metric_level_reasons.csv)。

阈值严格比较保存的未舍入浮点值：三项单调性显示时可能四舍五入成0.8，原值实际为 `0.7999999999999999`，在机器规则中未通过≥0.8。三者均另有共享IC强度不通过，不影响候选成员；本次保留冻结规则和完整条件记录，没有按显示舍入调整阈值。

## 统计强度与限制

主检验为双侧gap-aware moving-block bootstrap，block=20、samples=1000、seed=20260907；先恢复完整成熟交易日日历上的NaN缺口，一套765家族，其他backend只做parity。BH q≤0.05为696个，BY q≤0.05为656个。**610个p值达到1/1001分辨率下限，不能据这些相同p值细分排名。** 长自相关、短片段不能供块抽样及Monte Carlo精度仍有限；本轮未重新搜索block参数。

BH的依赖假设及相关因子库存限制其解释；BY为敏感性参照。Rank IC的q值不自动为原生收益、形态条件或最终候选并集提供额外FDR保证。规则已经看过development总体分布，候选结果也不是未见数据的确认。

全765表中有137个方向不稳定标注、47个时期集中标注、20个低有效样本覆盖标注、109个BY不显著标注；这些标注可以重叠。3/3中仍有26个出现反向Era等方向不稳定、6个低覆盖、1个BY敏感性标注，不能仅凭3/3跳过审阅。

raw universe没有完成全历史ST/涨跌停/停牌/流动性、微盘暴露、费用和成交检验。原生20D收益是重叠评价标签，不是每日可复利策略净值。经济描述可能对应风险或条件变量，不能仅因相关性显著就称为可交易alpha。

765库存资格及项目旧研究曾使用后期数据；2024+仅为本轮Held-aside Recent Diagnostic，不是全项目untouched OOS。本轮 `held_aside_recent_diagnostic_accessed=false`，10D、近期诊断、Core、组合与模型均未运行。旧selected/rejected与旧方向文件保留在历史路径，本次selection payload没有导入这些结果。

## 复现与停止点

[候选重放记录](CANDIDATE_REPLAY.json)证明：仅复制封存证据和冻结规则，不提供raw chunks、aggregate或enrichment/近期文件，仍能生成文件hash完全一致的9份候选产物。测试另覆盖负方向、必需指标缺失、parity失败、非共享原生条件、近期/旧outcome/10D列扰动、Era贡献和leave-one-era-out。

开发入口：

```powershell
python scripts/build_long_history_boards.py --run-id <completed_run_id> --stage evidence
python scripts/build_long_history_boards.py --run-id <completed_run_id> --stage delivery
python scripts/build_long_history_boards.py --run-id <completed_run_id> --stage candidate --rules-dir artifacts/long_history_multi_evaluator_screening_v1/26559c272310fd361fcb0c8de4b658b77946058241e4bf26ede281a71d64950b
```

生成目录使用独占创建，已有V0不会被重写；上述阶段只在对应产物不存在时执行。规则绑定的是这次封存证据，新的数据或统计规则不能套用此freeze。当前primary V0已完成，无需重新启动全量评价。

现在停在人工审阅：先检查3/3中的同源集中、方向与覆盖标注，再看2/3和incomplete的原生差异原因。是否继续冗余分析、10D、近期诊断或Core研究，由用户另行决定；这些工作不会在本轮自动启动。
