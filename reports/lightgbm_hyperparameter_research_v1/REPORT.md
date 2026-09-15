# LightGBM Hyperparameter Research V1 — 实施交付

2026-09-16。**IMPLEMENTED / AWAITING USER RUN**，未开始真实长训练或新outer结果评价。
E3 ECONOMIC SELECTION PAUSED / STRATEGY V2 CANDIDATE PENDING。

## 对提案的吸收和修正

已接受先调模型、后对最终prediction stream做组合研究的顺序；暂停actual path工程。
`5af341e`保留为Portfolio Mechanism Research / Candidate Set V1；30个目标结果不重跑。
保守baseline是否欠拟合尚未证明，不能先宣布100轮不足。cap积压只是结构事实，不能作经济优劣结论。

采用[固定nested计划](../../docs/LIGHTGBM_HYPERPARAMETER_RESEARCH.md)：每年只用上一年度成熟
inner validation及更早的purged训练历史，搜索9个预定trials。8个配置以每日Rank IC早停，
原始100轮为单独控制并可入选；均值在0.001容差内优先更低树复杂度。
每折完整outer训练从头拟合，仅早停轮数及参数来自inner。所有outer结果是development证据。
不进行全部参数交叉或看结果后扩搜索；稀疏轴向点只能初步判断容量区域，不能证明全面最优。

## 实现与复用

- 原V3 float64 Sequence、rank-before-mask/日权重、训练cache、bounded canonical reader、日历、
  outer预计算和独立saved-model replay均复用；旧learner及冻结合同字节不改。
- 新增独立nested政策、inner Dataset/early-stop接线、可恢复trial/selection/refit发布，
  outer训练月度keys/counts必须与原B494相等。validation bins只引用inner train。
- 单独进程重放九折全部outer预测；内层指标以SciPy scalar oracle复核。
  独立Evaluate入口在replay receipt通过前拒绝读取outer标签，逐日两臂同样本对照也核对SciPy。
- 输出全部trials、曲线、best rounds、半年诊断、年度选择及两臂daily/annual/era/coverage/HAC20。
  无自动production替换；run完成仍需人工结合全部结果判断Model V2 candidate。
- 每折只保留一套inner float64 scratch供9个trials复用，outer成功后验hash定向释放scratch；
  cache原receipt及独立retirement记录保留，其余模型/预测/keys/target/weight/失败staging不删。

## 预检与验证

本地main与origin/main起点同为5af341e。实际PowerShell Preflight通过：B494=494、9折、
9trials/折、最多90次fit；E盘当时约175GiB空闲。
2015首折：inner train 2010-01-29…2013-12-02（927日），valid 2014-01-02…2014-12-02（224日）。
2023末折：inner train至2021-12-02（2877日），valid 2022-01-04…2022-12-01（221日）。
训练与验证边界均使用真实21-session label exit隔离；不拿outer年选轮。

新专项18项测试通过，包括九折独立purge oracle、未来/maturity拒绝、固定样本/ties/常数、
小型synthetic数据上的真实8线程LightGBM Sequence固定轮数和早停、saved-model精确预测、
outer标签开启顺序、定向scratch恢复。没有进行真实大样本容量/耗时认证。
V3/预计算/D3-A及nested定向回归70项通过（19.44秒），之后补充完整九年synthetic评价测试，
最终nested专项18项通过（6.89秒）。fast检查Ruff通过、46项通过（17.33秒）；新增代码单独
Ruff通过，共117项不同测试。本轮以这些有界检查代替包含无关Forward/
recent历史流程的full tier，未执行完整full tier；不为无关检查访问2024+真实数据。

## 用户运行

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_baseline'
& .\scripts\research_lightgbm.ps1 -Action Preflight
```

通过后正式启动（单一入口，失败即停，后续阶段不会继续）：

```powershell
& .\scripts\research_lightgbm.ps1 -Action Run
```

Run顺序执行专项测试 → 81次inner fits/9次outer refits → 独立进程Replay → 独立Evaluate。
默认RunId=`lgbm_nested_20260916_v1`，运行时首次绑定当前代码/计划/配置/runtime/source receipts。
在首次fit前核验既有development feature切片与标签cache，不重算标签、不重新采集行情。
串行8线程；最坏65,700轮，可能多日；请保持至少60GiB空闲并留意失败staging占用。
首次运行尚无可信总时间估计，不能按旧100轮训练时间承诺完成时刻。

中断后再次执行同一个Run命令，完成单元逐hash校验后跳过，未发布单元重新执行；失败证据保留。
不要改文件/hash或为绕过错误随意换RunId。若仅独立重放/评价被中断，可分别使用
`-Action Replay`、`-Action Evaluate`；Evaluate会强制检查独立重放及各折发布证据。

输出：`outputs/lightgbm_hyperparameter_research/lgbm_nested_20260916_v1/`。
每折`trials/`、`selection/`、`outer/`；总体`verification/`、`evaluation/REPORT.md`、
`evaluation/summary.json`、`daily.csv`、`descriptive.csv`及hash receipts全部保留。

## 尚不能回答的研究问题

当前没有新的真实trial结果，欠拟合、通常早停轮数、容量平台、正则化影响、年度参数稳定性、
相对baseline的IC/ICIR/worst-year改善及是否值得替换均为 **PENDING USER RUN**。
不宣布LIGHTGBM TUNING COMPLETE或Model V2 candidate；长运行结束后核验并写结论再人工审核。
E1/三项行情状态事件扫描、E3旧30候选、Frozen Baseline、Forward及2024+没有运行或修改。
