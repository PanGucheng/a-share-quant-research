# Research Protocol V3-MVP 审阅与重算进度

状态：`RECOMPUTED / POSTRUN VERIFIED / STOP FOR HUMAN REVIEW`。用户要求的工程重算与运行后验证已完成。
旧宽表声明保持撤回，新结果以最终报告及新审阅结论为准。详见[逐提交审阅](AUDIT_20260909.md)及
[机器证据](REVALIDATION_EVIDENCE_20260909.json)。原始输出和回执全部保留。

## 已完成

- 审阅3个提交、14个原改动文件，恢复严格回执、float64分批路径及真正的OOF隔离测试。
- 独立目录完整重算P0/P1、两折8列canary、两折494列资源测试及计数复核。
- 运行后重新验证23个单元、358个文件、480个canonical分区、6106个价格文件；90张新旧表精确一致。
- 四个保存模型共1,943,838条预测已从canonical特征重新计算并精确核对。
- 两折494列采样峰值RSS为2.60/4.55GiB，预测覆盖均100%；固定100轮、8线程。
- fast 46、full pytest 585、26个validators、Qlib 6通过；详见[最终报告](REPORT.md)。

## 当前边界

本轮工程重算与验证已完成。旧宽表资格仍撤回，原回执/status/resource不改写。
以[新审阅结论](REVALIDATION_CLOSEOUT_20260909.json)解释原产物的pending-review状态。
P3四池竞争、近期重放及Strategy V2仍未授权；本轮不再要求重跑完整任务。

## 已执行的外部重算命令（留作复现）

```powershell
Set-Location E:\qlib_prj\qlib_baseline
& .\scripts\recompute_research_protocol_v3.ps1 -RunId v3_recompute_audit_20260909_v1 -Workers 2
```

脚本依次运行：真实小批probe（已完成则严格校验后复用本次新结果）、P0/P1/两折8列P2、
2015宽表、2023宽表、独立计数及回执复核。完整P1和模型均从本次新代码/源数据重新计算，
不复用旧v3_mvp或wide目录的标签、资格、模型或预测。

- 日志：`tmp/v3_recompute_audit_20260909_v1-<阶段>.log`，追加保存。
- 输出：`outputs/research_protocol_v3_mvp/v3_recompute_audit_20260909_v1/`。
- 状态：上述目录的`status.json`；最终独立复核结果在`revalidation_verify_summary/result.json`。
- 失败立即停止。保留所有临时目录；同代码/配置/环境再次执行同一命令，只复用严格验证通过的完成单元。
- 合同不匹配或已发布单元损坏时停止诊断，不能删除回执或改hash续跑；代码改变须新run-id并重新计算。
- 宽表按月保留float64块，首折与末折合计原始特征约29GiB，另需审计、模型和预测空间。
  本轮检查E盘约84GiB可用；运行前仍需检查空间。单个fit使用8线程，fit之间串行，默认2个年度审计进程。
- 本轮宽表单元总耗时为首折约12.6分钟、最大折约30.0分钟；12GiB RSS预算是审阅标记，并非内存硬限制。
- 用户关闭Codex不会终止自己启动的PowerShell进程；关闭该终端或关机会终止计算。

用户已授权验证后提交推送；提交位于独立审阅分支，不改写main历史。
脚本不会宣布P3就绪，也不计算模型收益或选择winner。
