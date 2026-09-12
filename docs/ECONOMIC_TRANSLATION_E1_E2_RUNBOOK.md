# Economic Translation E1 / E2 运行说明

2026-09-12：用户已完成本运行，封存与独立重放复核通过，**无需重跑**。见 [完成复核](../reports/economic_translation_mvp/e1_completion_v1/REPORT.md)。以下命令作为既有执行记录保留；E2阻塞、E3/E4未授权。

本阶段授权：E1 B494 prediction-only 结构与 E2 execution/data readiness。
E3/E4、真实NAV/收益比较、2024+、Strategy V2关闭。当前报告见 [E1/E2交付](../reports/economic_translation_mvp/REPORT.md)。

## 用户需要执行的唯一长运行

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_baseline'
& .\scripts\study_economic_e1.ps1
```

默认解释器 `E:\anaconda_envs\qlib_env\python.exe`；需要指定时：

```powershell
& .\scripts\study_economic_e1.ps1 -Python 'E:\anaconda_envs\qlib_env\python.exe'
```

顺序是 E1 synthetic checks → 九年 B494 结构扫描 → 独立重放。脚本遇错误立即停止。
没有行情/label参数、训练入口、收益评价入口或 buffer grid；E1 reader 固定 B/keys路径与列。
无论运行是否成功，都不启动 E3/E4。耗时未在真实九年输入上测定，不承诺预计时长。

输出目录 `outputs/economic_translation_mvp/e1_b494_v1/`：

- `REPORT.md`、`summary.csv`、`structural_review.json`：固定结构报告及待审议结论；
- `daily/rank_lags/membership/migration/turnover/ages/spells.parquet`：可重放细节；turnover文件内只有成员代理；
- `started.json`、`access.json`、`receipt.json`：代码/版本/输入绑定与访问、封存证据；
- `independent_replay.json`：独立重放结果；只有它通过后才可称 E1 COMPLETE / PREDICTION STRUCTURE VERIFIED。

完成日志应出现：`E1 COMPLETE / PREDICTION STRUCTURE VERIFIED. E3/E4 NOT AUTHORIZED.`
这不代表10/20已冻结，也不证明alpha decay或经济收益。

## 失败、复核与停止

如输出目录存在但无 complete receipt，脚本拒绝重建；保留 failure/started/已写输出，交给后续诊断。
不要删除目录、改输入hash或换run_id绕过失败。代码绑定变化也会停止，需要解释修复并保留旧证据。
完整输出再次执行不会重算主研究；先验既有seal，再独立重放。仅复核可运行：

```powershell
& 'E:\anaconda_envs\qlib_env\python.exe' -X utf8 .\scripts\study_economic_e1.py --verify
```

E2 的短真实 quote-unit canary 已执行并留存 [证据](../reports/economic_translation_mvp/quote_unit_canary.csv)。
不需要用户再次运行 `audit_economic_e2_data.py`；该入口固定输出目录、拒绝覆盖。
它不下载新数据，不拼接B分数，也不生成benchmark/策略NAV。

E2当前 **BLOCKED BY EXECUTION / DATA GAP**，详见 [执行合同](../reports/economic_translation_mvp/EXECUTION_CONTRACT.md)。
本次E1成功以后仍需审阅这些真实缺口，不允许以测试通过为理由进入正式组合评价。
