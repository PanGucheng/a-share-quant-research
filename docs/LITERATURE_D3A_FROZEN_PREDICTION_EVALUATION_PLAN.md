# D3-A：五臂冻结预测评价实施计划

2026-09-11，用户要求评估《实施 D3-A 五臂冻结预测评价》建议、吸收有价值部分，先写计划后实施。
本文件是对该请求的范围解释和实施细则；附件不是自动执行的独立指令。
正式长任务继续由用户在 PowerShell 运行。交付 evaluator、合成验证、只读 preflight 和命令后，
本轮停止于 **IMPLEMENTED / OUTCOME UNOPENED / USER RUN PENDING**，不把代码交付称为完成评价。

## 1. 评估与授权

建议有道理，主要价值在于保护冻结实验、共同样本和首次揭封证据，而不是重新选模型。
已核对 main 的 D2 完成提交 `c3bfed5`、D1 freeze、V3 日历和现有统计代码。
正式执行前再次逐项核验文件哈希与 sealed receipts；不单凭状态文档认定完整。

本次授权仅把 B494、S332、R218、C201、H358 的冻结 predictions 与 2015–2023
开发边界内成熟标签配对，进行一次正式 prediction-level representation comparison。
这是原 outcome 禁令的有限新授权；D3-B、组合、交易成本、收益曲线、SHAP、调参、重训、
新池及 2024+ 研究值继续禁止。评价不读取特征或价格，也不执行 saved-model 重放。

固定范围标签：

```text
pool_discovery_scope = retrospective_development_2010_2023
representation_design_scope = outcome_blind_retrospective_metadata_and_feature_evidence
model_fit_scope = past_only_purged
evidence_class = retrospective_pseudo_oos_development
unbiased_final_estimate = false
recent_access = false
```

这不是 fresh OOS，也不是 fully ex-ante discovery。首次配对读取后，后续设计只能称为
post-outcome research generation。既有 D1/D2 `outcomes_authorized=false` 是历史事实，
不得改写；新增独立 D3-A 执行契约记录本次授权及旧 freeze hash。

## 2. 保留的权威与输入

- [D1 freeze](../reports/literature_factor_representation_d1/freeze_v1/freeze.json)：
  `29e473cedcefa2715bb770188d64da23db579e509bb2a99982e93b8885d24ccc`。
- [D2 完成报告](../reports/literature_factor_representation_d2/COMPLETION_REPORT.md)：27 个 R/C/H 模型。
- B/S run：`outputs/research_protocol_v3_precompute/v3_precompute_broad494_strict332_20260909_v1`。
- R/C/H run：`outputs/literature_factor_representation_d2/d2_rch_20260910_v1`。
- [V3](RESEARCH_PROTOCOL_V3_MVP_PLAN.md)：float64 Sequence、固定 100 轮、模型/目标/权重/
  purge/feature order 保持原样；使用 `v3_recompute_audit_20260909_v1` 的已审计
  `audit/YYYY/keys.parquet` 和 `labels.parquet`，不创建新标签定义。

Preflight 校验 45 个 model/prediction 单元及独立 replay、D2 sealed 汇总、D2 完成核验绑定、
全部 168 月缓存 receipts 与字节、D1 freeze/code/runtime、B/S ordered members、
V3 keys/label 缓存 receipts 和 evaluation contract。只解释 metadata；数值文件只读字节作 checksum。
不调用旧 `load_context()`：它还会校验与本任务无关的历史 outcome 文件。

日历从 V3 assignments/intervals 推导，禁止硬编码 2,168 为实际有效评分日数。
预期 2,189 个预测日，成熟候选 2,168 日，2023 最晚 signal 11 月 30 日、label_end 12 月 29 日；
12 月 1–29 日为 `unscored_development_boundary`。I/O 前验证 role、精确 dates 和 maturity，
Parquet 必须投影和日期 predicate；只读成熟 label，不读跨 2024 的端点。

## 3. 共同样本与报告分母

按日以完整 canonical keys 左连接五臂和 raw label。重复、额外键、错序、缺少完整日、
错误 exit_date 是完整性错误，停止；缺失/非有限 prediction 或 label 用明确计数处理。
主样本为 finite mature label 与五个 finite prediction 的共同交集，至少 100 对。
在同一股票集合上做 average-tie ranks 的 Pearson correlation，即 Spearman Rank IC；
任一列或 label 常数时全五臂该日不可评分，避免六项对比使用不同日期。

保留所有预测日期，包括不可评分日，不删除困难年份；保存 canonical denominator、
maturity、finite label、各臂 finite prediction、common count、common/canonical、
common/finite-label、scoreable 和 reason、common-key hash。主均值为合法 daily IC 等日期平均。
分别报告工程 coverage、成熟标签可用率和共同评分 coverage。95% 原门槛仅作用于每臂每年
工程 prediction coverage；不临时新增共同 coverage 门槛，不据 coverage 改样本。
若任一年无可评分日或工程门槛失败，保留六项记录但总体正式对比 not testable。

## 4. 统计细则：冻结前补齐实现歧义

旧 freeze 规定六项 `S-B,R-B,C-B,H-B,C-R,H-C`、two-sided、alpha .05、single Holm family、
Bartlett HAC20/40、MBB20/40、1000 次、seed 20260909、shared date indices、no noninferiority。
全部原样保留。以下仅补齐尚未数值化的实现规则，先完成合成验证再揭封。

### HAC

旧 `dataset_design.autocorrelations` 会 dropna 压缩日期，不直接复用，也不修改其历史代码。
新增小型纯函数：对原交易日轴（保留 NaN）上 delta 的有效日均值 mu，令
`u_t = I_t * (d_t-mu)`（缺失日 u=0），有效日数 n。

```text
Var(mean) = [sum(u_t^2) + 2 * sum(k=1..L, (1-k/(L+1))*sum(u_t*u_(t-k)))] / n^2
```

使用原交易日 lag、不对每个 lag 重新缩短带宽、不把周末节假日当缺口。
这是截距均值 estimating equation 的 sandwich，采用无小样本修正与正态双侧 p；
无缺口时用独立 dense-kernel oracle 校验。n < 2 或非零常数 delta 的退化方差为
not testable；全零 delta 给 p=1/SE=0。HAC40 仅 sensitivity，不另做 Holm。
统计定义参照 [statsmodels HAC 文档](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)，
该接口本身假定连续等间隔序列，因此不能直接传入删除缺口后的数据。

### MBB

旧 gap-aware helper 不提供共享 indices，且可能丢弃无法成完整块的短片段后仍报告总体 CI；
保留旧实现，新增矩阵共享抽样。块只能在原交易日轴连续 scoreable 片段内，不能跨缺失日。
相邻年度和正常休市不构成缺口；缺少 canonical session 才构成缺口。
从全部合法长度 L 的重叠块均匀抽起点，每次 ceil(n/L) 块，拼接后截取 n 日；
五臂和六项对比共享同一组索引。20/40 各自固定 seed，不择优。
若 n < 2L，或任何有效短片段不能供应完整块，记录 unsupported dates/fraction，
不发布总体 CI，避免静默改变估计对象。输出 percentile 2.5/97.5% CI 及抽样索引 hash；
它是支持性普通 pointwise 区间，不是 Holm simultaneous CI，不产生 bootstrap 显著性家族。

### Holm 与解释

六项 HAC20 p 一次 Holm step-down；not-testable 保留位置，以 p=1 参与校正，显式 no rejection。
使用 [Holm step-down 定义](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html)，
合成 known p-values 校验。结果按六个研究问题报告点估计、不确定性及拒绝与否；
未拒绝不等于等价/无损/非劣。无自动 winner 或新策略选择。

## 5. 交付和运行顺序

1. 先提交本计划，历史冻结文件不变。
2. 实现纯统计函数、严格有界 reader、独立 D3-A contract、不可覆盖揭封标记、access JSONL、
   完成回执和报告生成器。没有 `--arm`、单年、试跑 outcome 或方法配置开关。
3. 合成验证：正负完美相关、ties、99/100、missing masks/common intersection、常数、
   zero/known delta、HAC gaps、MBB 共享索引/块边界/短片段、Holm、年末 maturity、未来读拒绝、
   键损坏、哈希损坏、重复执行和中断证据保护。完整小型模拟五臂九折跑通 publication。
4. Outcome-blind preflight。提交代码/验证/contract 后给用户 PowerShell 命令。
5. 用户一次运行全部五臂九折；首次读 prediction 或 label 数值之前，以 exclusive create
   写入 `OUTCOME_ACCESS_RECEIPT.json` 和全局揭封标记，fsync。回执引用精确日期、标签源/
   prediction/model hashes、code/runtime/Git/授权。失败也永久保留揭封事实和不完整目录。
6. 完成后在单独 `sealed/receipt.json` 绑定所有输出 hash 与初始 access receipt；不能把
   尚不存在的 output hash 伪写入初始回执。初始回执 + 完成回执共同构成完整证据链。
   成功重跑同命令只验证并报告已有封存；失败不自动重开、更换 run-id 绕过或覆盖 evidence。
7. 用户返回“跑完”后只读核验并提交报告，更新 D3-A COMPLETE，立即停止。

正式输出：全轴 daily IC/delta/coverage、five-arm descriptive、annual/era descriptive、
六项 contrasts（HAC20/40 SE/p、Holm、MBB20/40 CI、decision）、bootstrap support、
input provenance、access 日志、REPORT.md。报告逐项 Q1–Q6，包含现有 U/dense missingness
限制和 retrospective 标签。优先清晰表格，本轮不额外生成图或新统计检验。

## 6. 验收与停止点

代码交付不等于已观察结果。实际 outcome 是否打开以 append-only access receipt 为准。
正式运行完成后目标状态：D1 CLOSED / REPRESENTATIONS FROZEN；D2 CLOSED / 45 MODELS
SEALED；D3-A PREDICTION EVALUATION COMPLETE；D3-B / STRATEGY V2 NOT AUTHORIZED；
2024+ NOT ACCESSED。结果不符合预期时如实报告，不修改实验。
