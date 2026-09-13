# E2 历史采集续跑命令

2026-09-14：用户已完成 Quotes，States 在 SH600143 失败，Dividends 被手动停止。所有完成块 hash 已通过，详见 [中断复核](USER_RUN_20260914.md)。不要重跑 Quotes，也不要再使用旧四阶段连贴命令。

现在只执行 States 续跑：

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_baseline'
& .\scripts\resume_e2_hard_history.ps1 -Phase States
```

等看到 `states recovery inventory complete` 后，再单独执行 Dividends：

```powershell
& .\scripts\resume_e2_hard_history.ps1 -Phase Dividends
```

不要一次性粘贴两段。交互式 PowerShell 的前一条命令 throw，不保证停止已经粘贴排队的下一条命令。遇到源错误保留末尾日志；不要循环自动重试或删除 receipt。确认网络恢复后，相同单条命令会复用成功块并为失败处新建 attempt，原记录保持不变。

恢复入口使用 `E:\anaconda_envs\qlib_env\python.exe`。States 需要 BaoStock；Dividends 需要既有环境变量 TUSHARE_TOKEN，命令不显示 token。父目录 full_states 的 118 个完成块、full_dividends 的 5 个完成日期由引用复用，新结果写入 recovery_states_v1 / recovery_dividends_v1。恢复 complete.json 合并引用父结果与新结果，必须同时保留父目录。

日期范围、父 scope、旧采集代码与恢复代码均绑定；完整结束后再次运行会拒绝覆盖。若代码/hash 变化则停止核查，不改旧 scope。原 `close_e2_hard_blockers.ps1 -Phase Validate` 仍可仅运行 61 项 synthetic 检查，恢复测试使用 `python -m pytest -q tests/test_e2_history_recovery.py`。

这些命令只采集历史日终状态和逐 ex-date 分配事件，不读取 prediction/label，不运行 account 或 NAV。既有 Quotes 输出仍是旧换算配方诊断，SH601313 另有认证 overlay；采集完成不能直接交交易引擎。States 日终标记不自动等于盘前可得，Dividends 不覆盖全部 rights/conversion/terminal。

所有阶段完成后仍先做异常、身份与事件闭环，保持 **E2 BLOCKED**，不自动进入 E3/E4。
