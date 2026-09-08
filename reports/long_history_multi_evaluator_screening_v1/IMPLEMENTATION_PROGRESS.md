# Long-History Multi-Evaluator MVP：实施进度

最新状态：**PRIMARY V0 COMPLETE / STOP FOR HUMAN REVIEW**，2026-09-08。[审阅报告](REPORT.md)和两张765行Board已交付。用户于2026-09-07授权实施；下列运行记录保留各阶段当时的状态与测试数量。
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

运行数据在 ignored `outputs/long_history_multi_evaluator_screening_v1/`；smoke 每次使用新 run_id。新增 full 入口使用固定 run_id 恢复同一任务，不覆盖已完成单元。

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

尚未完成：正式 765 全量评价/FDR、Evidence Board V0、一次性规则冻结和 Candidate Board V0。全量恢复入口及其小规模验证见下节；初始单 worker 任务已由用户启动并在完成 94 单元后结束，现按用户要求增加进程并行。PIT 抽查、分块/两 worker 指标等价性、价格缓存完整性和 required metric profile 已有上述证据；这些不等于全量执行完成，更不能写 `primary_mvp_status=complete`。

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

以上入口保留为 audit/smoke。完整计划及停止点见 [开发计划](../../docs/LONG_HISTORY_MULTI_EVALUATOR_SCREENING_MVP_PLAN.md)。

## 全量计算与独立终端交接（2026-09-07）

新增 [全量 CLI](../../scripts/run_long_history_primary_full.py)，复用上述受限读取、价格缓存、精确标签、原生评价函数与 FDR。全量为 765 因子 × 14 年 = 10,710 个单元，每个单元计算三套原生指标；同年度 key hash 一致时共用标签。所有年度完成后才计算 19 个时期视图和单一 765 家族的 bootstrap/BH/BY。

每个单元先写 staging，再以目录重命名发布完整 receipt。恢复时逐文件核对哈希；输入配置、原生源码/依赖、相关实现、价格源内容或 canonical parent 大小/修改时间变化时拒绝混用旧结果。Canonical 大分区继续继承 assembly 的完整性认证，未重新逐字节扫描；stat 绑定不是防范恶意保留大小和时间戳篡改的认证。价格源完整性哈希可能触及近期存储字节，实际加载及计算数据仍不超过 2023-12-29。

同一 run_id 使用操作系统锁；正常退出或进程结束会释放锁，磁盘上的 `run.lock` 无需删除。强制结束时未发布的 staging 保留作诊断，重启只重算未完成单元。损坏的已完成单元会报错，不会静默当作缺失或 p=1；可用 `--rebuild-chunk 年份/因子名` 明确归档原单元和依赖汇总后重算。该选项仅用于工程重建，不改变研究规则。若整个输入合同发生变化，应保留旧 run，重新选择 run_id。

实际小规模验证见 [编排验证记录](ORCHESTRATION_SMOKE.json)：`orchestration_resume_20260907` 首次完成两个 2010 年单元，第二次只新增第三个；显式重建将旧单元归档，并仅重算指定的一个单元；`alpha158_BETA20 / 2010` 的八份原生结果与此前 `long_six_20260907` 及重建前结果 exact 一致。暂停使用 `--max-new-jobs`，没有缩小正式库存或将部分运行标为完成。Synthetic tests 覆盖合同变化、结果改值损坏、跨进程互斥、缺年度任务拒绝汇总、原始日序列与分桶汇总。

本次完整检查 529 tests 与现有 synthetic validators 通过；Fast 46 tests、Qlib runtime 6 tests 通过。完整计算及 765 因子真实 FDR 尚未运行。

用户要求自行启动长任务。请从 Windows 开始菜单或 Windows Terminal 新开 **独立 PowerShell**，执行：

```powershell
Set-Location E:\qlib_prj\qlib_baseline
& E:\anaconda_envs\qlib_env\python.exe -u scripts/run_long_history_primary_full.py --run-id primary_full_20260907 --workers 8 2>&1 | Tee-Object -FilePath tmp/long_history_primary_full_20260907.log -Append
```

中断后重新执行同一条命令即可恢复。不要加 `--max-new-jobs`，不要在运行期间更新本次绑定的研究代码或数据。此独立终端启动的计算不依赖 Codex 对话；关闭 Codex 后仍可运行，但须保留该终端并保持计算机开机、不休眠。关闭终端、关机或重启可能结束进程，之后可恢复。它只执行已实现的 Python 工作，不会在 Codex 关闭后自行继续开发或制定候选规则。

在另一个 PowerShell 查看进度：

```powershell
Get-Content E:\qlib_prj\qlib_baseline\outputs\long_history_multi_evaluator_screening_v1\primary_full_20260907\status.json
Get-Content E:\qlib_prj\qlib_baseline\tmp\long_history_primary_full_20260907.log -Tail 20
```

`status.json` 含当前单元、已核验完成数、总数、PID 与更新时间；初始化合同核对和最终 bootstrap 期间可能暂时没有逐单元更新。此前 20–41 小时估算置信度低；新入口的共享标签减少重复计算，但两个单元不足以重新承诺全量耗时。

成功终点为 `execution_status=computation_complete_review_pending`，同时 `primary_mvp_status` 仍为 `in_progress`。`aggregate/` 保存 `period_metrics.csv/parquet`、`primary_fdr.csv`、factor inventory、job receipts 和文件哈希。随后由 Codex检查完整证据、完善 Evidence Board、一次性制定并冻结候选规则，生成 Candidate Board V0，再交用户人工审阅；此命令不自动制定规则，也不访问 2024+ 诊断或训练模型。

## 进程并行提速（2026-09-07）

用户已停止初始任务并要求提速，随后明确要求直接测试 8 个进程。新增 `--workers 1/2/4/8`，由主进程调度、独立工作进程计算。每个进程的数值库与 Arrow 计算线程均为 1；一次最多派发与 worker 数相同的单元，不传输整张因子表，进程内按 key hash 复用标签。价格缓存建造与读取使用互斥锁，单元目录另有锁防止孤立进程与恢复任务同时写入。原生指标、标签、分桶、样本规则、年份边界、FDR 和汇总计算均保持原定义。

并行结果按完成顺序落盘，日志顺序允许交错。`status.json` 新增 `workers`、`inner_threads`、`active_jobs`；原 `current_job` 在并行时表示最近完成的单元，正在计算的单元以 `active_jobs` 为准。正常按一次 Ctrl+C 后，主进程停止派发并等待当前少量单元结束再退出；若强制结束进程，恢复时重新核验磁盘完成记录。

为复用用户已完成的 94 个单元，只允许已知旧 runner SHA-256 `1507f37f74c0458a7bc4a927309fcdd3ab109293339fa2539616fd29bcca634c` 的调度版本迁移，且除该 runner 哈希外，输入合同的每个字段必须相同。原 `contract.json` 和旧单元 receipt 不改写；`execution/` 追加旧合同与新执行源码的对应记录、每次实际 worker 数和耗时。配置中的初始 `resources.workers=1` 保留作原合同追溯，实际资源由 CLI 明确覆盖并记录；这不改变研究参数。其他实现、数据或规则变化仍拒绝复用。

`--verify-parallel` 只计算预先固定的 24 个代表因子在 2010/2023 的 48 个单元，用独立合同和目录隔离，不计算正式 FDR、不表示 primary complete。正式启动命令不应添加该参数。

实测结果见 [进程并行验证](PARALLEL_PROCESS_SMOKE.json)：

| 工作进程 | 同一批 48 单元耗时 | 相对单进程观测加速 |
| --- | ---: | ---: |
| 1 | 201.98 秒 | 1.00× |
| 2 | 114.20 秒 | 1.77× |
| 8 | 65.31 秒 | 3.09× |

两进程与八进程各有 376 份原生 Parquet、48 份日样本状态与全部输入/mask/status receipt 和单进程 exact 一致；2010 年 ATR 无可定义样本，三次一致标为 unavailable。八进程按秒采样的进程组 RSS 合计峰值约 4.53 GiB、系统剩余内存最低约 5.64 GiB、CPU 合计最高约 801%（一个逻辑核心为 100%）。RSS 合计含共享页，离散采样不保证捕获瞬时峰值。

耗时包含工作进程初始化、IO、标签、计算和落盘，未包括共同输入身份核对、全量汇总与 FDR。单进程/两进程曾建造价格缓存，八进程命中缓存，因此 3.09× 是这轮端到端观测加速，不是控制所有缓存条件后的纯并行效率。代码哈希逐轮保存：单进程基准后只补充 receipt 执行来源字段，两进程基准后只扩展 CLI 接受 8；数值计算未改变。

已在原 `primary_full_20260907` 上使用 `--workers 8 --max-new-jobs 8` 验证续跑：原合同与 94 个旧 receipt 字节未变，仅新增 8 个完成单元，目前 **102/10,710，paused_job_limit**，测试进程已退出。用户执行上方命令（不加限额参数）即可从现有结果继续，无需从头计算。完整检查 **530 tests**、Fast 46 tests、Qlib runtime 6 tests 通过；正式全量仍未完成。

## Primary V0交付（2026-09-08）

用户的八进程任务已完成10,710单元，续跑主计算8873秒。全部完成文件重新验证哈希、访问日期与样本计数；16个年度单元数据不可定义，无原生运行失败。全期765个Rank IC假设均可检验，BH/BY校正全部复算；六个预声明代表因子的13指标×19时期和bootstrap从原始日序列复算通过。

先封存不含候选判断的Evidence Board和总体分布，再一次性冻结规则 `26559c272310fd361fcb0c8de4b658b77946058241e4bf26ede281a71d64950b`，最后生成Candidate Board。结果为332个3/3、159个2/3、43个1/3、206个0/3、25个incomplete。两张Board均765行，9个blocked留在774定义inventory。

候选抽取仅使用封存primary证据和冻结规则；缺少raw、aggregate及全部enrichment/近期文件时，9份候选产物仍可按文件hash精确重放。完整检查538 tests、Fast 46 tests、Qlib runtime 6 tests通过。新增入口为 `scripts/build_long_history_boards.py`，详细文件及复现约束见[审阅报告](REPORT.md)。

全量计算已结束，无需继续执行前述启动命令。当前状态以 `primary_full_20260907/primary/run_manifest.json` 为准。10D、近期诊断、数值去重/聚类、Core/组合、模型均未启动；这些不是已完成的primary V0内容。本轮严格停在人工审阅。
