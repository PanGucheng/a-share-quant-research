# D3-A 执行说明

状态：**IMPLEMENTED / OUTCOME UNOPENED / USER RUN PENDING**。
按[实施计划](LITERATURE_D3A_FROZEN_PREDICTION_EVALUATION_PLAN.md)，仅执行冻结五臂的
2015–2023 mature prediction evaluation。45 个模型不重训、不重放、不改表示。
当前交付不是正式效果报告。

## 执行

在 PowerShell 中运行：

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_baseline'
& .\scripts\evaluate_literature_d3a.ps1
```

此命令先运行纯合成测试、校验冻结执行契约及全部输入哈希，再一次性评价五臂九折。
测试失败或 preflight 失败会在打开 outcome 前停止。没有单臂、单年、方法扫描参数。
默认 run-id 为 `d3a_five_arm_20260911_v1`。

如果只想先检查完整性：

```powershell
& .\scripts\evaluate_literature_d3a.ps1 -Preflight
```

`-Preflight` 只解释元数据和模型身份，数据文件只作字节哈希；不读取 prediction/label
数值，也不创建揭封回执。执行环境继续使用 `E:\anaconda_envs\qlib_env\python.exe`。
本轮真实 preflight 已核验 45 个模型、252 份源 receipt，预测日 2,189，成熟候选日 2,168；
实际 common scoreable dates 留待运行结果确定。

正式评价按年度读取五份 predictions 和已审计的 keys/labels 缓存，然后做每日共同样本
Spearman、六项 HAC/Holm 和共享索引 MBB，不读取 canonical 特征或 provider 价格。
无需 D2 规模的训练临时盘。正式墙钟和峰值尚未实测，不能用合成测试时间推算；
日志逐年显示进度，不在中途显示 IC 供选择。

## 输出与揭封记录

- 执行契约：[execution_v1/contract.json](../reports/literature_factor_representation_d3a/execution_v1/contract.json)。
- 首次打开标记：`reports/literature_factor_representation_d3a/OUTCOME_OPENED.json`。
- 运行根：`outputs/literature_factor_representation_d3a/d3a_five_arm_20260911_v1`。
- 初始回执：运行根的 `OUTCOME_ACCESS_RECEIPT.json`，在首次数值读取前 exclusive-create/fsync。
- 完成结果：运行根 `sealed/`，含 daily/contrasts/descriptive CSV、bootstrap support、
  REPORT.md、contract、access JSONL、初始回执副本及文件哈希 receipt。
- 提交用副本：`reports/literature_factor_representation_d3a/completion_v1/`，完整复制封存的小型结果。
- 日志：`outputs/literature_factor_representation_d3a_logs/`，每次新文件。

初始回执记录授权、时间、Git、五臂/model/prediction/source/code/runtime hashes、
exact dates 与 maturity cutoff；最终 output hashes 在完成 receipt 中与它绑定。
初始回执不可因尚未完成而补写或覆盖。

## 中断、重复与停止

若在首次揭封后失败，保留 marker、回执、failure.json 与 `.sealed.incomplete`。
**不要删除它们，不要更换 run-id 重开，不要自行改规则重跑。** 把日志和错误交回当前任务诊断。
marker 保守地在读取前建立，即使读取前立即失败，也不恢复为 outcome-blind 状态。

成功后重复相同命令只做合成测试/完整性核验并返回 `already_complete_verified`，不再计算真实结果。
如果仅最终报告副本复制失败，保留不完整副本并诊断；不重新评价。

跑完后回复“跑完了”。随后核验/提交正式报告，状态改为 D3-A COMPLETE 并停止。
没有等价/非劣检验；年度/Era 是描述；不自动选 winner、改模型或进入 portfolio。
D3-B、Strategy V2 与 2024+ 研究值始终不在本轮授权内。
