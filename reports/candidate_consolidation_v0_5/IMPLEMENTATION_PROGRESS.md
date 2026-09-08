# Candidate Consolidation V0.5 实施进度

2026-09-08用户授权开始实施；本文件为后续会话恢复入口。

## 最新状态：代表提案已交付，停止供人工审阅

用户已完成全量计算：168/168个月份、3382日，墙钟3735.6秒（约62分钟）。本轮逐hash验证全部日证据，完成121,771 pairs的Full、A/B/C/D、LOO_A/B/C/D共9个精确统计视图，汇总用时约16.2分钟；未重算Primary或全量日Spearman。

已生成[代表提案报告](REPORT.md)及[494行代表提案表](representative_proposal_board.csv)、[765行语义审阅](economic_semantic_review.csv)、[精确重复关系](exact_alias_map.csv)。四个相似度等级.995/.95/.85/.70的Full complete簇数分别390/202/132/89，不把任一数字解释为最终入池数量。全期精确重复有5组10成员，均为Alpha158与Alpha360对应项；该数字仅针对494工作集，不能与初始765语义库存中的8对表达式线索直接比较。

五个canonical风险controls的Full/四Era注释共12,350行；包含自比较身份标记，不把自相关当风险发现。10个距离视图（含保守Stable）及完整SciPy linkage、局部average对照、跨Era/LOO稳定性、cluster风险汇总、四层级pair状态和代表排序明细保存在 `outputs/candidate_consolidation_v0_5/consolidation_20260908_v2/proposal_v1/`。

所有层级均有35项因子因语义/状态mask问题暂缓；窗口或机制不同的成员保留身份。代表政策在解释聚类输出前写入[政策文件](REPRESENTATIVE_POLICY.json)，没有使用IC、收益或模型表现。`representation_sign`只描述特征相对表示的全期符号，不修改Primary方向，也不自动授权替换。完整语义表属于规则辅助审阅，仍需用户审阅，不冒充专家逐项签字。

**明确缺项**：价格暴露未计算，因为尚未验证该community-derived provider的价格单位和归一化溯源。审计本机Qlib `scripts/data_collector/yahoo/collector.py::_manual_adj_data` 可见按单只股票首日close归一化的实现，说明不能仅凭字段名把provider close当作横截面名义价格；这不是对当前provider处理链的证明。因此本次保持unavailable，而不加入意义未确认的control。行业仍缺少开发期覆盖。两项作为提案限制保留，不用近期值回填。

验收：[PROPOSAL_VALIDATION.json](PROPOSAL_VALIDATION.json)。555项完整测试、46项fast测试、26个验证器通过；独立pandas复核真实pair的全期中位数/分位数通过；所有层级complete簇内最大距离满足cut，494/765成员不丢失，12,350暴露行及整数样本计数schema通过；[产物receipt](PROPOSAL_RECEIPT.json)绑定报告和runtime文件hash。原Primary20份冻结文件逐hash不变。

后续停止在人工审阅，不自动进入Core、组合、10D、近期诊断、模型或Strategy V2。下列初期进度和全量命令保留为执行历史；**本次全量已完成，无需重跑**。

## P0/P1初期交付范围（历史）

- 固定774库存、765研究可用、494 active；通过原Primary Board hash与20份冻结文件hash验证输入。
- 774行语义基础表采用既有map白名单列，补价格斜率、历史/当前价格比、二元事件注释。其余继承语义仍标需复核，不能声称765项人工语义审阅已全部完成。
- 同一天多列有界parquet读取，先求日期交集，再读取；各因子键必须完全相同，缺失分区/重复键/日期越界失败。
- 共享 `factor_similarity.py` 精确Spearman内核：SciPy average ranks、交集mask分组矩阵计算；pandas作为精确对照。旧日相关入口保持原行为。
- SciPy聚类wrapper的V0.5适配：排序轴、成员hash身份、singleton、complete未知距离、average局部完整矩阵限制。
- 新独立runner：固定12日canary、1/8进程、月分片、OS锁、原子发布、receipt校验、恢复与状态输出。
- 日证据包含rho、共同样本数、缺失原因、各因子finite/inf计数、每日universe规模、读取slice hash及当次日期范围内exact alias。局部alias不等于全期可替代关系。

## P0/P1交付时的后续工作（现已推进，缺项见上）

本轮入口的 `full` 只执行开发期全量**日证据**，不声称整个V0.5完成。之后还需P2的Full/Era精确分块汇总，P3的跨Era/LOO稳定性、数值簇与经济/暴露解释，以及P4的全部494行label-free代表提案。价格control的复权/单位审计尚待完成；行业仍为开发期不可用。五个既有canonical controls已加入同一个内核；control_only不扩大494工作集。

原Primary、Candidate Rule、765库存身份保留；未运行10D、2024+数值、IC重筛、模型、组合或自动Core。原开发计划中的P4人工停止点继续有效。

## 验证与运行

合格run-id：`consolidation_20260908_v2`。真实canary已通过：四Era各取首/中/末交易日，共12日，每日全494列（五个controls均已在active内）。日期及证据见 [CANARY.json](CANARY.json)、[P1_VALIDATION.json](P1_VALIDATION.json)。全量必须匹配该run的代码/输入/配置hash，并已通过canary；代码变化应使用新run-id重新验证，不混用旧receipt。

| 检查 / 校准 | 结果 |
|---|---|
| pandas精确对照 | 最大绝对误差4.44e-16，小于1e-12容差；缺失原因一致 |
| 1/8进程 | 72对日数组文件SHA256完全相同，含rho、共同样本、原因、finite/inf数与universe数 |
| canary墙钟 | 单进程485秒、8进程118秒；含每个日期额外pandas oracle，非全量耗时 |
| grouped内核 / pandas oracle | 单进程12日累计81.8 / 342.2秒；全量只运行已合格grouped内核 |
| 内存 | 单日最大采样RSS约456MiB；2023-12整月reader+alias校准约926MiB，8份外推约7.2GiB |
| 单月读取 | 21日、42,000行、494列约12.5秒；这次只校准读取与alias内存，没有运行额外整月全对计算 |
| 测试 | fast 46项；full 552项及26个验证器全部通过；包含进程被终止后的锁释放/未发布分片重算、损坏receipt拒绝、未来边界与outcome隔离 |
| 冻结保护 | 原Primary清单20份文件逐hash保持一致 |

8进程实测内核工作量线性摊销的理想值约0.95小时，加上月度I/O、调度、落盘和非均匀工作量，先为全量日证据预留**1–3小时**。单进程canary期间同时执行了仓库检查，12日期也不构成精确运行时预测；全量进度可进一步校准。内存数字为采样与外推，不声称已实测8个完整月份同时驻留的总峰值。

工作集和语义基础表分别见 [working_set.csv](working_set.csv) 与 [inventory_semantic_audit.csv](inventory_semantic_audit.csv)。后者明确保留继承语义待复核状态，不以表格生成代替完整语义审计。

## 外部PowerShell命令

从用户自己的PowerShell运行以下命令；该进程由该终端持有。保持终端运行。发生中断时重复同一命令，已完成月份会逐hash验证后跳过；当前未发布月份重新计算。

```powershell
Set-Location E:\qlib_prj\qlib_baseline
New-Item -ItemType Directory -Force tmp | Out-Null
& E:\anaconda_envs\qlib_env\python.exe -u scripts/run_candidate_consolidation_v0_5.py --run-id consolidation_20260908_v2 --stage full --workers 8 2>&1 | Tee-Object -FilePath tmp/candidate_consolidation_20260908_v2.log -Append
```

查看进度：

```powershell
Get-Content E:\qlib_prj\qlib_baseline\outputs\candidate_consolidation_v0_5\consolidation_20260908_v2\daily\status.json
```

全量有168个月份任务、3382个交易日、121,771个pair。完成时根目录 `status.json` 为 `daily_evidence_complete_aggregation_pending`；这时继续P2汇总与P3/P4，不重新运行Primary。完整的日证据保存在该run的 `daily/<month>/`；不提交大型数组到Git。`--stage prepare`可只验证输入与当前合同，`--stage canary`可独立恢复未完成canary；正式全量命令不会重复运行oracle。运行前要求至少50GiB磁盘余量，当前已检查足够。

早期试验 `consolidation_20260908` 在真实114种mask的首日发现保守auto路径选用pandas耗时较高，随后停止；其分片仅为试验证据。单独同日grouped对照约6.64秒，与已有pandas结果在1e-12容差内一致。正式验证切换为grouped并使用独立run-id，早期分片不用于正式恢复。
