# LightGBM nested procedure：最终结果审阅

2026-09-16。**LIGHTGBM HYPERPARAMETER RESEARCH COMPLETE / MODEL V2 CANDIDATE**。

结论：将本轮 `lgbm_nested_20260916_v1` 的 **B494 年度 nested tuned procedure**
列为 Model V2 研究候选。全部预定 81 个 inner trials、9 次 outer refit 与已有独立模型重放齐备，
本次复核未发现阻止候选成立的 artifact、选参、时间隔离或统计错误。
整体平均 IC 改善有 development 支持，但年度及后段表现不足以证明稳定支配 baseline。
**不是生产替换、不是 Strategy V2、不是固定参数赢家，也没有新增训练或开启下一轮研究。**

这是一项审阅判断，不是事先声明的自动晋级检验。不存在为了通过而删除某年、改搜索范围、
改 patience/预算或根据 outer 表现重选参数。原始运行状态 `MODEL_CANDIDATE_REVIEW_PENDING`
作为封存的机器运行结果保留；本文件及 final_review/decision.json 记录其后的审阅决定。

## 证据与验收矩阵

| 项目 | 最终状态 | 核验范围 |
|---|---|---|
| 预定搜索 | COMPLETE | 9 年 × 9 trials；没有补点或参数交叉 |
| Inner 统计与早停 | PASS WITH BUDGET LIMITATION | 81 份逐行预测、target、daily IC、上下半年统计、完整曲线、保存轮数；12/72 ES 试验到预算上限 |
| 九年选参 | PASS | 独立按最高均值减 0.001、再按 leaves×rounds 等规则复算；与原 selection 完全一致 |
| Outer 模型与样本 | PASS | 9 模型、4,377,824 条预测；训练 batch keys/counts 与冻结 B494 相等 |
| 独立模型重放 | PASS | 原 9 折 exact replay receipt 与当前模型语义哈希核对；本次不重复读取全部特征重放 |
| Outer 结果评价 | PASS | 从保存的 baseline/tuned 预测与允许的成熟标签独立复算每日 Spearman，再复算年度/阶段/HAC20 |
| 时间和输入隔离 | PASS | 合同与代码哈希、2010+ train、上一年 valid、label-maturity purge、读访问范围；没有读取 2024+ 研究值 |
| 候选判断 | MODEL V2 CANDIDATE | development 候选；production replacement=false |
| 经济研究 | PAUSED | E1 COMPLETE / E2 CORE READY；E3 经济选择、Strategy V2 与 actual path 均不恢复 |

审阅程序 [scripts/review_lightgbm_completed.py](../../scripts/review_lightgbm_completed.py)
只读封存运行，写入单独的 [final_review](final_review/audit.json)。无训练入口、无原始特征加载。
共校验 711 份文件（包括 receipt），包含 baseline；9 份 scratch retirement 只允许与原 receipt
一致的 `.float64` 缺席，不能把它们声称为仍可读取的缓存。历史失败尝试、原 receipt 和产物不改动。
模型文件字节哈希与 LightGBM model_to_string 语义哈希是两种口径，分别核对，不能直接混比。

运行合同 canonical hash：`cb72acb4941d330f09e9cde49448f5ceda42dce77e0633f8f1c7f102c6323e31`。
合同文件 SHA256：`86ca07f8005990225443febe287662ddf0a66189d116b441777e37332f590a74`。
原研究计划及 25 个合同绑定代码/文档保持不变。
本次针对统计、选参和标签评价门禁的 5 项无训练测试通过（14 项未选执行）；完整 artifact 审计通过。

## 九年 selection 与 best_iteration

年份是 outer 年份，所有选择只看上一年 inner validation。表中 mean 是入选 trial 的 inner mean，
不一定是该年最高 mean。所有未列参数继续沿用 baseline。

| Outer 年 | 入选 trial / 参数变化 | best_iteration / outer rounds | 入选 inner IC | 0.001 plateau |
|---|---|---:|---:|---|
| 2015 | l1_1：lambda_l1=1 | 38 | 0.141530 | l1_1 |
| 2016 | leaves63：63 leaves / depth 6 | 363 | 0.176109 | leaves63 |
| 2017 | l1_1 | 310 | 0.247588 | l1_1 |
| 2018 | lr06：learning_rate=0.06 | 444 | 0.169939 | lr06 |
| 2019 | l2_10：lambda_l2=10 | 564 | 0.181001 | leaves31, l1_1, l2_10 |
| 2020 | lr06 | 779 | 0.132837 | lr06, leaves63 |
| 2021 | leaves63 | 709 | 0.155584 | leaves63 |
| 2022 | lr06 | 59 | 0.090229 | lr06, l2_10 |
| 2023 | l1_1 | 150 | 0.126103 | leaves31, l1_1 |

2019 真正最高 inner mean 是 leaves31 的 0.181531，但复杂度为 31×275=8525；
l2_10 的 15×564=8460 更低，因此按预定规则入选。2020 最高是 leaves63 的 0.133135，
lr06 在容差内且复杂度更低，也正确入选。这两年不能把 inner_best_mean 当作选中模型的分数。

入选轮数范围 38–779，中位数 363；3 年不超过 150，6 年超过 300。
同 baseline 参数的 base_es 在 8/9 个 inner 年优于 fixed100，平均差 +0.013068，
但这是早停使用同一 validation 的样本内选择收益，不能当作独立泛化改善。
2022 的 base_es 只保留 1 轮且弱于 fixed100，2015 入选 38 轮的 outer 又明显下降。
因此“所有年份都因 100 轮而欠拟合”不成立；也不能按这些已观察 outer 年份临时切换回 baseline。

**预算和早停限制：**12 个 ES trials 的完整曲线达到 800 轮，分布于 outer 2018（1）、
2019（1）、2020（5）、2021（5）。其中唯一入选且到预算上限的是 2020 lr06，best=779、
evaluated=800，尚不足其后 50 轮 patience。best<800 不代表收敛。
另有 2020 的 ff100/l1_1/leaves31 早停在 best=2，2022 base_es/min300 在 best=1；
它们体现局部早期峰值与 patience 的影响，不能把其差表现解释成参数方向必然有害。
本轮不扩大预算，也不追加训练。候选的定义包含现有 800/50 预算及早停规则。

## Parameter-axis behavior

以下是 **inner 的九年等权描述**，相对 base_es；每个轴自身会选不同轮数，
因此是“参数变化＋所诱导的早停路径”对比，不能解释为固定轮数下的纯因果参数效应。
全部 81 个数值、上下半年及资源数据见 [all_trials.csv](final_review/all_trials.csv)。

| Trial | 平均 Δinner IC vs base_es | 正差年份 | 入选次数 | 审阅 |
|---|---:|---:|---:|---|
| fixed100 | -0.013068 | 1/9 | 0 | 部分年份增加/调整轮数有价值，非普遍结论 |
| base_es | 0 | — | 0 | 比较锚点，不是被证明劣势的生产模型 |
| lr06 | +0.001198 | 7/9 | 3 | 最一致的轴向支持，但变化量小且 2020 受预算限制 |
| leaves31 | -0.002306 | 5/9 | 0 | 2016 强、2020 弱；不能推出更大容量单调改善 |
| leaves63 | +0.000498 | 4/9 | 2 | 2016、2021 入选；2015 弱于 base_es 约 0.01444 |
| min300 | +0.000027 | 4/9 | 0 | 与 min100 几乎持平，没有支持更改全局默认值 |
| l1_1 | -0.001198 | 5/9 | 3 | 年份依赖明显；入选多不等于九年平均最好 |
| l2_10 | -0.000548 | 4/9 | 1 | 2019 在容差内凭复杂度入选，无普遍改善证据 |
| ff100 | -0.003472 | 4/9 | 0 | 没有取消 feature subsampling 的一致依据 |

四个年份存在多个容差内候选，说明**局部相近分数**，不能证明跨年份、跨轴的稳定参数平台。
剩余五年 plateau 只有一个成员；稀疏单轴试验没有参数交互的证据。所有入选 trial 上下半年
inner IC 都为正，但差异明显，例如 2015 选择所用的 2014 validation 为 0.193168 / 0.083007。
这些半年度切片只作描述，不新增选参门槛。

## Baseline vs tuned：逐年稳定性

同日、同股、同标签 finite mask；ICIR 是每日 IC 均值/样本标准差，**不年化，也不是 Sharpe**。

| Outer 年 | Baseline IC | Tuned IC | ΔIC | Baseline ICIR | Tuned ICIR |
|---|---:|---:|---:|---:|---:|
| 2015 | 0.178725 | 0.159866 | -0.018859 | 1.7884 | 1.4562 |
| 2016 | 0.226505 | 0.234704 | +0.008199 | 1.8814 | 1.9997 |
| 2017 | 0.125154 | 0.146966 | +0.021812 | 1.3758 | 1.5734 |
| 2018 | 0.160969 | 0.175275 | +0.014306 | 1.9018 | 2.3837 |
| 2019 | 0.093091 | 0.113733 | +0.020642 | 0.6677 | 0.8348 |
| 2020 | 0.125496 | 0.155967 | +0.030471 | 0.9936 | 1.4882 |
| 2021 | 0.101834 | 0.093318 | -0.008516 | 0.7699 | 0.8031 |
| 2022 | 0.125366 | 0.127267 | +0.001901 | 1.0974 | 1.1252 |
| 2023 | 0.111766 | 0.111292 | -0.000474 | 0.6845 | 0.6989 |
| 全期 | 0.139079 | 0.146886 | +0.007807 | 1.0937 | 1.2035 |

Mean IC 6/9 年改善，3 年下降；ICIR 8/9 年改善。2021/2023 的 ICIR 上升并不抵消 mean IC 下降，
两者不能混作“八年模型更好”。两臂均无负年度 mean IC；最差年 baseline 为 2019 的 0.093091，
tuned 为 2021 的 0.093318，几乎没有实质改善，而且并非同一年。

| 阶段 | Baseline IC | Tuned IC | ΔIC | 解释 |
|---|---:|---:|---:|---|
| 2015–2017 | 0.176795 | 0.180512 | +0.003717 | 2015 损失抵消部分后两年改善 |
| 2018–2020 | 0.126473 | 0.148278 | +0.021805 | 整体增益主要来源 |
| 2021–2023 | 0.113009 | 0.110581 | -0.002428 | 改善没有在后段延续；不能主张稳定优越 |

全部 2,189 个预测交易日保留，2,168 日可评分，2023 年末 21 日因 development 边界标签不成熟而 NA。
九年预测 coverage 均为 100%；common coverage 全期 94.6803%，2015 为 82.9325%，
2023 为 91.1602%。这不是预测缺失，common 样本受到标签可得性及边界限制。
配对比较消除了两臂样本不一致，但不能保证缺失标签随机，或把结果外推到未评分证券。

## HAC20 与证据强度

在完整交易日轴上保留 NA，以 Bartlett lag 20 对 paired daily ΔIC 的均值估计：

- Mean ΔIC：**+0.007806523**；n=2,168。
- HAC20 SE：**0.002954077**；双侧正态近似 p：**0.008226577**。
- 近似 95% 区间：**[+0.002016637, +0.013596408]**。

独立标量 lag-product 实现与原结果一致到 1e-12；另用含内部缺失日的 dense Bartlett kernel
测试验证不能压缩 NA 日。年度/阶段的同口径诊断见 [stability.csv](final_review/stability.csv)，
它们是补充审阅切片、未经多重比较校正，不另作正式“显著年份”筛选依据。

HAC20 处理既定带宽内的时序相关，不能消除更长依赖、制度变化或此前模型/因子研究对 development
时期的适应。Outer 没参与该年 inner 选参，但 B494 与历史研究已经观察过这些年份；
所以这是 retrospective development，不是 fresh OOS。不能把 p 值解读为候选生产成功概率。

## 候选范围与停止点

保留 B494、V3 float64 Sequence、原训练历史与样本/权重，保留九个预定 trials、上一年 purged
inner validation、每日 Rank IC 早停、800 轮/50 patience、0.001 复杂度优先选择，以及
每年完整 outer refit。这整个程序构成候选，九年所选参数是其历史实例。
不把 lr06 或 l1_1 等某个参数事后固化为全期最优，也不按 outer 年份挑选 baseline/tuned。

候选成立的理由是：合同执行与独立复核完整、总体和多数年度改善、没有发现工程性阻断。
仍保留它为候选而不替换 baseline 的理由是：后段走弱、2015 明显回退、参数与轮数跨年变化大、
若干曲线被预算截断、development 反复观察以及标签覆盖限制。
没有证据证明这些 IC 变化会转化为扣费经济收益；本轮不进行该评价。

**停止等待人工审核。** 不新增训练，不选择新的 training regime，不开展组合/E3/E4，
不访问 2024+，不合并独立的 RQAlpha PoC 分支。Model Baseline V1、Strategy V1 及本轮全部原始产物保留。
