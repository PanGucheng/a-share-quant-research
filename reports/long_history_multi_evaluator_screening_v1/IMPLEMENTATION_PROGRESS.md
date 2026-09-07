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
| `long_six_20260907` | 已完成 6 因子×14 年=84 单元，全部 parity/native/exact replay 通过；1,134.2 秒 |
| `final_regression_20260907` | 最终保护检查加入后重跑最小 6 因子，全部 parity/native/exact replay 通过；43.4 秒 |

最小窗口为 2021-01-04 起的 60 个交易日。扩展短窗采用各 signal-era 首 60 个实际交易日；因子由来源、经济族、修正语义选择，未按指标成绩调整。最小/扩展/全历史 smoke 都是 retrospective development 接口验证，不是候选资格。

[扩展短窗摘要](EXTENDED_SMOKE_SUMMARY.csv) 的最大原生日 Rank IC 差异为 `1.1102230246251565e-16`，低于执行前设定的 `atol=1e-12, rtol=0`。该容差比计划建议更严格，未因结果调整。短窗访问审计最大请求日期为 2021-05-07（含标签尾部）。扩展和长历史运行有时间重叠，耗时/RSS 不是独占机器的 cold/cache 或并行认证结果。

[全历史摘要](LONG_SMOKE_SUMMARY.csv) 记录 84 个年度单元；[分块对照](BLOCK_EQUIVALENCE.csv) 的 192 项短窗/年度原生输出比较全部 exact pass。[资源估算](RESOURCE_ESTIMATE.json) 给出单 worker 全量约 20–41 小时的暂定区间，不能外推模型 8T 加速，也不是正式执行许可或 SLA。

[财报可得日期抽查](PIT_SAMPLE_AUDIT.json) 覆盖 2010、2021 分区交接两侧及 2023 四个窗口，每窗取 canonical 字典序前 8 支股票，共 1,888 行；latest-public-event、无未来财报和 ROA 数值核对全部通过。历史段使用 historical statement events，continuation 使用 merged events；最初误用 continuation 事件源造成两只早期股票缺事件，已按正确 parent 重查并披露，没有改写 canonical 因子值。

[Bootstrap null smoke](BOOTSTRAP_NULL_SMOKE.json) 对 32 组 AR(1)=0.6、3,361 日并注入十日缺口的合成零均值序列使用 block=20、samples=1000，3/32 的 p≤0.05；这不是充分的统计校准证明。p 值分辨率为 1/1001，正式使用仍须披露 Monte Carlo 限制与短片段排除。

`quality_765_20260907` 已完成全 765 development-only feature profile，按分区/年落盘，耗时约 1,377.8 秒（23 分钟）。新增价格缓存复用现有 Parquet/sidecar 格式，绑定 `$close` 源内容、日历、loader AST、请求日期和 instruments，并校验逻辑内容；真实缓存 smoke 另列结果。缓存完整性哈希可能读取近期存储字节，但缓存输出与计算行仍严格限制 development。

[价格缓存真实验证](PRICE_CACHE_SMOKE.json)：首轮一份共同价格缓存 miss、其余五因子复用命中；第二轮六因子全部命中。48 个原生结果文件与首轮完全一致；两轮约 39.9/29.6 秒。该收益只适用于已测短窗，不是全量加速保证。合成测试覆盖同 schema 改值损坏、价格源内容变化与两 worker 原生指标一致性。

[两 worker 真实对照](PARALLEL_SMOKE.json) 在共享已加载输入上同时计算 6 因子的原生指标，48 项与顺序结果 exact 一致。Parquet 丢失的索引 freq 元数据不参与比较，日期值、索引结构与指标值仍严格比较。原生计算段约 4 秒；不含 IO、缓存建造和进程启动，因此不认证全量吞吐。

[原生指标清单冻结](../../artifacts/long_history_multi_evaluator_screening_v1/ce3d1c0cf946be1179d117f9726409faeabc32839741e30c073a2fd0ba0d41bc/native_profile.json) 绑定通过的原生源码与指标范围；仅冻结 primary metric profile，不冻结 candidate threshold，也不等于正式全量执行完成。

[全库质量摘要](FEATURE_QUALITY_SUMMARY.json) 与 [765 因子质量表](FEATURE_QUALITY_FULL.csv) 已生成：10,710 个年度记录、540 次受限读取，无无穷值、无全期没有有限值的因子、无全期缺乏 50 样本变动横截面的因子。同起止区间的各分区 key hash 一致；最大有效读取日 2023-12-29。覆盖率最低约 35.46%、中位约 95.56%，分母是 canonical 分区行，不能理解为全部历史 A 股。低覆盖、晚起始与常量日期只保留诊断，不删因子、不改 765 库存。

## 验收与剩余工作

已验证：超界读取在 IO 前拒绝、留置期 synthetic 改值不改变受限输入、重复键拒绝、缺交易日标签不发生物理移位、未成熟标签为空、ties/常量/NaN/inf、native 正负方向与收益算术、signal-era 跨年语义、FDR 完整家族和缺口。

完整仓库检查通过 **526 tests** 及所有现有 synthetic validators；最新定向检查 **15 tests** 通过。Fast 检查 46 tests、Qlib runtime 6 tests 通过。依赖仍有既有 deprecation/runtime warnings。新增保护已用最终 6 因子真实回归验证。

尚未完成：正式全量任务恢复与缓存损坏后的受影响批次重建、真实全量执行资源选择、正式 765 全量评价/FDR、Evidence Board V0、一次性规则冻结和 Candidate Board V0。PIT 抽查、分块/两 worker 指标等价性、价格缓存完整性和 required metric profile 已有上述证据；这些不等于全量执行链验收，更不能写 `primary_mvp_status=complete`。

近期诊断访问保持 false。10D、Core/经济组合、模型和 Strategy V2 均未启动；原 Phase 0 backward replication 与冻结 Strategy V1 未改动。

## 复现入口

从仓库根目录、已配置 Qlib 环境执行；run_id 必须使用新名字：

```powershell
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id audit_new
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id minimal_new --smoke
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id eras_new --extended-smoke
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id long_new --long-smoke
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id quality_new --quality-audit
python scripts/run_long_history_multi_evaluator_screening_v1.py --run-id cache_new --smoke --price-cache
```

当前入口没有 full/candidate 子命令。完整计划及停止点见 [开发计划](../../docs/LONG_HISTORY_MULTI_EVALUATOR_SCREENING_MVP_PLAN.md)。
