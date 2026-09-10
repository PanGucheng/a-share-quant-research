# Literature Representation D2 实施交付

2026-09-11最新状态：**D2 COMPLETE / ALL FIVE ARMS SEALED**。
27模型及独立replay已核验，见[完成报告](COMPLETION_REPORT.md)。下文保留2026-09-10入口交付时记录。

2026-09-10。**D1已正式冻结；D2代码与轻量验证完成，真实27模型待用户运行。**
[执行命令和恢复规则](../../docs/LITERATURE_D2_PRECOMPUTE_RUNBOOK.md)。

## 意见评估及实施取舍

接受附件的R218/C201/H358自然结构、common raw U61、递归稀疏限制、rank minimum100、
family内50%/跨family完整性、economic-axis方向和严格0.995替代门槛。
它们与D1全量审阅一致；本轮没有新correctness blocker证据，也没有进行新的全面公式资格认证。
接受dense variable-node平均的实际含义：22–63桶2010年44.52%的有效输出只用部分lag，
不将其写成固定完整路径。保留range完整family规则的覆盖代价。
六contrasts及Holm/HAC/bootstrap仅冻结声明，不执行evaluator。

采用三处工程细化：

1. 旧candidate/recipe/receipt保持原样，新增[freeze overlay](../literature_factor_representation_d1/freeze_v1/freeze.json)
   和[语义补充](../literature_factor_representation_d1/freeze_v1/semantics.json)正式承接批准。
   D1冻结先以 `d05e7eb` 独立提交并推送，再实施D2。
2. 无跨日期状态的逐日表示缓存可安全共享，构建时与D1输入/输出哈希核对。
   H2023作为正式27模型之一先资格检查；不新增额外候选或超参数试验。
3. 独立naive表示预注册1e-12绝对容差，预测score要求exact。若失败则停止，不能把表示近似一致冒充预测exact。

## 实现与验证

复用原V3训练数值组件，新增表示缓存、不可变原子单元、fold/date门禁、身份合同及独立重放。
每月训练keys/hash/count与B/S两者匹配才fit。B/S只读取工程metadata，不读取封存分数。
独立路径禁用生产composite/predict和label读取后仍能完成synthetic saved-model重放。

- 53项定向测试通过：D2新增10项（含参数化），D1 38项、V3 precompute 5项。
- 合成H358、1600训练行、固定100轮float64 Sequence，保存模型后独立逐值prediction replay exact。
- synthetic score被修改后，即使测试故意重算文件checksum，独立数值replay仍检测失败。
- 覆盖未来日期、错fold role、列序/config/caveat改变、残留stage、坏hash、幂等完成跳过、缓存列序/数值与同日因果性。
- Ruff通过；PowerShell实际metadata preflight通过，未启动长任务。
- [真实有界feature canary](bounded_feature_canary.json)：2023-12合法切片42,000行与D1证据一致；
  仅重建2023-12-29的2,000行，三个arm哈希精确匹配D1，独立表示最大差2.78e-16。
  耗时12.88秒、峰值RSS约937 MiB，真实模型拟合数为0。这不是整折资源资格结果。

没有运行全仓full validators，因为其中历史研究流程会读取本轮禁止的outcome/近期证据。
未修改V3权威、B/S模型/回执、canonical数据、旧计划快照或D1诊断packet。

## 待用户运行及最终报告

真实表示缓存0个月，真实R/C/H模型0/27，真实年度独立replay0/27（交付时）。
完整最大折资源尚未实测；正式入口先H2023→replay→资源门禁，再进入余下单元。
真实最终报告将在用户运行后依据 `sealed/folds.csv` 与全部模型/重放回执核验，
报告各折counts/coverage/hash/resource和失败记录，不能预先填入成功状态。

D1 CLOSED / REPRESENTATIONS FROZEN；D2 USER RUN PENDING。
OUTCOME EVALUATION NOT AUTHORIZED；POOL COMPARISON NOT AUTHORIZED；2024+ NOT ACCESSED。
