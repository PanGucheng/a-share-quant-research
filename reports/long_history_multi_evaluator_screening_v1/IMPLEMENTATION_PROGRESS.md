# Long-History Multi-Evaluator MVP：实施进度

状态：**IMPLEMENTING；Primary V0 尚未完成**。用户于 2026-09-07 明确授权按计划实施。
实施基线：`f951f55c3626919b6c0e5cf94ff540d7bcb71358`（已核对远端 main）。

## 已实现

- 新增 [配置](../../configs/long_history_multi_evaluator_screening_v1.yaml)、[受限输入及原生评价模块](../../factor_research/long_history_screening.py)、[CLI](../../scripts/run_long_history_multi_evaluator_screening_v1.py)。
- 校验 canonical identity、774/765 库存、语义连续性、分区交接和路径；只继承资格清单，不把历史 coverage 或方向用于选择。全部大分区尚未重新逐字节认证。
- 读取前收窄 effective dates；拒绝 2024+ 请求、归一化后重复 keys、空数据和超界价格。价格为配置 provider 的 `$close`，转换 float64 后按精确交易日计算 T+1 close→T+21 close，不填充缺价。
- IC 与五分桶样本分别构造。ties 无法形成五桶时保留可定义的 IC。50 样本为可定义性下限；primary 不依赖 10D。
- 调用三套原生日 Rank IC，以及 Alphalens 分桶收益、jqfactor factor_returns、Qlib Pearson/long-short。Alphalens 插入的非交易日空值仅在 parity 比较时去除，原输出保留。
- jqfactor 在 pandas 2 下的 `groupby.apply` 重复 date 层已复现。兼容函数仅将原函数的权重分组改为 `group_keys=False`，保留原算术及源码 hash，不改参考仓库文件；正/负相关 synthetic oracle 验证收益公式。
- 原生日序列的 full/annual/signal-era 汇总保留最大标签退出日；FDR 接口绑定完整 765 家族，恢复交易日缺口后复用 gap-aware bootstrap 与 BH/BY。两者尚未构成真实全量 Board。

## 实际运行

运行数据在 ignored `outputs/long_history_multi_evaluator_screening_v1/`；每次使用新 run_id，不覆盖历史产物。

| Run ID | 目的与结果 |
| --- | --- |
| `initial_20260907` | 首次最小 smoke；暴露 Alphalens 日历补空导致的日期索引差异，保留失败 |
| `smoke_calendar_fix_20260907` | 6 因子交易日 IC parity 通过；jqfactor 原生 factor_returns 重复 date 层失败，保留原始错误 |
| `initial_native_pass_20260907` | 6 因子×60 日×3 backend 全部通过，顺序重跑 exact；总耗时约 41.4 秒 |
| `extended_eras_20260907` | 已完成 96 单元；95 个可评价单元 parity/native/replay 通过，Era A 的 ATR 无可定义样本；645.1 秒 |
| `long_six_20260907` | 固定 6 因子完整 development，按年度分块且保留跨年 label tail；结果按 receipt 汇总 |
| `final_regression_20260907` | 最终保护检查加入后重跑最小 6 因子，全部 parity/native/exact replay 通过；43.4 秒 |

最小窗口为 2021-01-04 起的 60 个交易日。扩展短窗采用各 signal-era 首 60 个实际交易日；因子由来源、经济族、修正语义选择，未按指标成绩调整。最小/扩展/全历史 smoke 都是 retrospective development 接口验证，不是候选资格。

[扩展短窗摘要](EXTENDED_SMOKE_SUMMARY.csv) 的最大原生日 Rank IC 差异为 `1.1102230246251565e-16`，低于执行前设定的 `atol=1e-12, rtol=0`。该容差比计划建议更严格，未因结果调整。短窗访问审计最大请求日期为 2021-05-07（含标签尾部）。扩展和长历史运行有时间重叠，耗时/RSS 不是独占机器的 cold/cache 或并行认证结果。

## 验收与剩余工作

已验证：超界读取在 IO 前拒绝、留置期 synthetic 改值不改变受限输入、重复键拒绝、缺交易日标签不发生物理移位、未成熟标签为空、ties/常量/NaN/inf、native 正负方向与收益算术、signal-era 跨年语义、FDR 完整家族和缺口。

完整仓库检查通过 **523 tests** 及所有现有 synthetic validators；最新定向检查 **12 tests** 通过。Fast 检查 46 tests、Qlib runtime 6 tests 通过。依赖仍有既有 deprecation/runtime warnings。新增保护已用最终 6 因子真实回归验证。

尚未完成：全 765 development feature quality、fundamental availability 的本轮抽查闭环、单进程/并行及分块等价性、缓存 identity/损坏恢复、资源估算与 required profile 冻结、正式 765 全量评价/FDR、Evidence Board V0、一次性规则冻结和 Candidate Board V0。不能把最小/扩展 smoke 通过写为 Phase 1 全部通过，更不能写 `primary_mvp_status=complete`。

近期诊断访问保持 false。10D、Core/经济组合、模型和 Strategy V2 均未启动；原 Phase 0 backward replication 与冻结 Strategy V1 未改动。

## 复现入口

从仓库根目录、已配置 Qlib 环境执行；run_id 必须使用新名字：

```powershell
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id audit_new
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id minimal_new --smoke
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id eras_new --extended-smoke
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id long_new --long-smoke
```

当前入口没有 full/candidate 子命令。完整计划及停止点见 [开发计划](../../docs/LONG_HISTORY_MULTI_EVALUATOR_SCREENING_MVP_PLAN.md)。
