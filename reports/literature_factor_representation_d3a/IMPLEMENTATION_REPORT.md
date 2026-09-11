# D3-A 实现交付

2026-09-11：**IMPLEMENTED / OUTCOME UNOPENED / USER RUN PENDING**。
[计划](../../docs/LITERATURE_D3A_FROZEN_PREDICTION_EVALUATION_PLAN.md)先以 `2ab2456` 提交，随后实施。
用户新授权限于五臂冻结预测的成熟开发期评价；长执行仍由用户自行运行。
[PowerShell 入口与失败处理](../../docs/LITERATURE_D3A_EVALUATION_RUNBOOK.md)。

## 采纳与调整

保留附件的五臂共同样本、六项 paired delta、HAC20 + single Holm、HAC40/MBB20/40
支持性区间、开发边界及揭封后停止要求。没有修改原 D1/D2 freeze、表示、模型或 evaluation contract。
独立 D3-A contract 作为本次授权 overlay，旧 `outcomes_authorized=false` 历史记录保持不变。

补齐 outcome 打开前的实现细则：HAC 使用完整交易日轴上的截距 sandwich / n²；
MBB 对五臂/六对比共用抽样 indices，短片段无法提供完整块则不发布总体 CI；
不可检验对比保持六项 family，以 p=1 参与 Holm，明确 no rejection。
初始 access receipt 与最终 output hash receipt 分开，因为打开前不存在结果哈希。

## 复用与新增

复用 V3 calendar/role/maturity、float64 身份和已审计 label/keys 缓存、D1 freeze check、
D2 completion receipts、canonical metadata、hash/provenance。没有调用旧 broad context loader，
没有重新生成 label，也没有访问特征、价格、近期数据或历史 outcome 结果表。

新增 [纯统计模块](../../research_validation/frozen_prediction_statistics.py)、
[有界 evaluator](../../model_research/frozen_prediction_evaluation.py)、
[CLI](../../scripts/evaluate_literature_d3a.py)、[PowerShell](../../scripts/evaluate_literature_d3a.ps1) 和
[合成测试](../../tests/test_frozen_prediction_d3a.py)。
旧 HAC/dropna 与 bootstrap 实现被其他历史契约引用，保持原样；新模块解决当前缺口和共享样本问题。

## 验证口径

合成验证覆盖正/负 Spearman、ties、99/100、各臂不同缺失 mask、共同交集、常数、
zero/known delta、HAC dense-kernel oracle 与正态 p、Holm known values、共享 bootstrap
indices/块边界/短片段、V3 t+21 maturity、未来日期 I/O 前拒绝、损坏键/exit/hash、
完整合成五臂九折 publication、重复执行和失败后保留揭封记录。
具体测试数量和 preflight 结果见 [VALIDATION.json](VALIDATION.json)。

真实 preflight 只读完整性验证：45 模型/预测、all-nine exact replay、168 个表示缓存、
252 份源 receipts，模型序列化 SHA 与文件字节 SHA 分别核对；两种 hash 的定义不能混用。
日历成熟候选 2,168/2,189，2023-11-30 signal / 2023-12-29 exit。
它不证明实际 scoreable dates、IC 或显著性；这些仍未计算。

所有真实 prediction/label 数值读取都留给用户正式命令。输出将回答六个预注册问题，
不自动宣布 winner，不把未拒绝解释为等价/无损，不做组合、SHAP、调参或 2024+ 访问。
