# D3-A 完成审阅

2026-09-11：**D3-A PREDICTION EVALUATION COMPLETE / VERIFIED / STOP FOR HUMAN REVIEW**。
用户运行完成，本轮核验通过，无需重跑。

六项预注册对比均未拒绝零差异。当前证据没有确立任一表示的增量优势；
未拒绝也不能解释为等价、非劣或无损压缩。D1/D2 不变，不据结果调整表示或模型。

## 主要结果

| 对比 | 平均 paired daily IC delta | HAC20 p | Holm p | 正式判断 |
|---|---:|---:|---:|---|
| S−B | −0.005393 | 0.059025 | 0.354150 | 未检出差异 |
| R−B | +0.000899 | 0.088036 | 0.440181 | 未检出差异 |
| C−B | −0.002878 | 0.658179 | 1.000000 | 未检出差异 |
| H−B | +0.001369 | 0.780211 | 1.000000 | 未检出差异 |
| C−R | −0.003777 | 0.557023 | 1.000000 | 未检出差异 |
| H−C | +0.004247 | 0.134737 | 0.538948 | 未检出差异 |

HAC40 双侧 p 均大于 .05；MBB20/40 的六项普通 percentile 区间均含零。
两种长度均有完整支持：2,168 个连续可评分交易日，无内部缺失片段，
合法块数分别为2,149和2,129；共享抽样索引哈希与封存结果一致。
MBB 区间不是 Holm-adjusted simultaneous CI，不另作新的检验家族。

| 表示 | 列数 | mean daily Rank IC |
|---|---:|---:|
| Broad B | 494 | 0.139079 |
| Strict S | 332 | 0.133686 |
| Representative R | 218 | 0.139978 |
| Composite C | 201 | 0.136201 |
| Hybrid H | 358 | 0.140448 |

R 和 H 相对 B 的正点估计不足以确立改善；C/S 的负点估计也未达到正式校正后的拒绝标准。
H−C 的正点估计未确立加入 raw representatives 的增量。研究结论保留这六项实验结构，
不把均值大小顺序升级为 winner、生产候选或经济优劣。

## 样本与覆盖

2,189 个完整预测日中，2,168 个日历成熟候选日全部达到共同样本至少100对且可计算 IC。
2023-12-01 至2023-12-29共21日、42,000个键保留为 `unscored_development_boundary`，
没有读取这些 signal 的未成熟 label。合法成熟末日为2023-11-30，exit为2023-12-29。

成熟候选日期有4,335,824个 canonical keys，五臂共同有限标签/预测样本4,144,939对，
pooled成熟共同覆盖95.5975%。五臂工程预测覆盖均100%，因此共同样本损失来自有限标签可用性，
本次并未通过按臂使用不同样本来形成 IC 差异。
2015年共同覆盖仅82.9325%，2016年91.1244%，2017年92.8803%；这些年份仍完整保留。
不据这些数值新加 coverage 过滤或修改标签。详细年度/Era统计只作描述。

## 完整性与核验范围

- 实际运行代码：`15da7e27d64e4afeb06c0c711ffbad6316fe0741`。
- 揭封时间：2026-09-11 02:25:42 UTC（北京时间10:25:42）。
- 执行契约：`57da47d77dbd5efba627020fdc57fdfacd1173394a411d2f7f4f7ed889f94212`。
- 45个模型与prediction、all-nine independent replay、252份源receipts重新校验通过。
- 初始marker、access receipt、运行sealed和提交副本的文件哈希及契约完全匹配。
- 63次读取/126条request-complete事件的path、columns、exact dates、role、source hash、
  行数与契约一致，只有合法keys、五臂prediction及成熟label；没有feature/price/2024+访问事件。
- 基于已封存 daily aggregate 重建 contrasts/descriptive/REPORT 字节完全一致；
  MBB区间/support/共享indices哈希一致；另以原交易日位置的dense-kernel sandwich和独立Holm
  step-down复算，HAC20/40 SE、p及校正值通过核验。
- 本轮没有重新读入原始 prediction/label 数值配对，也没有重新计算横截面IC。
  原始配对计算来自用户正式运行，合成独立Spearman oracle是揭封前已有验证。

评价封存单元计时20.11秒，不含命令前置测试、preflight和最终副本复制；不将它写成端到端耗时。
未发现failure.json或incomplete目录。原有58项交付测试保持有效，本轮新增只读审阅脚本已实际执行且lint通过。

证据：[原始正式报告](completion_v1/REPORT.md)、[六项精确结果](completion_v1/contrasts.csv)、
[访问回执](completion_v1/OUTCOME_ACCESS_RECEIPT.json)、[完成receipt](completion_v1/receipt.json)、
[独立审阅记录](POSTRUN_VERIFICATION.json)、[审阅脚本](../../scripts/review_literature_d3a_completion.py)。
原封存文件保持原字节，本审阅是单独附加文档。

## 研究边界

这是 retrospective pseudo-OOS development evidence。因子池发现及表示设计的回顾性范围未改变，
年度 past-only purged fit 不消除前序发现偏差；不是 fresh untouched OOS 或无偏最终估计。
U61的语义/质量限制、dense variable-node composition和跨family全可用要求保留。

D1 CLOSED / REPRESENTATIONS FROZEN；D2 CLOSED / ALL FIVE ARMS SEALED；D3-A COMPLETE。
已揭封事实永久保留，后续表示改动必须标为 post-outcome research。
D3-B、portfolio、SHAP、调参、Strategy V2和2024+研究值未授权，停止等待人工审阅。
