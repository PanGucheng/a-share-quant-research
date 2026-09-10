# Literature Factor Representation D1

最新状态：**D1 CLOSED / REPRESENTATIONS FROZEN**，见[正式冻结](FORMAL_FREEZE.md)（`d05e7eb`）。
下文保留冻结前诊断与人工审阅记录；当前D2入口见[运行说明](../../docs/LITERATURE_D2_PRECOMPUTE_RUNBOOK.md)。

2026-09-10。用户要求先提交计划、再实施D1；计划修订已以 `b877ad3` 提交并推送。
诊断V1实现在提交 `e5228d5`；当前唯一继续审阅的配方是 **candidate_v2**。

**D1 FULL STRUCTURAL SCAN VERIFIED / HUMAN REVIEW REQUIRED / D2 NOT AUTHORIZED**。
用户已完成全量扫描，168个月、3382日期、6640610行及独立oracle已核验。
最新结论见 [全量结构审阅](FULL_STRUCTURAL_REVIEW.md)。配方仍未正式冻结。
下文第1–7节保留首次实施与canary交付记录，其中“尚未运行”描述的是当时状态；无需重复长扫描。

## 1. 交付与自然列数

| 项目 | 数量 |
|---|---:|
| 原始identities / 去重后parents | 494 / 489 |
| common raw U / 可rank的G parents | 61 / 428 |
| R(G) raw representatives | 157 |
| C(G) rank outputs | 140 |
| 其中rank singletons / multi-node outputs | 116 / 24 |
| 其中multi-family outputs | 2 |
| R = U + R(G) | **218** |
| C = U + C(G) | **201** |
| H = U + R(G) + C(G) | **358** |
| 主题 / measurement families / source horizon tokens | 12 / 115 / 99 |
| 新增严格近似替代 | 0 |

R实际依赖218个原始节点；C/H各依赖489个。结构扫描投影494列，额外5列用于复核exact aliases，
计权前去重。没有为了压缩比例调整规则。

- [494逐项inventory](candidate_v2/inventory_494.csv)：公式/units/horizon、测量轴、方向、语义状态、
  canonical lineage、dated availability、feature-only quality、0.995提案与U/R/C/H去向。
- [完整recipe/DAG](candidate_v2/recipe.json)、[R](candidate_v2/R_candidate.json)、
  [C](candidate_v2/C_candidate.json)、[H](candidate_v2/H_candidate.json)：有序列名与身份哈希。
- [计数](candidate_v2/counts.json)、[dense groups](candidate_v2/dense_groups.json)、
  [未来evaluation合同](candidate_v2/evaluation_contract.json)、[access合同](candidate_v2/access_contract.json)。
- [当前候选指针](CURRENT_CANDIDATE.json)、[packet文件哈希](candidate_v2/packet_hashes.json)。

当前recipe hash：`8b688bd098ebafd1c1da2bab32d029624f6da65f7166c59f702fbc18499cf51f`。
recipe绑定源文件、代码LF哈希、canonical identity、文献来源与正式计划；变化会拒绝续跑。
这些不是D2 pool authorization；V1保留为失败诊断证据，不供D2选择。

## 2. 语义与U审核的实际限度

462条继承V0.5.1 resolved状态，并增加测量轴/方向/角色判断；32条Alpha101仍未解决经济语义。
494条均有去向，不等于494条均完成独立专业经济解释。
所有expected-return directions均不作断言；未知收益方向不用于确定U或sign。

U逐项说明在 `u_item_review`，新hold对象不能自动进入：

| U主要限制 | 数量 | 当前处理 |
|---|---:|---|
| Alpha101经济语义未解决 | 32 | 提议原canonical身份/raw保留；不rank、不聚合、不推断sign；仍需人工认可 |
| provider stock-specific price scale未核清 | 23 | 有限raw值保留，不擅自除价格、改量纲或跨股票rank |
| recursive missingness/quality | 3 | ADX正负方向与ATR沿用canonical状态/缺失；不补值、不重启递归 |
| state/event mask | 3 | PSAR down保留状态缺失；BBHI/KCHI保留0/1，不将0视为缺失 |

ATR同时涉及价格尺度，PSAR同时涉及状态和价格尺度，逐项说明保留这些交叉限制。
构建前核查canonical research-usable、blocked state、block reason与历史/续接语义一致性；
本次未识别新的canonical correctness blocker。这是有限来源核验，不是对未知公式的全面正确性证明。
dated PIT/warmup继承canonical实现，未重建数据、重新授予数据资格。

按测量含义而非source库计权；保留PIT latest-statement与TTM、总波动与残差波动、窗口与递归参数差别。
0.995提案没有合格的新近似替代，保留unknown-pair事实，未假装完成新的全矩阵complete-linkage证明。

## 3. Dense-lag结构

只有field、current-close分母、ratio算子、normalization、availability一致且仅lag变化的节点合组。
Alpha360的287列加5个canonical Alpha158别名，经去重对应287个unique dense nodes。

| Field | Unique nodes | 非空bucket | R retained lags |
|---|---:|---:|---|
| close | 57 | 3 | 4、13、40 |
| high | 55 | 3 | 5、13、40 |
| low | 60 | 4 | 0、3、13、40 |
| open | 58 | 3 | 3、13、40 |
| vwap | 57 | 3 | 4、13、40 |

bucket固定为0、1–5、6–21、22–63，取已存在distinct lag的较低中位数。
R保留16个dense raw reps，C形成16个dense outputs，H保留两类共32个output identities。
R主动舍弃271个单点lag的raw分辨率（287→16，保留约5.57%）；C使用全部dense父节点聚合。
lag40是实际22–59离散grid中心，不声称是文献最优lookback。
Alpha158 STD、TA多参数/递归规则不套用这些单点lag buckets。

C只有两个multi-family输出：20-session range intensity与30-session up-day balance。
因此当前主要研究dense-lag压缩与rank表示，不能夸大为广泛economic-theme潜在因子模型；
不为扩大融合范围放宽语义条件。

## 4. Canary发现与一次有依据的修订

V1使用50%跨family门槛。range组合的 `amplitude_20` rolling20需20个观察，
`mature_parkinson_volatility_20`允许min_periods10。
在2010/2012采样日，V1分别有288/1526、401/1986的有效输出只依赖一个family。
证据见 [V1多family诊断](canary_v1/multifamily_daily.csv)。

唯一修订V2规则：

1. 完整dated universe内，G叶float64 average rank：`(rank - 0.5) / n - 0.5`。
2. `n_min=100`仍为待全历史确认的唯一候选；constant/all-missing/below-min输出缺失。
3. family内至少 `ceil(0.5 × frozen nodes)` 可用，按有效节点等权；不跨日期填补。
4. 跨family要求**全部frozen families可用**，各family等权，缺任意family即缺失。
5. U/R raw有限值不变，infinity按V3约定变NaN；H严格按output identity取并集。

修改依据是稳定测量轴组成，不是覆盖率、列数或模型效果；没有threshold × outcome sweep。
新增近义lag可能改变值/缺失，但固定有效family集下不改变父层名义权重；exact alias不改变值/mask/分母。

V2相同12日重验后，两个multi-family输出均无single-family有效输出，跨family有效输出L1漂移为0。
range有效输出从22640降到21276，新增1364个缺失。这项覆盖率损失明确接受，仍须完整扫描检查分布。
单family桶内节点组成仍可变化，不能将跨family漂移为0解释成所有测量组成恒定。

## 5. 验证结果与资源

[V2 canary summary](canary_v2/summary.json)：四era各自首/中/尾交易日，共12日、23544行，
覆盖2010-01-29至2023-12-29。每日使用完整dated universe，不抽股票后rank。

- 428个rank叶×12日均达到100且非常数；140个rank输出每天有限样本数均≥100。
- 3个recursive raw U在2010-01-29各仅1个有限值，在2012-07-18均全缺失；
  [6个稀疏date-factor单元](canary_v2/raw_U_sparse_days.csv)完整披露。保留已知canonical缺失限制，
  不rank、不填补；它们的raw保留理由仍须人工审阅，不能用生成代码通过掩盖覆盖质量问题。
- 无raw/生成infinity，无constant rank output；5组exact alias在每个切片值与mask一致。
- naive oracle不导入生产rank/平均函数；各臂mask相同，绝对误差最大
  `2.7755575615628914e-16`，验收 `rtol=0, atol=1e-12`。
- [逐日output诊断](canary_v2/daily_outputs.csv)、[多family诊断](canary_v2/multifamily_daily.csv)
  包含缺失损失、有效family、权重及参与数量分布。
- 采样有限cell率：R约94.30%，C约93.97%，H约94.75%；各臂分母不同，仅结构描述，不作效果排名。
- V2读取/转换/naive重放约54.84秒，最大单日输入frame约7.68MiB；不是process峰值RSS。
  全量按月装载，不能据此声称完整任务只需8MiB。

全量为168个月、3382日；按canary逐日耗时线性外推约4.3小时，月度I/O摊销/缓存/负载会影响实际时间。
这不是实测全量耗时或上限。长任务尚未由Codex执行。

检查：D1 synthetic38项通过；加V3 precompute regression共43项；fast46项及Ruff通过；
PowerShell parser、独立canary重放、receipt/aggregate重算核验通过。
覆盖手算ties/方向/层级、alias、日期读取前失败、bounded投影、schema/dtype、hash、损坏续跑与错误oracle反例。
未运行完整 `check_quality.py full`：历史closeout validators涉及本任务禁止的冻结outcome/近期证据；
采用scoped synthetic检查，不宣称全仓验证通过。六contrasts/HAC/bootstrap仅声明式合同，未执行evaluation。

## 6. 用户执行的PowerShell命令

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_baseline'
& '.\scripts\run_literature_representation_d1.ps1' `
    -Python 'E:\anaconda_envs\qlib_env\python.exe' `
    -RunId 'd1_structure_20260910_v2'
```

依次执行packet/source/code检查、完整月度扫描+逐日naive独立重放、receipt/aggregate复核；非零退出即停。
`verify-full`只重读diagnostic/receipt，不再次读canonical；独立计算在`full`的每个日期完成。
没有模型/label/prediction/importance/outcome读取入口。

完整chunk检查hash后复用。中断留下的未完成chunk会硬停保留，不自动删除/覆盖；
先检查异常及access日志、排除污染/正确性问题后才可另用RunId，不能换ID隐藏outcome误读。
不要再次`build`覆盖候选。

结果：`outputs/literature_factor_representation_d1/d1_structure_20260910_v2/full/`，
包含summary、逐年/折leaves/outputs/arms CSV、月度diagnostic Parquet及access/receipt。
fold汇总仅按P0 train/predict日轴，重叠训练日按各折分别归属，不执行evaluate角色。
canary目录同名year/fold汇总仅覆盖采样日，不能冒充全年计数。

## 7. 边界与下一停止点

只允许2010-01-29至2023-12-29的研究feature值；非法日期/列在I/O前失败。
跨期Parquet以列投影和日期predicate读取，不做whole-file值读取/hash。先对完整dated PIT截面rank，
不用label可用性缩减截面。这是应用层allowlist，不是操作系统沙箱。

本轮未训练R/C/H、未打开封存预测分数/IC/importance/收益结果、未执行pool outcome comparison，
未访问2024+研究值，未改变V3 float64 Sequence权威、Broad/Strict预计算或V0.1快照。

用户全量运行结束后，仅审阅结构计数、缺失/节点组成与U理由。
rank minimum100、family内50%尚未正式冻结，32个Alpha101 raw保留仍需人工认可。
取得全量证据与人工判断后才能形成可冻结packet；freeze本身也不自动授权D2。
