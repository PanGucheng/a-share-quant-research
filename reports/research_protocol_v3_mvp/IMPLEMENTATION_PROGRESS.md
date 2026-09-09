# Research Protocol V3-MVP P0–P2 实施进度

用户于2026-09-09授权实施[正式计划](../../docs/RESEARCH_PROTOCOL_V3_MVP_PLAN.md)的P0–P2。本文件为会话恢复入口。未授权P3四池竞争、近期重放或Strategy V2。

## 当前实施范围

- P0：独立年度生成器及精确逐日角色表；2015–2023九折、2,189个预测日、2,168个日历成熟评价日。
- P1：765项物理合格因子的训练期可估计性，分年分批读取；精确成熟标签计数。Broad494、Strict332仅作已知身份诊断，Baseline与Human池未冻结。
- P2：固定LightGBM 4.6.0、100轮、8线程、NaN原生输入；首折/末折完整训练跨度的固定8列工程canary。无OOF标签、IC、收益、importance或选参反馈。

本机内存约28GiB，实施开始时空闲约9GiB。494列最大折原始数组约22.5GiB，完整全宽训练资源资格暂不声明；8列canary不冒充494列压力测试。

## 恢复与运行

运行目录：`outputs/research_protocol_v3_mvp/v3_mvp_20260909_v2/`。`contract.json`绑定代码、配置、canonical元数据、价格源和上游冻结证据hash。每年审计与每个canary独立原子发布，已完成分片验证receipt后复用；代码变化必须使用新run-id，不混入旧结果。

以下入口已实现，后续以最终报告记录的合格run-id为准：

```powershell
Set-Location E:\qlib_prj\qlib_baseline
& E:\anaconda_envs\qlib_env\python.exe -u scripts/run_research_protocol_v3_mvp.py --run-id v3_mvp_20260909_v2 --stage prepare
& E:\anaconda_envs\qlib_env\python.exe -u scripts/run_research_protocol_v3_mvp.py --run-id v3_mvp_20260909_v2 --stage audit --workers 4
& E:\anaconda_envs\qlib_env\python.exe -u scripts/run_research_protocol_v3_mvp.py --run-id v3_mvp_20260909_v2 --stage canary
& E:\anaconda_envs\qlib_env\python.exe -u scripts/run_research_protocol_v3_mvp.py --run-id v3_mvp_20260909_v2 --stage finalize
```

状态文件为该运行目录中的`status.json`；本轮临时日志为`tmp/research_protocol_v3_v2.log`和`tmp/research_protocol_v3_full_final.log`。中断的未发布临时目录保留作诊断，重跑只重新计算未完成单元，不将部分文件标记为完成。

初始单进程试跑`v3_mvp_20260909`在首年审计期间主动停止，改为四年度并行后使用独立`_v2`运行绑定；旧临时分片未作为新版本证据复用。模型canary并发数始终为1，Qlib每个审计worker的kernels=1。

## 交付记录

P0–P2已完成。13项V3针对性测试通过；P0九折日期与独立审计一致；P1已完成14个年份、765项因子分批feature-only审计和成熟标签计数。每折训练日有限标签均无少于100对的日期；P1诊断中物理765/Primary工作集494/Strict 3-of-3为765/494/332，Baseline与Human池仍未冻结。

P2两项固定8列工程canary均通过100轮、annual fit、整年/按月预测一致性、原生NaN与8线程执行：2015 fit 2,090,742行、peak RSS约622MiB、fit约2.1s；2023 fit 5,788,028行、peak RSS约1,111MiB、fit约5.3s。2015 canary预测覆盖94.8786%（因选定ATR/早期列缺失），低于95%提示阈值，2023为99.9934%；因此完整池的资源资格与模型池可用性保持 blocker，不能据此启动P3。

完整检查：V3 targeted 13、fast 46、full 575、Qlib 6全部通过（保留既有warnings）。最终运行状态为`p0_p2_complete_stop_for_review`，`protocol_ready=true`、`pool_experiment_ready=false`、`full_width_resource_qualified=false`；未读取近期值，未计算IC/收益/importance，未启动竞争。
