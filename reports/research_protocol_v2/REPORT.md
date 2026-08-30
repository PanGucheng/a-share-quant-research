# Research Protocol V2 / Purged Rolling Split V2

> 状态：`FROZEN DESIGN`；本阶段只设计、生成并验证研究协议，没有训练模型、读取候选结果或修改 Strategy V1 / Forward Track。

## 结论

Research Protocol V2 已具备开始后续 Structured ML V1 **开发研究**的时间边界基础（本阶段未启动该研究）。它把模型选择固定在 `5` 个 development 时间环境，把 `7` 个更细历史环境及旧三个 test 全部隔离为 `post_observation_research / historical_diagnostic_only`。所有 `34` 个关键验证项状态为 `pass`。

V2 的主要变化不是放松保护，而是删除 V1 在 exact interval purge 之后重复执行的同侧 20 日 embargo。标签仍为 `t+1` 入场、`t+21` 退出，因此训练样本必须满足 `label_end < evaluation_start`，边界前真正需要排除 21 个 feature dates。

## V1 审计

V1 最初为早期因子筛选、LightGBM baseline 和少量 historical holdout 设计。它的优点是简单、保守、按真实交易日保存精确 assignments，并阻止 train/validation 标签跨入后续 period。其三个 outer split 的 train/validation/test 日期分别为：

- `split_001`: 688/77/120
- `split_002`: 808/77/124
- `split_003`: 926/83/124

名义 6 个月 validation 在真实日历中约有 `118`–`124` 个交易日。每段先删除 21 个与 test interval 重叠的 validation feature dates，再删除 20 个 validation tail dates，所以只剩 `77`–`83` 日。train 边界也执行相同的 21+20 删除。

purge 的真实作用是删除标签区间与下一段相交的样本；embargo 在 V1 实现中又从已经安全的 train/validation 尾部各删 20 日。它没有隔离 evaluation 之后进入未来训练的样本，也没有单独声明序列依赖机制，因此语义上是对相同边界的第二层 buffer，而非不同风险。V1 仍无 interval overlap；问题是信息损失和语义重复，不是保护不足。

## V2 时间结构

### Development evidence

固定 `5` 个两个月 validation 环境、每三个月推进一次：

- `dev_env_001`: 2023-05-04..2023-06-30, 40 dates, labels through 2023-07-31
- `dev_env_002`: 2023-08-01..2023-09-22, 39 dates, labels through 2023-10-31
- `dev_env_003`: 2023-11-01..2023-12-29, 43 dates, labels through 2024-01-30
- `dev_env_004`: 2024-02-01..2024-03-28, 35 dates, labels through 2024-04-30
- `dev_env_005`: 2024-05-06..2024-06-28, 39 dates, labels through 2024-07-29

一月间隔用于让 20 日标签自然成熟；若节假日使 interval 仍跨入下一环境，生成器按实际 `label_end` 排除尾部日期，而不是使用看起来安全的固定数字。最后 development label 在 `2024-07-29` 已成熟，早于 2024-08-01 diagnostic boundary。

两个且仅两个训练历史假设进入候选：

- `expanding`：旧数据仍有统计信息；每 fold 使用全部合法历史，train dates 为 `522`–`764`。
- `sliding_504`：A 股非平稳性可能使约两年以前的数据有害；每 fold 固定使用最后 504 个已经通过 interval purge 的训练日。

不扫描 1/2/2.5/3/4 年。两种窗口必须在同一五个环境上比较；旧历史 diagnostics 不能改变选择。

### Historical diagnostic evidence

V2 预定义 `7` 个两个月、三个月步长的历史诊断环境，从 `2024-08-01` 到 `2026-03-31`。它们增加 regime、decay 和 failure analysis 的分辨率，但全部是已经观察过的历史，不是 fresh OOS。旧 `split_001`–`split_003` 保留原日期与 artifact identity，仅作为与旧实验对照的 legacy anchors。

只有 development 中冻结的单一 candidate 才能 replay diagnostics；模板当前全部 `execution_authorized=false`。diagnostic performance、feature importance 或失败不能回流改模型、representation、窗口、调仓或超参数。

### Forward evidence

现有 Strategy V1 Forward Track 原样保留。V2 不把历史重新切片包装成 prospective evidence。任何 Model/Strategy V2 的真实确认仍须在候选冻结后由自然到来的新数据提供。

## 模型选择与 trial governance

后续 LightGBM、DoubleEnsemble 和 raw/economic/sleeve/hybrid representation 使用完全相同的五个 folds。主指标是各 fold `mean_daily_rank_ic` 的等权平均，同时强制报告 paired delta、worst fold、fold dispersion、negative-fold count、coverage 和 failure count。

challenger 只有在 paired mean 与 median delta 都为正、至少赢 3/5 folds、且无 fold 失败时才可替代较简单 incumbent；否则记录 tie/inconclusive。每个注册实验只允许改变一个轴，最多 8 个 candidate。architecture、representation、training window 和 hyperparameter 试验分别登记，candidate manifest 必须在 fit 前冻结，实际尝试数（含失败）不可删除。

## Label horizon 与决策频率

20 日标签描述从次日到第 21 个交易日的中期横截面收益，不要求 portfolio 只能每 20 日调仓。5 日 rebalance 是执行层的持仓更新选择，但会重复使用高度相关的中期信号，可能放大 turnover。后续模型报告必须提供 score autocorrelation/decay、5 日更新下的持仓重叠与 turnover；本阶段不 sweep 5d/10d/20d/40d 标签。是否研究多 horizon 保留为独立、预注册的后续问题。

## Qlib 评估

固定 Qlib commit 为 `d5379c520f66a39953bad76234a7019a72796fd0`，无需升级。当前 `RollingGen` 支持 expanding/sliding segment 平移、固定 trading-step 与粗粒度 `trunc_days`，适合在项目边界确定后物化普通 Qlib task；它不能表达逐样本 exact label interval、evidence authority、split-local feature eligibility 或 diagnostic isolation。因此 V2 采用项目生成器作为 authority，暂不调用 RollingGen。

Recorder 可记录模型 artifact，Collector 可汇总 recorder，TaskManager 则引入独立 task backend；当前项目已有 hash manifest、prediction lineage 和 CSV 任务表。现在接入会增加 MLflow/MongoDB/task glue，未证明减少复杂度，所以全部暂缓。Structured ML 首次规模扩张后再用实际重复成本复评。

## V1 与 V2 的信息效率

- V1：3 个 outer validations，共 `237` / `360` 个按 split 计的 usable/nominal validation dates（`65.8%`）；3 个 historical test windows；每 split 42 purge + 40 embargo dates。
- V2：每个训练历史 candidate 看到 5 个统一 validation environments，共 `196` / `201` 个 usable/nominal validation dates（`97.5%`）；7 个细粒度 diagnostic environments；每 task 只做 exact 21-date train-side interval purge，额外 embargo 为 0。
- V2 的价值是更多 selection regimes、统一 candidate comparison 和明确证据权限，不是把更多历史窗口称作 OOS。保护等价或更强：训练标签仍严格结束于 evaluation 前，且最后 development label 也严格早于 diagnostic boundary。

## 独立验证与边界

验证覆盖 train/evaluation label overlap、chronology、duplicate/cross-fold assignments、calendar/matrix-date scope、相邻环境 label isolation、development/diagnostic authority、legacy test isolation、determinism、embargo=0 和 task execution hard-stop。Factor Universe V2、Matrix、Economic Multi-Factor Research V1、Model/Strategy V1、frozen predictions、historical releases 与 Forward outputs 均未修改。

## 对阶段问题的简答

1. V1 为早期少量 holdout 和严格防泄漏而设计；优点是简单保守、exact assignments 可审计。
2. 不适合 Structured ML 的核心是单一 regime 选参、outer windows 少、以及 purge 后重复 embargo。
3. V2 使用 5 个 development 环境、两个有经济假设的训练历史方案、7 个 diagnostic 环境和不变的 forward evidence 层。
4. expanding/sliding 都保留为 development hypothesis；diagnostics 不参与选择。
5. 旧三个 test 是 legacy diagnostic anchors；Forward Track 角色不变。
6. 20 日 label 与 5 日 decision 可以共存，但必须审计 decay/turnover；多 horizon 需另立研究。
7. Qlib RollingGen 当前不采用为 authority，也无需升级；Recorder/Task/Collector 暂缓。
8. V2 保持 exact interval protection，提高 regime coverage并减少无解释的数据损失。
9. Model V2 下一阶段只能先注册 candidate、只跑 development、冻结 winner/无 winner 结论，再解锁 historical replay。
10. 当前已具备开始 Structured ML V1 protocol-governed development 的基础，但本阶段没有开始训练或比较。

## Remaining uncertainties

- 五个 development 环境仍来自有限的 2023–2024 历史，不能消除 regime uncertainty。
- 504 日 sliding 是一个机制假设，不是已知最优窗口；若结论 inconclusive，应保留 expanding incumbent，而不是增加窗口搜索。
- diagnostic replay 的成本和 Qlib experiment tracking 需求只有在真实 Structured ML 任务规模出现后才能可靠评估。
