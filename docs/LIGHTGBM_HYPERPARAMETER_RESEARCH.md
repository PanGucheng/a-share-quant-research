# LightGBM Hyperparameter Research V1

2026-09-16：用户授权参考新的研究顺序提案实施。本文件取代“不得开启模型研究”的旧停止指令，
仅开放 B494 的 2015–2023 development 超参数研究。长训练仍由用户运行。

## 研究顺序与判断

暂停 E3 经济选择和 actual path 接线。`5af341e` 的 30 个组合结构候选作为
Portfolio Mechanism Research / Candidate Set V1 保留，不重跑，不选经济赢家。
E1 COMPLETE、E2 CORE READY 保持；条件性账户问题没有因暂停而解决。

V3 配置经代码核实确为 leaves15/depth4/min100/lr0.03/L1=0/L2=1/FF0.8/100轮。
它是保守基准，但“明显欠拟合”是待检验假设。结构 backlog 不能证明 cap 在经济上劣势；
旧 prediction stream 的机制观察也不能直接冻结新 stream 的组合参数。

## 固定范围

复用 f2f3fc3 float64 monthly Sequence、B494 顺序、canonical、20D t+1 label、
原始年度 folds、expanding history、按日等权且跨历史日等权、rank-before-feature-mask。
保留 Model Baseline V1 全九折模型和 predictions，区别于 Forward Strategy V1。
不改因子定义/池、training window、recency、refit cadence、label horizon、模型家族。
不访问 2024+，不跑组合或继续 E2 工程，不依据收益选择任何参数。

## Nested 时间设计

对 outer Y=2015…2023，outer train/predict/evaluate 完全沿用已审计日历。
inner validation 为 outer 合法 train dates 中 Y−1 年的日期（年末未成熟日期不纳入）。
inner train 从 2010 起扩展，要求 signal 在 validation 起点之前，且 label exit 严格早于该起点。
因此两个边界均按真实 label interval purge，不能仅按信号年份分割。
2015 首折内层为 2010–2013 合法训练 / 2014 成熟验证；2014 是训练研究范围，非经济 warmup 扩权。
inner train 自己拟合 bins，validation Dataset reference=train；验证数据不影响训练分箱。

每折独立运行全部九个预定 trials；只用该折 inner 指标选择结构和 best_iteration。
再从头在完整 outer training history 重训一次，按所选轮数预测全年。
outer 标签仅在九折训练、预测和独立 saved-model replay 全部完成后由独立 evaluate 操作读取。
后续年份合法训练可以用以前 outer 年份已成熟标签，这不等于用当前 outer 标签调参。

## 固定预算与早停

| trial | 相对 V3 的变化 | rounds |
|---|---|---|
| fixed100 | 无 | 固定100，内层对照并可入选 |
| base_es | 无 | inner early stopping |
| lr06 | learning_rate=0.06 | 同上 |
| leaves31 | num_leaves=31,max_depth=5 | 同上 |
| leaves63 | num_leaves=63,max_depth=6 | 同上 |
| min300 | min_data_in_leaf=300 | 同上 |
| l1_1 | lambda_l1=1 | 同上 |
| l2_10 | lambda_l2=10 | 同上 |
| ff100 | feature_fraction=1 | 同上 |

八个 ES trial 上限800轮，patience50，min_delta=0，唯一 early-stop metric 为等日期平均
Spearman Rank IC；记录每轮完整曲线。训练目标仍 regression rank target，禁用默认 l2 选轮。
常数预测日 early-stop IC 计0且另记数量，避免早期常数模型使优化器失效；正式 outer 对照
按原 D3 语义将任一模型常数的共同日标为不可评分，不能删掉只对一臂不利的日。
该 callback 行为依据 [LightGBM 4.6 文档](https://lightgbm.readthedocs.io/en/v4.6.0/pythonapi/lightgbm.early_stopping.html)。

固定81次 inner fits +9次完整历史 refits，最多65,700轮；串行 fit，8线程。
不做全因子乘积、Optuna 或事后追加 trials。inner 月度 float64 块每折准备一次复用，
outer refit 使用现有预计算函数；不重做性能研究。800轮耗尽必须记录为预算截断，不能称收敛。
实际耗时取决于早停，可能多日，既有100轮耗时不可直接当成本轮总时长。

## 选择规则与可解释性

先取 inner mean daily IC 距最大值不超过0.001的候选集合，再选 leaves×best_rounds
最小者，依次以 leaves、rounds、预定 trial 顺序打破平手。0.001 是预先固定的工程容差，
不是统计显著性或非劣界限。保存所有 trial 年度/半年 IC、ICIR、曲线、轮数、成本与选择名单。
fixed100 允许胜出，因此不预设一定升级。半年度、跨折、邻居差异用于诊断，不能临时改目标。
容量邻域只有15/31/63等稀疏轴向点，不证明多维交互平台；本阶段不自动细化。

最终对照是“每年只用过去选参的固定调参流程”对 frozen baseline，不是事后全九年最佳
固定参数重演。按 outer 年报 mean daily Rank IC、非年化ICIR、worst-year、负IC年数、
2015–17/2018–20/2021–23 era、paired delta HAC20支持统计、prediction/common coverage。
只比较同一 B494 全部 canonical keys、同日共同有限标签和分数，至少100对；不沿用五臂
交集，因为本轮只有两臂，baseline 也必须在相同两臂样本重算。两臂有限预测 mask 应完全一致。

B494 发现和 development 结果已被观察；嵌套训练不消除历史选择偏差。不得称 fresh OOS，
不以单一最高IC判定 production 替换。最终候选须人工结合全九年/邻域/成本决定；不能自动升级。

## 执行与恢复

入口 `scripts/research_lightgbm.ps1`：Preflight 为元数据/文件完整性校验；Run 顺序训练与
独立进程 Replay，然后 Evaluate。默认 RunId 为 `lgbm_nested_20260916_v1`。
先冻结该 RunId 的完整代码/配置/source receipt 绑定，完成单元按 hash 跳过；失败保留隐藏
staging，重启同一命令重做未发布单元。不得改 receipt 续跑，代码或范围变化须停下审阅。
每折 outer 成功后释放该折已验 hash 的 inner float64 scratch，保留原 cache receipt 和单独的
retirement 记录；其状态为已消费的缓存，不再声称原 cache 文件仍完整。模型、trial、曲线、
内层预测及 keys/target/weight 保留。删除只限新运行目录下已核对路径/hash的 float64 文件。
任何已选 trial 的 outer refit 必须匹配原 B494 月度训练 keys/counts，拒绝样本漂移。
至少预留60GiB磁盘；本轮不是对所有参数资源需求的正式认证。

交付状态先为 IMPLEMENTED / AWAITING USER RUN。用户长运行完成后核验全部 trials、replay、
outer 对照，才能回答欠拟合/轮数不足/稳定容量区域及 Model V2 candidate。未运行不得填入结果。
暂停后续 training regime、portfolio retuning、actual execution、2024+，提交推送后等待人工审核。
