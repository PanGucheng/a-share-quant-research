# 长历史多体系因子重新筛选：开发计划与仓库审计

状态：**PROPOSED / 仅开发计划，尚未实施或运行**。编写日期：2026-09-07。

本计划依据用户提供的《长历史多体系因子重新筛选：仓库审计与开发计划制定》，结合实际仓库制定。附件中的执行性描述作为需求材料处理；本次用户授权是撰写计划并放入项目，不是启动其中的开发、筛选、模型训练或确认期评价。

建议先完成一个 **2010–2023、765 因子、三套评价器共用输入的 Evidence Board MVP**，再一次性冻结候选规则并交人工审阅。优先修复输入、标签、缺失样本与指标定义；复用成熟评价函数，不扩因子池、不设计人工加权总分、不自动选 Top 50。

## A. Current-State Audit

### A1. 审计基线与证据强度

- 仓库：`qlib_baseline`；本地分支 `main`。
- 本次审计基线：`972c6d1c35b53012a163fed4ab66ce48ec94dd50`，提交日期 2026-09-03。
- 编写时通过 `git ls-remote origin refs/heads/main` 确认远端 `main` 与本地一致；审计前工作区干净。
- 已阅读相关 authority 文档、实现和历史结果，检查 canonical manifest/lineage/partition metadata、本地交易日历、经济映射及依赖源码存在性；重新计算 canonical identity，核对 498 个分区路径全部存在。
- **没有重新逐哈希扫描 498 个大分区，没有全量读取因子值，没有执行评价器 smoke/full run。** 分区完整性、PIT 与数值正确性的既有结论来自已关闭的 canonical assembly；本次路径存在性检查不等价于新一次完整数据认证。
- 本文对未完成部分标注“待验证”或“拟新增”，不把历史报告、静态代码检查、开发建议写成已通过的运行结果。

现行边界见 [项目上下文](PROJECT_CONTEXT_SUMMARY.md)、[当前流水线](CURRENT_PIPELINE.md) 和 [Canonical 数据合同](CANONICAL_RESEARCH_DATASET.md)。Forward Track 仍有时间优先级，Strategy V1 保持冻结。

### A2. 数据与因子池的实际状态

重新计算得到的 identity 与 authority 一致：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

本地机器入口为 `outputs/canonical_historical_dataset_assembly_v1/current/` 下的 `manifest.json`、`partition_manifest.csv`、`factor_lineage.csv`。范围仍是 **2010-01-29–2026-06-09**；774 个唯一定义，765 个 research-usable，9 个 blocked。

| Factor source | 定义数 | Research-usable |
| --- | ---: | ---: |
| Alpha158 | 158 | 158 |
| Alpha360 | 358 | 358 |
| Alpha101 | 104 | 97 |
| TA | 81 | 79 |
| mature_public | 58 | 58 |
| project_basic | 15 | 15 |
| 合计 | 774 | 765 |

来源名中的 Alpha360/Alpha101 不等于此仓库唯一可用定义的数量。9 个 blocked 是：Alpha101 的 alpha021、alpha023、alpha027、alpha027_canonical_vwap_v2、alpha068、alpha086、alpha086_canonical_vwap_v2，以及 `ta_trend_psar_up`、`ta_volatility_kcp`；原因分别包含无有限值、常数/退化、历史覆盖不足和非有限值。

需要保留的资格限制：765 是继承自 **2021+ physical qualification** 的固定研究库存，不是“每个因子自 2010 年起均完整可用”的保证，也不是完全未使用后期信息形成的因子清单。本轮不重选这个库存，但必须重新给出 development-only 的可用性和起始日期；不得以旧 `global_coverage` 作为本轮新资格判断。9 个 blocked 留在 inventory 中说明原因，不自动解封。

Canonical 已统一修复 15 个 Alpha101、KAMA 和 19 个 fundamental 的跨段实现语义；`read_effective_partition` 必须按 effective dates 裁剪，不能把 parent parquet 全范围当 canonical 范围。详见 [assembly 报告](../reports/canonical_historical_dataset_assembly_v1/REPORT.md)。

### A3. 实际调用链与必须纠偏之处

**Multi-Source Screening 是历史结果组装器，并不是三个评价器的统一计算入口。**

1. [V4 runner](../scripts/run_factor_evaluation_v4.py) 调用 V3 的 `load_window_frame`：从 provider 读取、计算 basic factors、附加 tradability/data-quality，再强制做 tradable filter；可另外 merge external factor frame。
2. [dataset.py](../factor_research/dataset.py) 的 `to_factor_data` 产生含 factor value、quantile、label、forward_return 的长表。
3. [adapters.py](../factor_research/external/adapters.py) 的 `to_alphalens_factor_data`、`to_jqfactor_inputs`、`to_qlib_score_frame` 分别转换格式。
4. V4 的 `run_alphalens` / `run_jqfactor` 直接调用各自 `performance.py`；`run_qlib_eval` 当前由 pandas 算每日 Spearman，再调用 Qlib `risk_analysis`。
5. [summary.py](../factor_research/external/summary.py) 整理原始输出为 status / metric index。
6. [multi_source_screening.py](../factor_research/multi_source_screening.py) 读取 Alpha158 pool 和 TA/Alpha101/Alpha360 promotion、coverage、metric CSV，合成 screening input / board / pool。
7. [multi_source_judgement.py](../factor_research/multi_source_judgement.py) 再按历史规则分类；Alpha158 保留上游角色，新来源使用独立 probe 规则。

这条链尚未统一接入 canonical 765 因子长历史矩阵，且历史 source-specific 组装结构没有自动覆盖 basic/mature_public。应复用底层函数与输出命名，增加小型 canonical 编排入口，不能只改旧配置的起止日期。

三套 adapter **没有各自拉价格生成收益**，这一点符合需求；但共同上游并不等于输入已经满足新合同：

- 旧上游和 Phase 0 标签加载器使用按 instrument 的物理行 `shift(-21)/shift(-1)`；遇到 instrument/date 缺口时存在与交易日位置不一致的风险。此为代码路径风险，尚未用全量数据证明历史结果出错。
- Alphalens/jqfactor 对多个 horizon pivot 后整表 `dropna()`，会受到另一 horizon 或 quantile 缺失牵连；Qlib 按单 label 取样，相关函数再成对排除缺失，输入集合可能不同。
- adapter 的 `pivot_table(aggfunc='first')` 和 `drop_duplicates` 会折叠重复键；新入口必须提前拒绝重复或冲突，不能靠 adapter 消化。
- V4 的 `min_count` 配置不能视为三 backend 已一致执行的证据；`to_factor_data` 的 quantile 检查主要是可分桶数量，Qlib 包装函数没有统一的最小横截面约束。
- Qlib 包装只计算 Rank IC 及对 IC 序列的 risk summary，没有完整调用 Qlib-native IC、Pearson IC、long-short。其 `annualized_return` / `max_drawdown` 是对 **IC 序列** 的汇总，不是投资收益或策略回撤。
- 本地 Qlib 已有 `qlib.contrib.eva.alpha.calc_ic`、`calc_long_short_return`，可直接复用。后者返回 `(long-short)/2`，不能与 Alphalens/jqfactor 的 Q5−Q1 不经定义对齐就做数值 parity。
- [source_manifest.yaml](../factor_research/external/source_manifest.yaml) 保留版本/许可证线索，但 Qlib 列举的 API 与当前实际调用不完全一致，部分 source 描述仍写 future。运行前应记录实际代码 hash/版本，不能仅相信该历史清单。
- 两套 external `performance.py` 在本机存在；依赖导入和原生函数在当前环境是否成功，留待 smoke。历史 jqfactor 有 alpha/beta、factor_returns index-name 的 partial-pass 记录，不能默认当作已修好。

### A4. V4 已有证据、历史规则和缺口

| 对象 | 已实现 | 本轮判断 |
| --- | --- | --- |
| Alphalens | 日 IC、mean IC、quantile return/std error、factor return、alpha/beta、1/5/10 日 rank autocorrelation、top 1/5 日 turnover | 复用；增加逐日 quantile 输出供分段统计，保留原生参数和失败原因 |
| jqfactor | 日 IC、mean IC、quantile return/std error、factor return、alpha/beta、top 1/5 日 turnover | 复用；yearly/ICIR 目前不是完整统一输出，需由原生日序列汇总 |
| Qlib wrapper | pandas Spearman + Qlib risk_analysis | 改接已有 Qlib-native alpha API；旧 risk-on-IC 字段仅作 legacy |
| Context | index segment、listing age、benchmark-relative/grouped evidence；项目已有 neutralization/exposure 诊断 | 保留为可选 secondary；不要求主评价依赖全历史不完整的 context |
| Annual / broad eras | 已有时间切片、rolling stability、Phase 0 period calendar/period aggregation | 算法和数据结构可复用；未形成 765×3、2010–2023 full/annual/era 标准产物 |
| BH/FDR | BH/BY、moving-block、gap-aware bootstrap 已实现 | 复用函数；旧 669 因子、outer/inner split 输入与 family 必须更换 |
| Economic map | taxonomy 774 行，economic_map 765 行，覆盖全部 765 usable，lineage 的 family 无空值 | 不用重建；列完整不表示机制/文献强度一致，保留 ambiguous/weak 状态 |
| Duplicate / clustering | definition/proxy equivalence、数值 hash profile、daily-IC/exposure similarity、hierarchical clustering | 复用工具；尚无本轮 2010–2023×765 的完成结果，不继承旧代表因子选择 |

现有 `multi_source_judgement` 用 `max_abs_mean_ic` 跨 10D/20D 取最大值，并把多套 IC/IR 的符号观察合在一起；它不等于每个 backend 一票的 3/3。旧 coverage=0.90、IC=0.015/0.03/0.05、Qlib IR=3/4、direction ratio 等只保留 provenance，不能进入新版默认 selection。

目前的新长历史 selection authority **尚未形成**。旧判断对其历史池、冻结 Strategy V1 仍有追溯意义；在本轮一律降级为历史证据，不覆盖原 artifact。项目的 PIT、输入完整性、冻结数据身份和时间隔离仍是 correctness authority，不能与旧 alpha threshold 一起取消。

### A5. 与附件及现行路线的差异

| 问题 | 实际仓库状态 | 新计划处理 |
| --- | --- | --- |
| 774/765 是否过时 | 未过时，已由本地 lineage 复核 | 固定库存，不扩容 |
| universe 混用 | `factor_research/config.yaml` 确为 2010–2016/2017–2020 raw、2021+ tradable_only；旧中间窗口还止于 2020-08-01 | 新建连续 2010–2023 读取合同，不复用旧窗口清单 |
| 是否已有长历史工作 | [原路线](LONG_HISTORY_ROBUST_CORE_FACTOR_SELECTION_V1.md) Phase 0 已关闭，91 因子 backward replication 已完成 | 不重做 91 因子旧结论冻结；其结果作为已观察历史 |
| 最近区间是否未见 | [Phase 0 报告](../reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md) 已报告 2021–2026；旧路线 Phase 2 也包括 2023–2026 | 新版锁住 2024+，仅为本轮 protocol 的 confirmation，绝非 fresh OOS |
| 目标是否直接 Core | 原路线还包括四 pillar/grade/Pareto、Core team、停止规则 | 本 MVP 收缩为 evidence → candidate → 人工审阅；Core/组合/模型移后 |
| Fast 8T 是否直接覆盖 | 已认证的 8T 是 LightGBM/Fast/Full 模型执行路径 | 复用缓存/确定性经验，不能宣称三个 Python evaluator 已获 8T exact-parity 认证 |

本计划的 Phase 0–4 是 **MVP 自己的阶段编号**，不表示重新打开原路线已关闭的 Phase 0。后续实施启动时再同步当前路线的状态/范围；本次只新增计划入口，不静默替换现行 authority。

## B. Proposed Research Contract

### B1. 时间、标签与锁定边界

| 合同项 | 建议冻结值 |
| --- | --- |
| Screening/development 数据区间 | 2010-01-29–2023-12-29；本地日历共 3,382 个交易日 |
| Locked confirmation 请求区间 | 2024-01-01–2026-06-09；首个实际交易日 2024-01-02 |
| Primary label | `label_20d_t1 = close[t+21] / close[t+1] - 1` |
| Auxiliary label | `label_10d_t1 = close[t+11] / close[t+1] - 1`，只作稳健性标注 |
| 本轮价格读取上限 | 2023-12-29；两个标签都要求 entry/exit 实际日期不越界 |
| 20D 最后可成熟信号 | **2023-11-30**，最多 3,361 个信号交易日，个别股票还可能缺价格 |
| 10D 最后可成熟信号 | **2023-12-14**，最多 3,371 个信号交易日 |
| 未来确认期成熟上限 | 若以 2026-06-09 为价格截止，20D/10D 分别到 2026-05-11 / 2026-05-25；本轮不计算 |

上表日期来自本地 provider 的 `calendars/day.txt`，不是按工作日近似。`close` 使用同一 provider 的 `$close` 权威口径，entry 是 T+1 收盘而非 T+1 开盘；在 Phase 0 绑定 price source/hash、复权与单位合同。这里的标签用于预测评价，不代表已模拟可成交交易。

复用 [labels.py](../research_validation/labels.py) 的 `build_label_date_map` / `build_exact_calendar_label`，在 canonical date/instrument keys 上，以精确交易日查 entry/exit close，不按物理记录顺序移位，不填充缺失价格，不对 labels 中性化或标准化。已有 labels 若满足同一 source、日期、公式、key hash 才可复用；旧 `full_research_labels_v2` 的 2021+ 范围不能直接覆盖本轮。

年度和 Era 按 **signal date** 归组：2014 年末的持有区间可以落入 2015 年，只要 exit 不超过全局 2023-12-29。它们是有重叠的描述性历史切片，不是假设相互独立的 train/test；每段记录 actual signal start/end 和最大 exit_date。不得将最后 21 个信号日的未成熟值填成零，也不得为了保留 2023 年末信号而偷偷读取 2024 年价格。

### B2. Primary / secondary universe

建议 primary 使用全历史一致的 **canonical practical raw universe**：以 canonical keys、dated lifecycle 和 market presence 为权威，进行统一有限值和 schema 校验，不追加分时期的 tradable_only 或固定当今股票列表。

这里的 raw 仍受 canonical 原始样本合同约束，不表示所有历史 A 股的无偏完整样本。已有 assembly 对 practical historical universe 给出通过结论；但当前证据不足以证明全历史 ST、涨跌停、停牌、流动性 metadata 能可靠重建。故无需为了统一过滤重新开启 Historical Data Engineering；只有具体 keys/PIT correctness bug 才作为 blocker 修复。

Secondary 在 **2010–2023 内实际可靠的时期** 检查 tradability、size/liquidity/microcap 暴露。2021–2023 是已有配置入口，仍需检查字段覆盖、日期和信息可得时点，不能默认合格。metadata 不足写 `unavailable`，不得合成伪 ST/limit 数据，也不得借用 2024+ 样本。primary/secondary 分开输出 universe_id、有效日期和样本量，不拼接成一条“稳定性”序列。

按 `factor × label` 建立共同 IC 样本：canonical membership ∩ finite factor ∩ finite matured label ∩ 同一最小横截面规则。primary 20D 不因 auxiliary 缺失而删行，不取所有 765 因子的完整案例交集。建议沿用 V4 的 50 个样本/日作为待 smoke 验证的计算可定义性下限，明确它不是 alpha threshold。

Quantile 使用独立明确的有效分桶 mask，低值为 Q1、高值为 Q5；保留 ties/不足五桶的实际状态，不因不能分桶就自动删除原本可计算 IC 的日期。IC mask、quantile mask 各有 hash，三 backend 在对应指标上使用同一份样本。

### B3. Full / annual / broad-era evidence

- Full：整个 development 的成熟标签样本。
- Annual：2010–2023，14 个年度，包含有限样本量、日 IC 分布和符号序列。
- Broad eras：A=2010–2014、B=2015–2017、C=2018–2020、D=2021–2023，共四段；采用附件建议并在结果之前冻结，不沿用旧 Phase 0 的不同边界做数值直比。

三层证据均保留 backend/label/universe 维度，段缺失显示 unavailable。记录 mean/median IC、非年化 ICIR、明确约定的年化版本、valid dates、sign ratio、spread 等。Full mean 由原始有效日序列算，不能平均年度 ICIR 或无权平均各年 mean 代替。

各 Era 不做硬 AND gate。先展示 directional annual/era sequence、worst era、leave-one-era-out mean、各 Era 对全期总 IC 的贡献等描述量，候选规则阶段再一次性定义 `direction_instability`、`regime_concentrated` 等标注条件。不给不同时期额外权重，不搜索 era 边界，不新增 rolling/window 参数搜索。

### B4. Evaluator 的角色与 agreement

保留三个原生 namespace 的独立原始输出，不用一个统一计算结果伪装成三个 backend。原始值方向始终保留；未来候选展示方向要单独存 `analysis_direction`、`direction_origin`、`direction_freeze_id`。

同样本下 Alphalens/jqfactor 的默认 IC 是 Spearman，应该与 Qlib Rank IC 对齐，而非 Qlib Pearson IC。共同定义的指标做严格 parity；demeaning、权重、分桶、年化、long-short 缩放不同的指标保留定义后解释，不强行做相等断言。尤其不能把 20D overlapping spread 当每日可复利策略收益，不能把 risk-on-IC 的回撤写为交易回撤。

Agreement 分两层：

1. Phase 1–3：`parity_status`、符号一致数、`backend_available_count`，只说明实现对齐；尚未冻结 alpha pass 条件时不提前填“3/3 因子合格”。
2. Phase 4：每 backend 按事先冻结的 20D rule 输出 pass/fail/unavailable，形成 3/3、2/3、1/3、0/3 evaluator agreement；unavailable 单独列出，不能把 2 个成功后端伪装为 3 个，也不能把运行失败解释为 0/3 无 alpha。

三 backend 高度共享数据与核心统计量，agreement 是 implementation consensus，不是三个统计独立实验。若唯一指标就是相同 Rank IC，3/3 很可能是预期结果，不能据此声称统计显著性增强。

### B5. Multiple testing 与候选规则冻结

Phase 0 冻结统计程序、检验 family、主 label、原始方向/双侧检验和 seed；Phase 4 在首次全量 development 分布出来后，记录一次有理由的 candidate threshold 决策。两者区分开：不能到看到结果后再挑检验方法、主 horizon 或检验对象。

复用 [bootstrap.py](../research_validation/bootstrap.py) 的 gap-aware moving-block mean test 和 [multiple_testing.py](../research_validation/multiple_testing.py) 的 BH/BY。建议起始参数为 primary 20D 的 block_length=20、bootstrap_samples=1000（沿用已存在参数，仅是实施建议）；在正式 full 前用 synthetic/null smoke 验证适用性和 p 值分辨率。每日 IC 先 reindex 到完整允许交易日，保留 NaN gap，否则 gap-aware 也会错误跨缺口抽样。长自相关、短片段排除比例和 bootstrap Monte Carlo 分辨率明确披露，不把旧 block_length 视为已在新历史获证。

Primary family 是本次冻结的 765 因子库存中所有可检验 20D/full/raw 假设，测试前列清单，数量由数据可定义性决定；不得先按高 IC 或候选 backend agreement 筛完才做 FDR。缺乏可检验数据的因子留行说明，必要时以保守 p=1 纳入 planned-family 校正视图。由 parity 通过的 Qlib-native Rank IC 序列承担一套正式检验，其他 backend 是实现核对；不把同一假设乘三提高证据。10D、annual、era 默认描述性，不作为另一次挑优的显著性通道。若另外报告其检验，必须分开登记 family 和探索性地位。

一次性冻结的 `candidate_rules.yaml` 应写明来源、方向政策、quality、三 backend 条件、FDR 的使用方式、缺失处理及标注规则，并绑定 evidence/config/code hash。不得按目标候选数反复松紧调节；规则变化保留旧版本且重新声明为 development 探索，不能访问 confirmation。没有经济方向先验的因子可以用 development 全期方向形成候选描述，但必须标记 data-derived，不能伪装成事前经济预测。

## C. Reuse Map

| 分类 | 模块/产物 | 具体用法及限制 |
| --- | --- | --- |
| 直接复用 | [canonical_dataset.py](../research_validation/canonical_dataset.py) | identity、effective partition 读取；外层先收窄 development dates，禁止读取后才裁掉 locked 数值 |
| 直接复用 | [labels.py](../research_validation/labels.py) | 精确日历标签；给本轮两个 horizon 新建独立受限 cache |
| 直接复用 | 两个 external performance 模块、Qlib `eva.alpha` | 调用原生 metric，不复制实现；固定版本/参数 |
| 直接复用 | economic_map、taxonomy、[duplicate audit](../reports/factor_universe_v2/duplicate_equivalence_audit.csv) | 仅取 identity/family/mechanism/lineage；旧 coverage、outcome、direction 不自动进入本轮选择 |
| 小幅修改 | V4 runner / external adapters / summary | 接 canonical frame，单 horizon mask，重复键检查，原生 Qlib、分段汇总、metric-level status |
| 小幅修改 | [feature_eligibility.py](../model_research/feature_eligibility.py) | 复用 profile 与 content hash；单一 development 输入，去除旧 outer-split runner 耦合；profile 内用于诊断的插补不能写回 evaluator 输入 |
| 小幅修改 | [backward_replication.py](../factor_research/backward_replication.py) | 借用分区循环、period aggregation、计时和缓存思路；不调用固定 91 因子/旧方向/旧标签入口 |
| 小幅修改 | bootstrap / FDR / rolling 汇总函数 | 换本轮日 IC 与 family；不加载旧 split assignments、不重跑 nested/rolling 搜索 |
| 可选复用 | [factor_similarity.py](../factor_research/factor_similarity.py)、[factor_clustering.py](../factor_research/factor_clustering.py) | 限 development 的 redundancy metadata；暴露相关全量矩阵可延期，不自动删 N−1 |
| 需要新增 | 一个小型 `factor_research/long_history_screening.py`、一个 runner、一个 YAML | 仅负责受限读取、编排、证据汇总和候选提取；避免再建 manager/registry 框架 |
| 需要新增 | 本轮合同、parity receipts、Evidence/Candidate Board schema 和聚焦测试 | 独立 run_id、可恢复批次和阅读报告 |
| 退出新选择路径 | 旧 `multi_source_judgement`、source promotion 阈值、旧 recent_oos 选择、旧代表因子强删 | 原文件不删除、不移动、不改写；在新报告标 legacy provenance |

保留 Qlib dataset/feature order/Recorder 的后续兼容字段，但本轮不创建训练 dataset、不启动 Recorder 模型任务。无需为了这份计划抽取一个新的通用平台。

## D. Phased Development Plan

下面为后续实施工作包；本次交付不运行其中任何阶段。

建议运行目录为 `outputs/long_history_multi_evaluator_screening_v1/<run_id>/`，其中按 `phase0`、`smoke`、`evidence`、`candidate` 分目录；缓存位于 `tmp/long_history_multi_evaluator_screening_v1/`。人工报告与小型汇总进入 `reports/long_history_multi_evaluator_screening_v1/`，冻结规则对象按既有 content-addressed 方式保存在 `artifacts/`。运行数据默认不进 Git，不覆盖任何旧 `current/` 或 Phase 0 输出；遵守 [输出政策](OUTPUT_POLICY.md)。

### Phase 0 — Research contract / semantics audit

**依赖：** 本计划作为后续实施基线；不重做原路线已完成 Phase 0。

工作：绑定 commit/data identity、765 清单及 9 blocked、原生源码版本；建立只有 development 的读取路径；导出 label date map；确认 practical raw keys；仅做 feature-only profile；冻结三层时期、检验方法、输入 mask、metric definitions 和资源上限。抽取少量 canonical 行做精确日历标签核对，检查分区交接、fundamental availability 和 factor 起始缺失。

拟新增路径：`configs/long_history_multi_evaluator_screening_v1.yaml`、`scripts/run_long_history_multi_evaluator_screening_v1.py`、小型编排模块。这些路径目前是设计，不是已有可执行命令。

产物：`resolved_config.json`、`input_identity.json`、`factor_inventory.csv`、`feature_quality.csv`、`label_date_map.parquet`、`universe_contract.json`、`metric_definitions.json`、`access_audit.csv`、`job_inventory.csv`。

验收/停止：身份、重复键、PIT 和时间越界问题必须修复；确认无 2024+ values/returns/outcomes 可进入 evaluator。某个因子局部缺失记录状态；整库不可读或价格口径不清则停止。不能因旧 90% coverage 就提前淘汰大批长历史因子。

### Phase 1 — Evaluator parity smoke

**依赖：** Phase 0 correctness 合同通过。

先用 synthetic fixtures 验证正/负相关、ties、常量、NaN/inf、股票缺交易日、标签不同成熟日，再按 source/family/lineage 预选 **24 个**真实代表因子，固定清单后才读其 alpha。

建议配额：basic 3、Alpha158 4、Alpha360 3、TA 4、Alpha101 4、mature_public 6。覆盖 momentum、reversal、value、quality、volatility、liquidity、size、fundamental；Alpha101 至少包含已修正项与 legacy/canonical 对照，TA 包含 KAMA，fundamental 包含 PIT 财报因子。24 个具体名字由 lineage 与 family 交集确定，不按旧/新好成绩挑选；无法覆盖的类别记录原因。

两级 smoke：先 6 因子×2 horizon×3 backend×60 个交易日用于接口与资源探测；再 24 因子跨四 Era 各一段预先固定的 60 个交易日，并将其中 6 因子跑完整 development 检查长期累计行为。短窗结束允许用 development 内 label tail；不访问 locked 区间。保留年度/era汇总的 synthetic oracle。

逐日核对 row count、key hash、value/label hash、missing reasons、IC sign/magnitude、quantile direction、metric availability。共同定义 Rank IC 建议 `atol=1e-10, rtol=1e-8`；这是工程容差，smoke 前冻结，数值差超过容差需定位原因，不能看完因子结果再放宽。浮点零附近按容差处理符号，不制造假冲突。

产物：`smoke_factor_inventory.csv`、各 backend 原始输出、`adapter_parity.csv`、`metric_parity.csv`、`failure_reasons.csv`、`runtime_timing.csv`、`resource_estimate.json`。

验收/停止：任何共同指标符号反转、label/key mismatch、静默丢样本或主 IC backend 不可用都阻止 full。原生附加 alpha/beta 失败可在原因清楚且非候选必需指标时列为 partial evidence；不得将缺失指标算作 pass。修复共享函数时回归已有 adapter/V4 合同，不修改 frozen evidence。

### Phase 2 — Long-history full-factor evaluation

**依赖：** Phase 1 parity 通过，并用实测数据更新计算计划。

全量枚举 765 research-usable；数据不可定义者保留 failure/quality 行，不能静默漏因子。canonical factor/labels/universe 预计算一次，共享到三个原生 evaluator；依照分区与因子块逐批落盘，可恢复到失败批次。先完整落 primary 20D 以尽快看到证据，再完成全部 10D 辅助证据，最终验收不能仅交 primary。

保留每个 backend 的每日 IC、分桶/收益、turnover/autocorrelation 序列，再产生 full/annual/era 汇总。均值等可从日序列汇总；alpha/beta、标准误等不能平均已有汇总值，应对相应切片复用原生函数。分块需要正确 carry 前期 rank/持仓集合，避免每个年度重置 turnover 导致假跳变。

执行本轮 primary bootstrap/FDR，但在 Phase 4 前不据此反复删改运行清单、不正式选候选。metadata、失败、日序列、汇总与缓存分开，不生成全股票×765×2 的巨型长表。

产物：`raw/<backend>/`、`daily_metrics/`、`factor_period_metrics.parquet`、`data_quality_by_period.csv`、`multiple_testing.csv`、`test_family_inventory.csv`、`batch_status.csv`、`run_manifest.json`。

验收/停止：所有计划 job 都必须有 success/unavailable/failed 状态；重要 failures 未解决时整体标 incomplete。禁止静默 fallback 到旧矩阵/label/阈值。缓存损坏拒绝使用，重跑受影响批次；重大语义修复使受影响证据失效并重跑，不能只修报告。

### Phase 3 — Evidence Board construction

**依赖：** Phase 2 完整性检查通过；可随批次预览，最终完整版本统一封存。

构建长表和一因子一行的宽版索引，附完整可追溯 raw paths。加入年度符号序列、Era 贡献、availability、经济 family、重复关系及 secondary diagnostics。exact duplicate 可复用完全相同输入的计算，但仍保留所有因子行及别名映射；canonical/legacy 语义不同不能仅因名字近似合并。

拟定最小 schema：

| 产物 | 主键及核心字段 |
| --- | --- |
| `factor_inventory.csv` | factor；source、family、canonical/legacy mapping、research_usable、block_reason、definition/lineage hash |
| `factor_period_metrics.parquet` | run_id/factor/backend/label/universe_id/period_id/metric；value、unit、direction_mode、valid dates/samples、raw_path、status |
| `factor_evidence_board.csv` | factor；coverage/missing/finite、first/last usable、三 backend full 指标、annual/era 索引、parity、可用 backend 数、reason codes |
| `robustness_annotations.csv` | factor/annotation/universe/period；direction instability、regime concentration、size/liquidity、turnover、duplication、证据路径 |
| `candidate_board.csv` | factor/rule_version；各 backend pass/fail/unavailable、agreement、candidate_status、analysis_direction/source、FDR、review reasons |
| `pool_exports.json` | pool_id/rule_version；ordered factor list、definition hash、selection period、evidence references；本阶段可只保存预留结构 |

所有宽表均从原始证据生成，缺失与失败不同于数值 0。Board 必须容纳无完整 14 年历史的因子，并展示其有限证据，不把 full-schema frontier 当首次可用值日期。

验收/停止：765 行一一对应，9 blocked 在 inventory 附录可查；关键指标可从 raw 重算，时间窗不混用，source 与 backend 字段分离。产物为 CSV/Parquet/Markdown，先不开发 Web UI。

### Phase 4 — Candidate-rule freeze / candidate extraction

**依赖：** Phase 3 完整 Board 和首次经验分布。

先保存不含最终 pass 的完整 evidence snapshot，再基于 development 分布、既有规则出处、FDR、annual/era 与经济解释制定一次 candidate rule。候选数量是结果，不能设成调参目标；不同 source 不享有 Alpha158 旧池特权。允许 stable/conditional/review 等有原因的状态，不把 Era 全通过作为默认条件。

冻结规则及方向后一次提取 Candidate Board，并保留 old selected/rejected 作为旁证。旧方向若来自包含 locked 年份的历史判断，仅作 legacy 字段，不直接决定新版方向。对外输出候选表、未进入候选的原因和全部 evidence，而非“最终最佳因子池”。

产物：`candidate_rules.yaml`、`candidate_rule_rationale.md`、`candidate_rule_freeze.json`、`candidate_board.csv`、`candidate_factors.csv`、`review_queue.csv`、`REPORT.md`。

验收：相同 evidence/rules 重跑候选集合与顺序一致；仅改 locked synthetic 数据不影响任何本轮输出；没有自动 horizon 切换或按照候选个数调阈值。Phase 4 明确保存 confirmation 仍未读取的状态。

### STOP POINT — 人工审阅

交付完整 Evidence Board、Candidate Board、agreement/parity、年度/Era 稳定性、失败/限制、冻结规则和复现入口后停止。**不执行** locked confirmation、经济组合优化、Core team、LightGBM 重训、rolling redesign、Strategy V2。

后续接口应支持 Old Pool、Broad Quality-qualified Pool、Consensus Pool 和少量人工 Economic Combos。Old Pool 保留冻结 52 因子顺序；新数据上的实验副本另建身份，不改 Strategy V1。下一阶段再统一模型/训练日期/成本口径比较 Rank IC、ICIR、yearly/worst period、P01/spread、turnover、cost-adjusted return 和 drawdown；本轮不生成伪交易绩效承诺。

## E. Validation Plan

| 阶段 | Correctness / data contract | Parity | Leakage | Determinism / artifact |
| --- | --- | --- | --- | --- |
| 0 | identity、effective dates、unique keys、finite、dated universe；精确 entry/exit hand-check | exact-calendar helper 与无缺口参考公式一致，有缺口 fixture 能揭示 row-shift 差异 | price/factor read filter 最大 2023-12-29；exit 超界拒绝；PIT event availability | sorted inventory/config hash、只读 parent、独立 output root |
| 1 | NaN/inf/ties/constants、min-count、quantile、单 horizon mask | 三 backend 同 key/value/label；每日 Rank IC 容差；native long-short 定义单独核验 | mock/spy reader 拒绝 locked 请求；20D 不受 10D missing 牵连 | 顺序两次与小并行一次；冻结 seed、版本、排序；区别 binary hash 与逻辑内容 hash |
| 2 | 765 job inventory、批次不漏不重、annual/era coverage、groupby 日期连续性 | 每批共享样本 hash，全量共同 Rank IC 比较；不可比 metrics 不能误判失败 | 所有 stage 只消费 development artifacts；bootstrap 输入无 locked dates | cold/cache-hit、恢复重跑、不同块大小抽查一致；损坏缓存被拒绝 |
| 3 | raw→long→wide 可追溯、一对一 factor identity；失败≠0 | 同一 backend annual/full 重算一致；不平均 ICIR | economic map 仅读描述列；旧 outcome/coverage 不进入 selection payload | Board 行序和 reason codes 稳定；完整性计数匹配 manifest |
| 4 | rule_version/evidence identity 唯一、未测因子状态明确、FDR family 无事后删减 | 规则输入和 backend pass 可复算 | locked synthetic values/prices/outcomes 扰动后候选/方向/阈值不变 | 同规则同证据候选完全一致；freeze 后不能覆盖旧版本 |

重点扩展既有 [canonical tests](../tests/test_canonical_dataset.py)、[label tests](../tests/test_full_research_labels_v2.py)、[future-leakage tests](../tests/test_no_future_leakage.py)、[bootstrap tests](../tests/test_bootstrap_gap_aware.py)、[multiple-testing tests](../tests/test_multiple_testing.py)，并新增本轮 thin-runner/adapter parity 的聚焦 tests。测试目录名可在实施时按现有覆盖组织，不要求为每个字段机械造测试。

Locked 防护分为：输入文件/分区日期 allowlist、读取 filters、label exit 断言、candidate schema 列 allowlist 和 synthetic mutation test。历史 metadata/manifest 可能描述全 canonical 范围，允许作为身份读取；不允许把 locked 区间的因子值、收益、coverage、旧 outcome 或含该段的方向结论作为新规则输入。若 parquet 物理上含跨界 row group，允许必要字节校验，但有效输出行与后续计算必须受 filters 限制；记录这种存储与研究读取的区别。

本次仅文档变更执行 [CI 政策](CI_POLICY.md) 的 docs/repository 快速检查和本地链接检查；上述研究测试属于后续开发验收，不在撰写计划时启动全量计算。

## F. Compute Plan

### F1. 计算集合

| 范围 | 计算量/用途 |
| --- | --- |
| 固定 inventory | 774 定义；765 planned usable；9 blocked 不进入 evaluator |
| 最小真实 smoke | 6×3×2=36 个 factor/backend/horizon 单元，单段 60 个交易日 |
| 扩展 smoke | 24×3×2×4=576 个短段单元；另 6×3×2=36 个完整 development 单元 |
| Full 核心任务 | 765×3×2=4,590 个逻辑 factor/backend/horizon 单元；实际可批处理 |
| 时间汇总视图 | 1 full + 14 annual + 4 era =19；最多 87,210 个 factor/backend/horizon/period 单元，每单元有多项 metrics |
| 日 IC 规模 | 20D 最多 3,361 日、10D 最多 3,371 日；三 backend 合计最多 15,449,940 行日 IC 证据，不含 Pearson 等额外指标 |
| Primary FDR | 最多 765 个正式假设，bootstrap 1,000 次为初始建议；不乘 backend、年度或 Era 数量 |
| Secondary | 只在可靠 development 子区间，另记 jobs；不混入 4,590 基础量，不作为全主表交付的隐形前提 |

87,210 是逻辑证据视图数量，**不是** 87,210 次从 provider 重读全矩阵。Annual/Era 尽量从原生日序列汇总；需要原生非线性统计的指标仅重跑对应函数。

### F2. 共享预计算、内存与并行

一次性共享：canonical inventory/keys、calendar、20D/10D labels、feature quality、逐 factor/horizon masks、quantile assignments。三个 backend 各自计算主要 IC，不能共享一份 IC 然后复制三份；共用样本排序、输入准备和后续汇总缓存即可。

Cache identity 至少包含 canonical id、实际 source hash、effective/read dates、label公式和价格/calendar hash、universe/mask policy、factor definition、quantile、backend code/version/参数。旧 provider-basic cache、旧 669 daily IC、旧 2021–2026 方向/IC cache 不能只因 factor name 相同就命中。

建议先单 worker，之后测试 2 个因子/分区 worker，每 worker 内部数值库先设 1 thread，避免外层 worker×内部 8T 过度并行。24 因子 parity/资源测量通过才考虑 4 worker；不默认沿用 LightGBM 的 8T 加速倍数。原生 evaluator Python groupby/rank、IO、GC 和 pickle 可能成为瓶颈，进程/线程选择以实测为准。

按平均 2,000–4,000 股票、3,382 日作粗略容量示例，765 列 float64 仅数值就约 39–77 GiB，尚未计索引、副本和两份标签展开；实际样本规模须从限定分区统计。故按 canonical 分区、16–32 因子作为初始块，转换长表时进一步缩到单因子/单 horizon。quantile/turnover 时间状态跨块保留；不假设年度 parquet 可以无状态独立计算全部指标。

遵循 Forward 优先级，smoke 记录 peak RSS、CPU、读写 GB、每 source 的 median/p95 耗时与缓存命中率；并行前按 `shared_RSS + workers × p95_worker_RSS` 留足系统及 Forward 内存，不仅按 CPU 核心数选 worker。

### F3. 时间估算与反馈节奏

[已完成 Phase 0](../reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md) 的 91 因子、单 20D Rank IC、2010–2026 冷计算耗时 3,147.7 秒，整个 cold run 3,223.4 秒，cache replay 75.5 秒。按因子数与交易日线性外推，本轮单套 Rank IC 大致 **6–8 小时量级**；这只是不同计算链的参考，不是三 evaluator 全指标 benchmark。

完整三 backend、两个 horizon、quantile/turnover/alpha-beta/bootstrap 的首次运行先预留 **1–3 个工作日的机器窗口**，可信度低；实际受缺失、分桶实现、IO 与并行影响。Phase 1 后采用 `sum(source_factor_count × source/backend/label 实测耗时) / 实测并行效率 + I/O/bootstrap/汇总开销` 更新，附低/中/高估计。不要为了估算提前启动 765 全量 run。

首次反馈顺序：合同与最小 smoke → 24 因子 parity 与资源报告 → 全量 primary 20D evidence preview → 完整 10D/full/annual/era Board → 规则冻结和候选。若预算超出约定窗口，先减少非关键 context/图片与重复 IO，保留 primary、三 evaluator parity 和全因子清单；未完成部分标 incomplete，不把样本化 run 叫 authoritative full。

实施工作量粗估（不含 full 机器等待）：Phase 0 1–2 人日、Phase 1 2–3 人日、Phase 2 编排 1–2 人日、Phase 3 1–2 人日、Phase 4 0.5–1 人日，共约 5.5–10 人日。以 adapter 修复规模为主要不确定性；不安排新框架或模型工程。

## G. Risks / Open Decisions

| 风险/决定 | 当前建议 | 验证阶段与升级条件 |
| --- | --- | --- |
| Practical raw ≠ 完美 PIT/tradable universe | 复用 canonical dated keys，secondary 单列；不伪造旧 ST/limit | Phase 0 发现具体非法 keys/未来 membership 才重开数据修复 |
| 最近区间污染 | 只锁住新版 protocol；披露此前 Phase 0、旧筛选及 765 qualification 已观察后期 | Phase 0/4 allowlist、exit 与 mutation tests；不能声称恢复 fresh OOS |
| 标签物理行 shift、边界、复权 | 复用 exact-calendar helper，冻结 price source；缺价 NaN | Phase 0/1 精确日期 fixture，price/source 不清即 blocker |
| Missingness / factor start | 全库枚举、逐年/era 可用性、条件覆盖与全期覆盖都报告 | 不把晚出现因子强制当长历史稳定，也不因晚开始自动删除 |
| Backend metric mismatch | Rank IC 严格 parity，alpha/beta/long-short 按原生定义展示 | Phase 1 发现主指标方向/样本错误阻止 full |
| jqfactor partial-pass | 修正数据/index compatibility，原始错误可追溯 | 必需候选 metric 失败是 blocker，附加 metric 可标 unavailable |
| 重叠标签与 multiple testing | 一套正式 hypothesis family；gap-aware bootstrap；报告 BY、MC 分辨率/片段覆盖 | Phase 0/1 synthetic 校验；不把三 evaluator 当独立显著性 |
| Rule mining / 人工近期记忆 | 一次冻结，原始 evidence 先封存；不按候选数或近期收益调阈值 | Phase 4 rationale 与输入来源审计；人的既有知识污染无法通过代码完全消除 |
| Regime concentrated 的定义 | 先保存贡献/符号连续量，Phase 4 一次定标注；不逐 Era AND | 不为得到更多 stable 因子改 era 或添加权重 |
| Correlation / duplicate | canonical/proxy 对照保留；exact values 验证后缓存复用，cluster 仅作信息组 | 本轮全 exposure clustering 过贵可后移，不能阻断主 Board |
| 计算与依赖版本 | 先实测 1/2 worker；绑定原生源码和依赖；缓存可恢复 | 主要 IC 不可复现阻止 full；不借用模型 8T 认证 |

MVP 的硬停止条件是数据/标签/样本/PIT 错误、主 backend parity 不通过、locked evidence 进入选择、无法追溯的关键输出。理论上更完整但不改变候选判断的增强默认延期。

## H. 附件 23 项审计问题对照

| # | 结论与文内位置 |
| --- | --- |
| 1–2 | 774 definitions / 765 usable / 9 blocked，已复核 identity 和 lineage；A2 |
| 3–4 | V4 原生调用→summary→source board→judgement；三个 adapter 都在 external/adapters.py；A3 |
| 5 | 共用上游收益，但非新 canonical loader，且多 label dropna 造成样本差异；A3、B2 |
| 6–7 | 旧 judgement 对新长历史无 selection authority，旧池/冻结 Strategy 的历史地位保留；A4 |
| 8 | 原生 IC/quantile/return/turnover/alpha-beta/context 已有，Qlib wrapper 不完整；A4 |
| 9 | 切片、rolling、Phase 0 period 汇总已有，本轮 765×3 annual/era 集成尚无；A4 |
| 10 | BH/BY 与 bootstrap 可复用，但旧 669 split runner/family 不可直接套；B5 |
| 11 | taxonomy 覆盖 774、economic_map 覆盖全部 765 usable；机制/文献质量并不等强；A4 |
| 12 | 历史等价映射与 clustering 工具完成，本轮数值重复/聚类未运行；A4、C |
| 13 | raw/tradable_only 混用确实存在，V4 loader 还强制 tradable；A3、A5 |
| 14–15 | 可统一读取 canonical practical raw；未证实可可靠重建全期 tradability，建议 raw primary + 可靠时期 secondary；B2 |
| 16–17 | close[t+21]/close[t+1]−1 与 close[t+11]/close[t+1]−1；存在 row-shift 风险、overlap 和末端成熟边界；B1、B5 |
| 18 | Fast 8T 是模型路径，不能直接认证本轮；C、F2 |
| 19–20 | 主要瓶颈预计为 IO、逐日 rank/groupby、quantile/turnover、长表内存；共享 keys/labels/masks/quantile/input cache；F2 |
| 21 | 旧 source promotion、judgement、rolling/FDR/cluster selected、Phase 0 portability 均仅 provenance；A4–A5、C |
| 22 | 读取过滤、exit cutoff、schema allowlist、隔离 artifacts、mutation tests；B1、E |
| 23 | 复用 raw namespaces、metric index/status，再加 period/universe/rule/identity 字段，不能直接套 source-specific board；C、D Phase 3 |

验收成功看是否得到可信、完整、可追溯且与 locked period 隔离的 Evidence/Candidate Board，不以筛出多少“优秀因子”为标准。
