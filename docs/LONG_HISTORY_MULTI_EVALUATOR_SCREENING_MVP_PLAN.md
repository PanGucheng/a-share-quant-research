# 长历史多体系因子重新筛选：开发计划与仓库审计

状态：**IMPLEMENTING / 用户已于 2026-09-07 授权按计划实施**。Primary MVP 尚未完成。

当前已完成受限读取、精确日历标签、765 因子质量审计、24 因子跨时期及 6 因子全历史原生 smoke；正式全量编排与 Board 尚未完成。实施记录见 [初始实施报告](../reports/long_history_multi_evaluator_screening_v1/IMPLEMENTATION_PROGRESS.md)。

本计划依据用户提供的《长历史多体系因子重新筛选：仓库审计与开发计划制定》及后续修订意见，结合实际仓库制定。附件作为需求材料处理；后续用户明确要求按计划开始实施，现授权推进至 primary V0 人工审阅停止点。近期诊断、组合设计及模型训练仍不在本轮范围。

建议先完成 **2010–2023、765 因子、三套评价器共用输入、仅以 20D 为筛选 horizon 的 Primary Screening MVP**：先完成 parity，再取得 backend-native evidence、一次性冻结候选规则，交付 Evidence Board V0 / Candidate Board V0 并供人工审阅。10D 与非必要诊断单列为 Phase 2B，不阻止首轮交付。复用成熟评价函数，不扩因子池、不设计人工加权总分、不自动选 Top 50。

## A. Current-State Audit

### A1. 审计基线与证据强度

- 仓库：`qlib_baseline`；本地分支 `main`。
- 初版代码审计基线：`972c6d1c35b53012a163fed4ab66ce48ec94dd50`，提交日期 2026-09-03。
- 本次修订基线：`25fe6f8fb0cc04719fe507295a04b1bbab912c28`；通过 `git ls-remote origin refs/heads/main` 确认远端 `main` 与本地一致，修订前工作区干净。该提交只增加初版计划和索引，相关研究实现没有改变。
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
| 最近区间是否未见 | [Phase 0 报告](../reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md) 已报告 2021–2026；旧路线 Phase 2 也包括 2023–2026 | 2024+ 定义为 Held-aside Recent Diagnostic，无 untouched/prospective confirmation authority |
| 目标是否直接 Core | 原路线还包括四 pillar/grade/Pareto、Core team、停止规则 | 本 MVP 收缩为 evidence → candidate → 人工审阅；Core/组合/模型移后 |
| Fast 8T 是否直接覆盖 | 已认证的 8T 是 LightGBM/Fast/Full 模型执行路径 | 复用缓存/确定性经验，不能宣称三个 Python evaluator 已获 8T exact-parity 认证 |

本计划的 Phase 0–4 是 **MVP 自己的工作包编号**，不表示重新打开原路线已关闭的 Phase 0。它是原 Long-History Robust Core 路线的一项拟议收缩执行方案，不是第二条已授权主线。原路线的 feature quality 尚未开始，economic/redundancy、Core team、stopping-rule 工作也没有因本次修订而完成；其中非必要全量诊断与 Core/组合工作在本 MVP 中后移。2026-09-07 已获实施指令，当前路线导航现已同步为 IMPLEMENTING；本节其余内容保留修订时的范围说明。

## B. Proposed Research Contract

### B1. 时间、标签与近期诊断隔离边界

| 合同项 | 建议冻结值 |
| --- | --- |
| Screening/development 数据区间 | 2010-01-29–2023-12-29；本地日历共 3,382 个交易日 |
| Held-aside Recent Diagnostic 区间 | 2024-01-01–2026-06-09；首个实际交易日 2024-01-02；本轮不使用 |
| Primary label | `label_20d_t1 = close[t+21] / close[t+1] - 1` |
| Auxiliary label | `label_10d_t1 = close[t+11] / close[t+1] - 1`，只作稳健性标注 |
| 本轮价格读取上限 | 2023-12-29；两个标签都要求 entry/exit 实际日期不越界 |
| 20D 最后可成熟信号 | **2023-11-30**，最多 3,361 个信号交易日，个别股票还可能缺价格 |
| 10D 最后可成熟信号 | **2023-12-14**，最多 3,371 个信号交易日 |
| 后续近期诊断的成熟上限 | 若以 2026-06-09 为价格截止，20D/10D 分别到 2026-05-11 / 2026-05-25；本轮不计算 |

上表日期来自本地 provider 的 `calendars/day.txt`，不是按工作日近似。`close` 使用同一 provider 的 `$close` 权威口径，entry 是 T+1 收盘而非 T+1 开盘；在 Phase 0 绑定 price source/hash、复权与单位合同。这里的标签用于预测评价，不代表已模拟可成交交易。

2024–2026 的正式名称为 **Held-aside Recent Diagnostic（本轮留置的近期诊断期）**，其隔离仅限当前 protocol。库存资格和既有项目研究已使用过后期信息，它不提供真正 prospective、untouched 或强意义的 confirmation authority。后续仅在规则冻结且另行安排诊断后查看，用于描述最近阶段表现；不得参与 threshold 制定、candidate rule 调整、本轮人工组合设计，也不得看完诊断后回改 2010–2023 selection logic。本轮 STOP POINT 位于访问该段数据之前；改名不放松代码层面的隔离。

复用 [labels.py](../research_validation/labels.py) 的 `build_label_date_map` / `build_exact_calendar_label`，在 canonical date/instrument keys 上，以精确交易日查 entry/exit close，不按物理记录顺序移位，不填充缺失价格，不对 labels 中性化或标准化。已有 labels 若满足同一 source、日期、公式、key hash 才可复用；旧 `full_research_labels_v2` 的 2021+ 范围不能直接覆盖本轮。

年度和 Era 按 **signal date** 归组：2014 年末的持有区间可以落入 2015 年，只要 exit 不超过全局 2023-12-29。它们是有重叠的描述性历史切片，不是假设相互独立的 train/test；每段记录 actual signal start/end 和最大 exit_date。不得将最后 21 个信号日的未成熟值填成零，也不得为了保留 2023 年末信号而偷偷读取 2024 年价格。

### B2. Primary / secondary universe

建议 primary 使用全历史一致的 **canonical practical raw universe**：以 canonical keys、dated lifecycle 和 market presence 为权威，进行统一有限值和 schema 校验，不追加分时期的 tradable_only 或固定当今股票列表。

这里的 raw 仍受 canonical 原始样本合同约束，不表示所有历史 A 股的无偏完整样本。已有 assembly 对 practical historical universe 给出通过结论；但当前证据不足以证明全历史 ST、涨跌停、停牌、流动性 metadata 能可靠重建。故无需为了统一过滤重新开启 Historical Data Engineering；只有具体 keys/PIT correctness bug 才作为 blocker 修复。

Secondary 在 **2010–2023 内实际可靠的时期** 检查 tradability、size/liquidity/microcap 暴露。2021–2023 是已有配置入口，仍需检查字段覆盖、日期和信息可得时点，不能默认合格。metadata 不足写 `unavailable`，不得合成伪 ST/limit 数据，也不得借用 2024+ 样本。primary/secondary 分开输出 universe_id、有效日期和样本量，不拼接成一条“稳定性”序列。

按 `factor × label` 建立共同 IC 样本：canonical membership ∩ finite factor ∩ finite matured label ∩ 同一最小横截面规则。primary 20D 不因 auxiliary 缺失而删行，不取所有 765 因子的完整案例交集。建议沿用 V4 的 50 个样本/日作为待 smoke 验证的计算可定义性下限，明确它不是 alpha threshold。

Quantile 使用独立明确的有效分桶 mask，低值为 Q1、高值为 Q5；保留 ties/不足五桶的实际状态，不因不能分桶就自动删除原本可计算 IC 的日期。IC mask、quantile mask 各有 hash，三 backend 在对应指标上使用同一份样本。

### B3. Full / annual / signal-date era evidence

- Full：整个 development 的成熟标签样本。
- Annual：2010–2023，14 个年度，包含有限样本量、日 IC 分布和符号序列。
- Signal-date eras：A=2010–2014、B=2015–2017、C=2018–2020、D=2021–2023，共四段；采用附件建议并在结果之前冻结，不沿用旧 Phase 0 的不同边界做数值直比。

字段统一使用 `signal_era`，另存 `signal_era_start` / `signal_era_end`、实际信号范围与 `max_label_exit_date`。`period_type` 区分 `full` / `annual` / `signal_era`，full/annual 行的 `signal_era` 为空。Era 只按 signal date 归属，例如 2014-12 的信号仍属于 Era A，即使持有收益延伸至 2015；不称为 realized-return era 或 `market_era`，也不为此改变现有 signal-date 计算逻辑。

三层证据均保留 backend/label/universe 维度，段缺失显示 unavailable。记录 mean/median IC、非年化 ICIR、明确约定的年化版本、valid dates、sign ratio、spread 等。Full mean 由原始有效日序列算，不能平均年度 ICIR 或无权平均各年 mean 代替。

各 Era 不做硬 AND gate。先展示 directional annual/era sequence、worst era、leave-one-era-out mean、各 Era 对全期总 IC 的贡献等描述量，候选规则阶段再一次性定义 `direction_instability`、`regime_concentrated` 等标注条件。不给不同时期额外权重，不搜索 era 边界，不新增 rolling/window 参数搜索。

### B4. Evaluator 的角色与 agreement

保留三个原生 namespace 的独立原始输出，不用一个统一计算结果伪装成三个 backend。原始值方向始终保留；未来候选展示方向要单独存 `analysis_direction`、`direction_origin`、`direction_freeze_id`。

**Layer A — Shared Parity Layer：只验证输入与实现 correctness。** 检查 canonical factor values、signal dates、instruments、sample masks、label 定义、observation count、missing handling、direction convention 和逐日 Rank IC sign/magnitude。同样本下 Alphalens/jqfactor 的默认 IC 是 Spearman，应与 Qlib Rank IC 对齐，而非 Qlib Pearson IC。出现 +0.040/+0.039/−0.041 时，首先调查样本/adapter/方向 bug，不能称为筛选意见分歧。共同指标超过工程容差的 magnitude 差异同样必须解释。

**Layer B — Backend-Native Screening Layer：在 parity 通过后，依据各 backend 的原生主要证据形成候选状态。** Shared Rank IC 可以作为共同基础指标，但不能把同一 Rank IC threshold 重复三次当作三体系候选规则。结合实际实现，拟冻结以下最小证据范围：

| Backend | Phase 2A 最小原生证据及候选观察角度 | Phase 2B 非必要增强 |
| --- | --- | --- |
| Alphalens | 原生日 IC、`mean_return_by_quantile(by_date=True, demeaned=False)` 的分桶收益；从原生分桶收益作透明 Q5−Q1/monotonicity 汇总，考察强度与横截面分层形态 | alpha diagnostics、完整 turnover/autocorrelation、多 lag 扩展 |
| jqfactor | 原生日 IC、ICIR/年度汇总、`factor_returns`，考察收益加权信号与时间稳定性；quantile evidence 可复用现有原生入口 | alpha/beta、完整 turnover 与其他辅助诊断 |
| Qlib | `calc_ic` 的 Pearson/Rank IC、ICIR/Rank ICIR，以及 `calc_long_short_return`，考察预测相关性与原生 long-short signal | 其他已可靠可复用的 signal diagnostics；不引入模型或组合回测 |

这张表是 **实现前待 smoke 核验的最小 profile**，不是新指标公式授权。ICIR、年度统计、spread/monotonicity 的派生定义和所用原生序列须写入 `metric_definitions.json`；不能把项目汇总误标为上游原生函数。Phase 0 定义拟用指标角色，Phase 1 根据接口正确性/成本冻结每 backend 的 `required_primary_metrics` 与 `optional_metrics`，Phase 2A 开始后不再看结果挑指标。jqfactor `factor_returns` 的历史 index 问题若仍存在，应做最小兼容修复；若无法可靠提供，则在 full 前记录降级后的 quantile/年度证据 profile 与重叠局限，不能自动复制 Rank IC-only 规则冒充 native screening，也不能静默把运行失败算合格。

原生视角仍可能高度相似，尤其 Alphalens 与 jqfactor 有大量共同统计定义。不得为了制造 2/3 而更换数据样本、direction 或人为设置相冲突阈值；如可可靠复用的 native 证据不足以区分视角，应如实标 `native_profile_limited`，不夸大 agreement 的价值。无需机械实现意见中列出的全部指标；alpha/beta 与非必要交易性诊断不成为 primary Board 的默认前提。

候选规则在首次 primary 全量经验分布后一次性冻结：每 backend 的 rule 必须实际引用其 primary native evidence，至少一个非 shared Rank IC 条件参与该 backend 的候选判定，其余证据可作 review/警示；不得仅在表里附加指标而筛选仍完全等同。各 backend 使用同一已记录的 analysis_direction，不能为提高各自 pass 率单独翻转方向。full/annual/signal-era、FDR 与来源可见，signal eras 不做机械 AND gate，不做人工加权总分。

`parity_status` 与 `alphalens_candidate_status` / `jqfactor_candidate_status` / `qlib_candidate_status` 分字段存储。规则未冻结时候选字段为 `not_evaluated`；冻结后每 backend 给出 pass/fail/unavailable 及 metric-level reasons，再构成 agreement。仅三个 backend 均可判定时输出 3/3、2/3、1/3、0/3；有 unavailable 时显示 `incomplete`、`pass_count` 和 `backend_available_count`，不能把失败解释为 0/3 无 alpha。Parity 失败则阻止正式候选提取，不能把它混进 native disagreement。

同定义指标做严格 parity；demeaning、权重、年化、分桶和 long-short 缩放不同的指标保留原生定义后解释。不能把 20D overlapping spread 当每日可复利策略收益，也不能把 risk-on-IC 的回撤写为交易回撤。Agreement 是相关评价框架的候选意见汇总，不是三份统计独立证据，更不代表 `3/3 = final factor`。

### B5. Multiple testing 与候选规则冻结

Phase 0 冻结统计程序、检验 family、主 label、原始方向/双侧检验和 seed，Phase 1 冻结 B4 的 backend primary metric profiles；Phase 4 作为 Phase 2A 的候选收尾工作包，在首次 20D 全量 development 分布出来后，记录一次有理由的 candidate threshold 决策。两者区分开：不能到看到结果后再挑检验方法、主 horizon、指标清单或检验对象。

复用 [bootstrap.py](../research_validation/bootstrap.py) 的 gap-aware moving-block mean test 和 [multiple_testing.py](../research_validation/multiple_testing.py) 的 BH/BY。建议起始参数为 primary 20D 的 block_length=20、bootstrap_samples=1000（沿用已存在参数，仅是实施建议）；在正式 full 前用 synthetic/null smoke 验证适用性和 p 值分辨率。每日 IC 先 reindex 到完整允许交易日，保留 NaN gap，否则 gap-aware 也会错误跨缺口抽样。长自相关、短片段排除比例和 bootstrap Monte Carlo 分辨率明确披露，不把旧 block_length 视为已在新历史获证。

Primary family 是本次冻结的 765 因子库存中所有可检验 20D/full/raw 假设，测试前列清单，数量由数据可定义性决定；不得先按高 IC 或候选 backend agreement 筛完才做 FDR。缺乏可检验数据的因子留行说明，必要时以保守 p=1 纳入 planned-family 校正视图。由 parity 通过的 Qlib-native Rank IC 序列承担一套正式检验，其他 backend 是实现核对；不把同一假设乘三提高证据。10D、annual、era 默认描述性，不作为另一次挑优的显著性通道。若另外报告其检验，必须分开登记 family 和探索性地位。

一次性冻结的 `candidate_rules.yaml` 应写明来源、方向政策、quality、三 backend 条件、FDR 的使用方式、缺失处理及标注规则，并绑定 evidence/config/code hash。不得按目标候选数反复松紧调节；规则变化保留旧版本且重新声明为 development 探索，不能访问近期诊断期。没有经济方向先验的因子可以用 development 全期方向形成候选描述，但必须标记 data-derived，不能伪装成事前经济预测。Primary q 值只对应登记的 Rank IC 假设，不自动为 native return/monotonicity 条件或最终候选组合提供额外 FDR 保证。

## C. Reuse Map

| 分类 | 模块/产物 | 具体用法及限制 |
| --- | --- | --- |
| 直接复用 | [canonical_dataset.py](../research_validation/canonical_dataset.py) | identity、effective partition 读取；外层先收窄 development dates，禁止读取后才裁掉留置期数值 |
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

下面为已授权的实施工作包；阶段是否完成以实际验收和实施报告为准。

**Primary 交付顺序：Phase 0 → Phase 1 → Phase 2A 主计算 → Phase 3 Evidence Board V0 → Phase 4 规则冻结/Candidate Board V0 → STOP 人工审阅。** 为保留原计划结构，Phase 3/4 继续作为 Board 与规则的工作包名称，但它们属于 Phase 2A 的交付收尾，不是等待 Phase 2B 后才开始的新阶段。只有主计算、Board 和候选收尾均完成，才将 `primary_mvp_status=complete`；不得仅有 metrics 就宣布 2A 里程碑完成。

Phase 2B 在 primary V0 可审阅后独立安排；可以停在 V0 先获得反馈。Phase 2B 缺失或失败不使完整的 20D primary V0 变成 incomplete，但必须显示 `enrichment_status=not_started/partial/complete`。两套状态独立，10D 不能成为第一次 Candidate Board 的 blocker。

建议运行目录为 `outputs/long_history_multi_evaluator_screening_v1/<run_id>/`，其中按 `phase0`、`smoke`、`primary/evidence`、`primary/candidate`、`enrichment` 分目录；缓存位于 `tmp/long_history_multi_evaluator_screening_v1/`。人工报告与小型汇总进入 `reports/long_history_multi_evaluator_screening_v1/`，冻结规则对象按既有 content-addressed 方式保存在 `artifacts/`。运行数据默认不进 Git，不覆盖任何旧 `current/` 或 Phase 0 输出；遵守 [输出政策](OUTPUT_POLICY.md)。

### Phase 0 — Research contract / semantics audit

**依赖：** 本计划作为后续实施基线；不重做原路线已完成 Phase 0。

工作：绑定 commit/data identity、765 清单及 9 blocked、原生源码版本；建立只有 development 的读取路径；导出 label date map；确认 practical raw keys；仅做 feature-only profile；冻结三层时期、检验方法、输入 mask、metric definitions 和资源上限。明确 `phase2a_required` 与 `phase2b_optional` 任务清单，不默认遍历 V4 的全部 steps。抽取少量 canonical 行做精确日历标签核对，检查分区交接、fundamental availability 和 factor 起始缺失。

拟新增路径：`configs/long_history_multi_evaluator_screening_v1.yaml`、`scripts/run_long_history_multi_evaluator_screening_v1.py`、小型编排模块。这些路径已建立；当前 CLI 支持 metadata preflight、最小和跨时期短窗 smoke，尚不支持 full/candidate 执行。

产物：`resolved_config.json`、`input_identity.json`、`factor_inventory.csv`、`feature_quality.csv`、`label_date_map.parquet`、`universe_contract.json`、`metric_definitions.json`、`access_audit.csv`、`job_inventory.csv`。

验收/停止：身份、重复键、PIT 和时间越界问题必须修复；确认无 2024+ values/returns/outcomes 可进入 evaluator。某个因子局部缺失记录状态；整库不可读或价格口径不清则停止。不能因旧 90% coverage 就提前淘汰大批长历史因子。

### Phase 1 — Evaluator parity smoke

**依赖：** Phase 0 correctness 合同通过。

先用 synthetic fixtures 验证正/负相关、ties、常量、NaN/inf、股票缺交易日、标签不同成熟日，再按 source/family/lineage 预选 **24 个**真实代表因子，固定清单后才读其 alpha。

建议配额：basic 3、Alpha158 4、Alpha360 3、TA 4、Alpha101 4、mature_public 6。覆盖 momentum、reversal、value、quality、volatility、liquidity、size、fundamental；Alpha101 至少包含已修正项与 legacy/canonical 对照，TA 包含 KAMA，fundamental 包含 PIT 财报因子。24 个具体名字由 lineage 与 family 交集确定，不按旧/新好成绩挑选；无法覆盖的类别记录原因。

Primary 两级 smoke：先 6 因子×20D×3 backend×60 个交易日用于接口与资源探测；再 24 因子跨四个 signal eras 各一段预先固定的 60 个交易日，并将其中 6 因子跑完整 development 检查长期累计行为。既检查 Layer A 的逐日 Rank IC parity，也验证 B4 的 Layer B 必需原生函数及派生汇总。短窗结束允许用 development 内 label tail；不访问近期诊断期。保留年度/signal-era 汇总的 synthetic oracle。

10D 的共用标签/格式合同先用 synthetic fixture 验证；真实 10D smoke 留作 Phase 2B 的开始条件，或在低成本时顺带完成，不阻塞 20D 的通过状态。若发现的是共同标签/adapter 代码的 correctness 问题且会影响 20D，则仍需先修复；仅 10D 特有的缺失或附加函数失败不应无限推迟 primary。

逐日核对 row count、key hash、value/label hash、missing reasons、IC sign/magnitude、quantile direction、metric availability。共同定义 Rank IC 建议 `atol=1e-10, rtol=1e-8`；这是工程容差，smoke 前冻结，数值差超过容差需定位原因，不能看完因子结果再放宽。浮点零附近按容差处理符号，不制造假冲突。

产物：`smoke_factor_inventory.csv`、各 backend 原始输出、`adapter_parity.csv`、`metric_parity.csv`、`failure_reasons.csv`、`runtime_timing.csv`、`resource_estimate.json`。

验收/停止：任何共同指标符号反转、label/key mismatch、静默丢样本、20D 主 IC backend 不可用或冻结 primary profile 的必需原生函数失败，都阻止 primary full。附加 alpha/beta 等 Phase 2B 函数失败单列 optional status；不得将缺失指标算作 pass，也不得在 full 后事后删去失败的 required metric。修复共享函数时回归已有 adapter/V4 合同，不修改 frozen evidence。

### Phase 2A — Primary Screening MVP

**依赖：** Phase 1 parity 通过，并用实测数据更新计算计划。

全量枚举 765 research-usable，**仅以 20D T+1 为 primary screening horizon**；数据不可定义者保留 failure/quality 行，不能静默漏因子。canonical factor/20D labels/universe 预计算一次，共享到三个原生 evaluator；依照分区与因子块逐批落盘，可恢复到失败批次。完成 B4 所列且已通过 smoke 的最小 native profiles、full/annual/四个 signal eras 及 primary multiple-testing/FDR。

保留各 backend 的每日 IC 及其所需的原生 quantile/factor-return/long-short 序列，再产生 full/annual/signal-era 汇总。均值等从日序列汇总，标准误等不能平均已有汇总值，应对切片复用相应函数。turnover/autocorrelation、alpha/beta 及 secondary tradability 默认交 Phase 2B，不能因为 V4 已有 steps 就全部列为 2A 必需。若成本接近零可附带产出，但不能改变验收依赖。

执行一套本轮 primary bootstrap/FDR，先保存全体 development empirical distributions，再进入 Phase 3/4 的 Board 与一次性候选规则收尾。期间不据结果删改运行清单，不生成巨型全股票×765 长表。首次交付的 **Factor Evidence Table / Evidence Board V0 + Candidate Board V0** 必须已可人工审阅，无需等待 10D、额外 alpha/beta 或 tradability。

计算产物：`raw/<backend>/`、`daily_metrics/`、`factor_period_metrics.parquet`、`data_quality_by_period.csv`、`primary_metric_distributions.csv`、`multiple_testing.csv`、`test_family_inventory.csv`、`batch_status.csv`、`run_manifest.json`。里程碑产物还包括 Phase 3/4 定义的两张 V0 Board、三 backend candidate lists、冻结规则与人工审阅报告；其 `evidence_scope=primary_20d`。

验收/停止：全部 primary job 必须有 success/unavailable/failed 状态；工程性 required failures 未解决时 primary 为 incomplete，数据本身不可定义则明确保留不可判断状态。禁止静默 fallback 到旧矩阵/label/阈值。缓存损坏拒绝使用，重跑受影响批次；重大语义修复使受影响证据失效并重跑。10D、非必要交易性证据不足只影响 enrichment status，不影响已完整的 primary V0；V0 是 alpha 候选证据，不声称已完成可交易性验证。

### Phase 2B — Auxiliary Robustness Enrichment

**依赖：** Phase 2A 的 V0 已可审阅；本工作包可后续安排，不是首次交付的前置条件。

用同一 development-only 合同完成真实 10D smoke 后，补全 765 因子的 10D 辅助原生证据、方向一致性与 signal-era/annual 汇总。按实际价值和成本补充 20D/10D 较昂贵 alpha/beta、更完整 turnover/autocorrelation，以及仅在可靠 development 时期可用的 size/liquidity/microcap/tradability diagnostics。跨时间块保留 lagged rank/集合状态，不能年度重置后伪造 turnover 跳变。细分 optional job 清单和不可用原因，不要求所有可能的增强都完成。

产物：`auxiliary_period_metrics.parquet`、`robustness_annotations.csv`、`enrichment_status.csv` 和带新增注释的 Evidence Board 版本。绑定 primary V0 的 evidence/rule hash；**不因 10D 或后补诊断重算 primary backend pass、候选方向、候选集合或 threshold**，只增加 warnings/review annotations。若发现真实 correctness bug，则按显式勘误流程使受影响 primary 结果失效，不能借“修 bug”按绩效调规则。

验收：10D 语义/样本/日历/方向 parity、enrichment 缓存和复现检查通过；primary V0 及 candidate hash 保持不变。Phase 2B 也不访问 2024–2026，不启动组合或模型工作。昂贵 optional diagnostics 未完成时标 partial，允许报告已有有用信息。

### Phase 3 — Evidence Board construction

**依赖：** Phase 2A primary 计算与 FDR 完整性检查通过；这是 2A 的 evidence 收尾工作包，不依赖 2B。可随 primary 批次预览，最终 V0 统一封存。

构建长表和一因子一行的宽版索引，附完整可追溯 raw paths。V0 加入年度符号序列、signal-era 贡献、availability、经济 family、重复关系及已低成本可靠获得的 size/liquidity/microcap 标注；其余 secondary 列标 `not_run/unavailable`。exact duplicate 可复用完全相同输入的计算，但仍保留所有因子行及别名映射；canonical/legacy 语义不同不能仅因名字近似合并。

拟定最小 schema：

| 产物 | 主键及核心字段 |
| --- | --- |
| `factor_inventory.csv` | canonical_factor_id/factor；source、family、canonical/legacy mapping、research_usable、block_reason、definition/lineage hash；canonical_factor_id 绑定 dataset id 与 factor name |
| `factor_period_metrics.parquet` | run_id/factor/backend/label/universe_id/period_id/metric；period_type、signal_era、signal_era_start/end、actual_signal_start/end、max_label_exit_date、value、unit、direction_mode、valid dates/samples、raw_path、status |
| `factor_evidence_board.csv`（V0） | canonical_factor_id/factor；coverage/missing/finite、availability window、source/family、三 backend native full 指标、annual/signal_era 索引、primary FDR、direction stability、regime concentration、parity_status、native disagreement、warnings、evidence_scope |
| `robustness_annotations.csv` | factor/annotation/universe/period；signal_era、direction instability、regime concentration、size/liquidity/microcap、turnover、duplication、证据路径、annotation_status；未运行不得默认为无风险 |
| `candidate_board.csv`（V0） | factor/rule_version；alphalens_candidate_status、jqfactor_candidate_status、qlib_candidate_status、agreement、pass_count、backend_available_count、full_period_strength、annual_stability、worst_signal_era、regime_concentration、primary_fdr、economic_family/source、analysis_direction/source、warnings/review reasons |
| `run_manifest.json` | primary_mvp_status、enrichment_status、held_aside_recent_diagnostic_accessed=false、evidence/rule/code identity；完整 primary 不取决于 enrichment |
| `pool_exports.json` | pool_id/rule_version；ordered factor list、definition hash、selection period、evidence references；本阶段可只保存预留结构 |

所有宽表均从原始证据生成，缺失与失败不同于数值 0。Board 必须容纳无完整 14 年历史的因子，并展示其有限证据，不把 full-schema frontier 当首次可用值日期。

验收/停止：765 行一一对应，9 blocked 在 inventory 附录可查；关键指标可从 raw 重算，signal-date era 不冒充 realized-return era，source 与 backend、parity 与 candidate status 分离。Phase 4 前 candidate 字段只能是 not_evaluated；native disagreement 在原生规则冻结后填充，不能与 parity failure 混淆。产物为 CSV/Parquet/Markdown，先不开发 Web UI。

### Phase 4 — Candidate-rule freeze / candidate extraction

**依赖：** Phase 3 primary Evidence Board V0 和首次全量 20D 经验分布；这是 2A 的候选收尾工作包，不依赖 2B。

严格执行顺序：parity 通过 → 全量 20D primary native evaluation/FDR → 查看全体 factors empirical distributions → 结合已冻结 native profiles、full strength、annual stability、signal-era concentration、FDR 和历史 rule provenance 一次制定并冻结 candidate rules → 分别生成 Alphalens/jqfactor/Qlib candidate lists → agreement / Candidate Board V0 → STOP 人工审阅。Phase 2B 不插在这条交付链中。

先保存不含最终 pass 的 evidence snapshot；不边看哪些具体因子 pass 边反复调整 threshold。每个 backend 规则记录所用原生指标、派生定义、阈值理由和 reason codes，遵守 B4 的非单一 Rank IC 要求；共享 quality/FDR 不计作三份独立统计确认。候选数量是结果，不能设成调参目标；不同 source 不享有 Alpha158 旧池特权。允许 stable/conditional/review 等有原因的状态，不把 signal eras 全通过作为默认条件。

冻结规则及方向后一次提取 Candidate Board，并保留 old selected/rejected 作为旁证。旧方向若来自包含留置期年份的历史判断，仅作 legacy 字段，不直接决定新版方向。对外输出候选表、未进入候选的原因和全部 evidence，而非“最终最佳因子池”。

产物：`candidate_rules.yaml`、`candidate_rule_rationale.md`、`candidate_rule_freeze.json`、`alphalens_candidates.csv`、`jqfactor_candidates.csv`、`qlib_candidates.csv`、`candidate_board.csv`（V0）、`candidate_factors.csv`、`review_queue.csv`、`REPORT.md`。3/3 仅为候选意见一致，任何 list 都不是最终因子或投资组合。

验收：相同 evidence/rules 重跑候选集合与顺序一致；仅改留置期 synthetic 数据不影响任何本轮输出；没有自动 horizon 切换或按照候选个数调阈值。Phase 4 明确保存 `held_aside_recent_diagnostic_accessed=false`。

### STOP POINT — 人工审阅

**首个 STOP POINT 是 Phase 2A primary V0 可供人工审阅，不等待 Phase 2B。** 交付完整的 20D Factor Evidence Table / Evidence Board V0、Candidate Board V0、native agreement / shared parity、年度/signal-era 稳定性、primary FDR、失败/限制、冻结规则和复现入口；明确列出 auxiliary 未运行项。后续若安排 2B，可补充注释后再次交付，但不推翻 primary 冻结结果。

本轮不执行 2024–2026 近期诊断、最终经济组合设计/优化、Core team、LightGBM 重训、rolling redesign、Strategy V2。V0 人工审阅只使用 development 证据；后续人工组合研究也不得借用近期诊断期反向挑选本轮因子或组合。

后续接口应支持 Old Pool、Broad Quality-qualified Pool、Consensus Pool 和少量人工 Economic Combos。Old Pool 保留冻结 52 因子顺序；新数据上的实验副本另建身份，不改 Strategy V1。下一阶段再统一模型/训练日期/成本口径比较 Rank IC、ICIR、yearly/worst period、P01/spread、turnover、cost-adjusted return 和 drawdown；本轮不生成伪交易绩效承诺。

## E. Validation Plan

| 阶段 | Correctness / data contract | Parity | Leakage | Determinism / artifact |
| --- | --- | --- | --- | --- |
| 0 | identity、effective dates、unique keys、finite、dated universe；精确 entry/exit hand-check | exact-calendar helper 与无缺口参考公式一致，有缺口 fixture 能揭示 row-shift 差异 | price/factor read filter 最大 2023-12-29；exit 超界拒绝；PIT event availability | sorted inventory/config hash、只读 parent、独立 output root |
| 1 | NaN/inf/ties/constants、min-count、quantile、单 horizon mask、required/optional profile | 三 backend 同 key/value/label；每日 Rank IC 容差；native primary 函数验证独立记录 | mock/spy reader 拒绝留置期请求；20D 不受 10D missing 牵连 | 顺序两次与小并行一次；冻结 seed、版本、排序；区别 binary hash 与逻辑内容 hash |
| 2A | 765 primary job inventory、批次不漏不重、full/annual/signal_era coverage、primary FDR | 每批共享样本 hash，全量共同 Rank IC 比较；native profile 完整，无 Rank IC-only 伪三票 | 所有 stage 只消费 development artifacts；bootstrap 无留置期 dates | cold/cache-hit、恢复重跑、不同块大小抽查一致；损坏缓存被拒绝 |
| 2B | 10D 与 optional job 单列、annotation missing≠通过、lag 状态跨块正确 | 真实 10D smoke→辅助评价；原生可比指标 parity | 不使用 2024+；辅助结果不能进入 primary rule evaluator | primary candidate/rule hash 不变；enrichment_status 不控制 primary_mvp_status |
| 3 | raw→long→wide 可追溯、一对一 factor identity；失败≠0 | 同一 backend annual/full 重算一致；不平均 ICIR | economic map 仅读描述列；旧 outcome/coverage 不进入 selection payload | Board 行序和 reason codes 稳定；完整性计数匹配 manifest |
| 4 | rule_version/evidence identity 唯一、未测因子状态明确、FDR family 无事后删减；只有 20D 也能完成 V0 | 三套 native 规则可复算；parity/status 与候选 status 分离；unavailable 不得伪装 0/3 | 留置期 synthetic values/prices/outcomes 扰动后候选/方向/阈值不变 | 同规则同证据候选完全一致；删除全部 10D/optional 文件仍可重建相同 V0 |

重点扩展既有 [canonical tests](../tests/test_canonical_dataset.py)、[label tests](../tests/test_full_research_labels_v2.py)、[future-leakage tests](../tests/test_no_future_leakage.py)、[bootstrap tests](../tests/test_bootstrap_gap_aware.py)、[multiple-testing tests](../tests/test_multiple_testing.py)，并新增本轮 thin-runner/adapter parity 的聚焦 tests。测试目录名可在实施时按现有覆盖组织，不要求为每个字段机械造测试。

留置期防护分为：输入文件/分区日期 allowlist、读取 filters、label exit 断言、candidate schema 列 allowlist 和 synthetic mutation test。历史 metadata/manifest 可能描述全 canonical 范围，允许作为身份读取；不允许把近期诊断区间的因子值、收益、coverage、旧 outcome 或含该段的方向结论作为新规则输入。若 parquet 物理上含跨界 row group，允许必要字节校验，但有效输出行与后续计算必须受 filters 限制；记录这种存储与研究读取的区别。

计划撰写阶段只执行文档检查；现实施阶段按 [CI 政策](CI_POLICY.md) 运行比例适当的研究测试、完整仓库验证与 Qlib runtime 检查，结果见实施报告。

## F. Compute Plan

### F1. 计算集合

| 范围 | 计算量/用途 |
| --- | --- |
| 固定 inventory | 774 定义；765 planned usable；9 blocked 不进入 evaluator |
| 20D 最小真实 smoke | 6×3=18 个 factor/backend 单元，单段 60 个交易日 |
| 20D 扩展 smoke | 24×3×4=288 个 signal-era 短段单元；另 6×3=18 个完整 development 单元 |
| Phase 2A 全量核心任务 | 765×3×1=2,295 个 factor/backend/20D 单元，执行最小 primary native profiles |
| Phase 2A 时间汇总 | 1 full + 14 annual + 4 signal eras =19；最多 43,605 个 factor/backend/20D/period 单元 |
| Phase 2A 日 Rank IC | 20D 最多 3,361 日；三 backend 最多 7,713,495 行，不含 Pearson/原生收益等额外 metrics |
| Phase 2B 10D smoke | 默认复用 24 因子/四个短段及 6 因子长段的清单，先最小 18 单元；相同适配链已有明确可复用证明时可缩减真实复测，保留差异覆盖 |
| Phase 2B 10D 全量 | 另 2,295 个单元、43,605 个 period 视图、最多 7,736,445 行日 Rank IC；不属于 V0 完成条件 |
| 两个 horizon 全部完成后 | 共 4,590 个 factor/backend/horizon 单元、87,210 个 period 视图、15,449,940 行日 Rank IC；不能倒过来要求这个总量才发布 V0 |
| Primary FDR | 最多 765 个正式假设，bootstrap 1,000 次为初始建议；不乘 backend、年度或 Era 数量 |
| Phase 2B 其他增强 | alpha/beta、turnover/autocorrelation 按 backend/label/metric 另列 jobs；secondary universe 仅可靠 development 子区间，不隐含在 2A 计数中 |

43,605/87,210 是逻辑证据视图数量，**不是** 同样次数从 provider 重读全矩阵。Annual/signal-era 尽量从原生日序列汇总；需要原生非线性统计的指标仅重跑对应函数。三套候选规则和 Board 是对紧凑 evidence 的运算，不新增一轮 factor-value 评价。

### F2. 共享预计算、内存与并行

一次性共享：canonical inventory/keys、calendar、feature quality、factor slices、逐 factor/horizon masks、quantile assignments。Phase 2A 先生成 20D label cache；10D 可在确实低边际成本时一起生成，但读取器必须允许它不存在，候选逻辑不依赖它。Phase 2B 优先复用相同 source/日期/值的 factor slices 与已有 20D 日序列；horizon-dependent mask/label 不能混用。

三个 backend 各自计算主要 IC，不能共享一份 vectorized Rank IC 后复制三份。已有 vectorized/pairwise IC 与批处理可用于输入准备、加速核对或已经通过原生 parity 的执行优化；新增替代路径不是 MVP 前提，必须保留实际 backend/function provenance。模型 Fast 8T 认证不外推为 evaluator 认证。

Cache identity 至少包含 canonical id、实际 source hash、effective/read dates、label公式和价格/calendar hash、universe/mask policy、factor definition、quantile、backend code/version/参数。原始 factor cache 与 label/metric cache 分开，便于 2B 复用；primary rule 输入须列 allowlist，不能读到后补 10D。旧 provider-basic cache、旧 669 daily IC、旧 2021–2026 方向/IC cache 不能只因 factor name 相同就命中。

建议先单 worker，之后测试 2 个因子/分区 worker，每 worker 内部数值库先设 1 thread，避免外层 worker×内部 8T 过度并行。24 因子 parity/资源测量通过才考虑 4 worker；不默认沿用 LightGBM 的 8T 加速倍数。原生 evaluator Python groupby/rank、IO、GC 和 pickle 可能成为瓶颈，进程/线程选择以实测为准。

按平均 2,000–4,000 股票、3,382 日作粗略容量示例，765 列 float64 仅数值就约 39–77 GiB，尚未计索引、副本和两份标签展开；实际样本规模须从限定分区统计。故按 canonical 分区、16–32 因子作为初始块，转换长表时进一步缩到单因子/单 horizon。quantile/turnover 时间状态跨块保留；不假设年度 parquet 可以无状态独立计算全部指标。

遵循 Forward 优先级，smoke 记录 peak RSS、CPU、读写 GB、每 source 的 median/p95 耗时与缓存命中率；并行前按 `shared_RSS + workers × p95_worker_RSS` 留足系统及 Forward 内存，不仅按 CPU 核心数选 worker。

### F3. 时间估算与反馈节奏

[已完成 Phase 0](../reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md) 的 91 因子、单 20D Rank IC、2010–2026 冷计算耗时 3,147.7 秒，整个 cold run 3,223.4 秒，cache replay 75.5 秒。按因子数与交易日线性外推，本轮单套 Rank IC 大致 **6–8 小时量级**；这只是不同计算链的参考，不是三 evaluator 全指标 benchmark。

**Phase 2A** 仅包含一个 horizon、最小三 backend profiles 和 primary FDR，先作 **0.5–1.5 个机器日**的低置信度排期占位；**Phase 2B** 的 10D 全量加所选择增强另留 **0.5–2 个机器日**占位，可延后或分批交付。它们不是实测 SLA，也不能用因子数减半推断耗时必定减半；实际取决于 native step 成本、缓存复用、IO 与并行。原计划整体 1–3 日估计不再作为 V0 等待条件。

Phase 1 按最小/24 因子 smoke 分别记录时间、peak RSS 和 cold/cache；Phase 2A 估算采用 `sum(source_factor_count × source/backend/20D/required-step 实测耗时) / 实测并行效率 + I/O/bootstrap/Board 开销`。Phase 2B 另估 10D 与 optional-step 清单，扣除已验证的共享读取和序列缓存；分别给低/中/高估计，不沿用 LightGBM 加速倍数。不要为了估算提前启动 765 全量 run。

首次反馈顺序：合同与最小 smoke → 24 因子 parity/native profiles 与资源报告 → 全量 primary 20D evidence → 规则冻结与 Candidate Board V0 → 人工审阅；**10D 不在首次反馈关键路径上**。若 primary 超出预算，先消除重复 IO、移除误纳入的 optional steps，再调整执行资源；不能省掉 primary FDR、必需 native 证据或部分因子却宣布 V0 complete。2B 延迟只标 enrichment pending。

开发排期也按交付拆分：Phase 0 约 1–2 人日、Phase 1 约 2–3 人日、2A 主编排约 1–2 人日、Phase 3/4 V0 收尾约 1–2 人日，primary 共约 5–9 人日；2B 利用共用 runner 另估 1–3 人日，随选定增强量更新。均不含机器等待，主要不确定性是 adapter/native 函数兼容修复；不安排新框架或模型工程。

## G. Risks / Open Decisions

| 风险/决定 | 当前建议 | 验证阶段与升级条件 |
| --- | --- | --- |
| Practical raw ≠ 完美 PIT/tradable universe | 复用 canonical dated keys，secondary 单列；不伪造旧 ST/limit | Phase 0 发现具体非法 keys/未来 membership 才重开数据修复 |
| 最近区间污染 | Held-aside Recent Diagnostic，仅本轮隔离；披露此前 Phase 0、旧筛选及 765 qualification 已观察后期 | Phase 0/4 allowlist、exit 与 mutation tests；不参与规则/本轮人工组合，不能声称恢复 fresh OOS |
| 标签物理行 shift、边界、复权 | 复用 exact-calendar helper，冻结 price source；缺价 NaN | Phase 0/1 精确日期 fixture，price/source 不清即 blocker |
| Missingness / factor start | 全库枚举、逐年/era 可用性、条件覆盖与全期覆盖都报告 | 不把晚出现因子强制当长历史稳定，也不因晚开始自动删除 |
| Backend metric mismatch | Rank IC 严格 parity，alpha/beta/long-short 按原生定义展示 | Phase 1 发现主指标方向/样本错误阻止 full |
| jqfactor partial-pass | 修正数据/index compatibility，原始错误可追溯 | 必需候选 metric 失败是 blocker，附加 metric 可标 unavailable |
| 重叠标签与 multiple testing | 一套正式 hypothesis family；gap-aware bootstrap；报告 BY、MC 分辨率/片段覆盖 | Phase 0/1 synthetic 校验；不把三 evaluator 当独立显著性 |
| Rule mining / 人工近期记忆 | 一次冻结，原始 evidence 先封存；不按候选数或近期收益调阈值 | Phase 4 rationale 与输入来源审计；人的既有知识污染无法通过代码完全消除 |
| Regime concentrated 的定义 | 先保存贡献/符号连续量，Phase 4 一次定标注；不逐 Era AND | 不为得到更多 stable 因子改 era 或添加权重 |
| Correlation / duplicate | canonical/proxy 对照保留；exact values 验证后缓存复用，cluster 仅作信息组 | 本轮全 exposure clustering 过贵可后移，不能阻断主 Board |
| 计算与依赖版本 | 先实测 1/2 worker；绑定原生源码和依赖；缓存可恢复 | 主要 IC 不可复现阻止 full；不借用模型 8T 认证 |

Primary MVP 的硬停止条件是数据/标签/样本/PIT 错误、主 backend parity 不通过、必需 native profile 无法可靠执行、留置期 evidence 进入选择、无法追溯的关键输出。10D 或 optional enrichment 未完成不是 primary blocker。理论上更完整但不改变候选判断的增强默认延期。

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

验收成功看是否得到可信、完整、可追溯且与近期诊断期隔离的 **20D Evidence/Candidate Board V0**，不以筛出多少“优秀因子”为标准；10D 等增强用独立状态交付。

## I. 本次修订取舍与实施前待解决项

采纳意见中的主要收敛建议：明确 parity/native screening 两层、拆分 2A/2B、降低近期 evidence authority、加入 proposed 导航、显式命名 `signal_era`，并同步 schema、候选规则顺序、验收和计算集合。保留现有 2010–2023、canonical 765、20D/10D、raw primary、FDR 单 family 和不训练模型的主线。

未机械采纳全部指标作为首轮必需项，也不通过三组人为不同的 Rank IC threshold 制造分歧。现有原生函数的最小 profiles 见 B4；2A 的 Board/规则沿用 Phase 3/4 工作包完成，避免重复建立一个提前筛选器或第二轮候选冻结。

本次复核未发现相对初版的新代码变更或新近证实的数据运行故障。仍存在的实施缺口是 canonical 受限入口、精确日历标签接入、adapter 单 horizon/mask 一致性、Qlib-native wrapper 补齐，以及 jqfactor 必需函数的兼容性。进一步明确：V4 runner 当前默认执行多项 steps，若不增加最小 required/optional step 选择，单在文档拆 2A/2B 不能实际节省计算。这些是 Phase 0/1 和薄编排入口应解决的已有能力缺口，不是重新扩建研究框架的理由。以上为修订时的审计结论；后续实施与实际 smoke 结果单独记录于实施报告，不回改历史审计事实。
