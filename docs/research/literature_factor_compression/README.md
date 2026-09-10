# 研究规划的结构审计附件

对应 [正式研究计划](../../LITERATURE_GROUNDED_FACTOR_COMPRESSION_PLAN.md)。
这里的文件是文档附件，不是 runner 输入、正式因子池或已批准的选择结果。

- [STRUCTURAL_INVENTORY_494.csv](STRUCTURAL_INVENTORY_494.csv)：494 个冻结 Broad 成员，
  保留来源、完整语义摘要、真实窗口/单位、已有质量摘要、hold、精确重复和历史 cluster 索引。
- [AUDIT_METADATA.json](AUDIT_METADATA.json)：来源文件和本地论文的 SHA-256、汇总计数、
  已封存预计算的状态快照及本轮验证限制。

`existing_family`、`existing_mechanism` 来自 V0.5.1，不是新的文献 taxonomy。
`legacy_cluster_*` 来自旧 Full 统计分组，不能直接作本轮替代资格。
`measurement_type` 暂复用单位分类；细分操作符和 availability 的逐列映射尚待 D1。
所有 `proposed_*`、新臂 eligibility/role 和 direction 字段中的 pending 均是有意保留的待审核状态。
不可把这些占位值转换成默认同组、默认正向或默认纳入。

覆盖率限于已有 2010-01-29 至 2023-12-29 feature-only 摘要；未新增值扫描。
B/S 的 folds/rows/exact 仅来自已有重放结果 JSON；本轮未重新训练或 replay。
文件没有 IC、收益、importance、SHAP、prediction score、Primary analysis_direction 等设计污染列。

来源 CSV 按 factor 主键连接；494 个身份唯一且与既有 Broad 合同一致。
审计快照绑定 `main@47ad9f4`。论文 PDF 仍在用户的本地 `paper` 目录，不随文档提交。
`source_file_sha256` 和 `inventory_sha256` 记录本机读取到的原始字节；
Git checkout 可能转换文本换行，清单跨平台验证使用只将 CRLF 还原为 LF 的 `inventory_sha256_lf`。
不得用换行规范化去接受未知的数值或语义修改；旧研究回执仍遵守各自原始合同。
该目录的产物不允许被解释为正式 freeze 或任何后续实验的自动授权。
