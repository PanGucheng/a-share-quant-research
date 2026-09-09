# V3 Broad494 / Strict332 九折预计算

状态：入口实现及轻量验证完成，真实模型预计算与独立重放尚未执行。
用户于 2026-09-09 授权本轮，并明确要求长任务自行在 PowerShell 执行。
`f2f3fc3` 已快进合并到本地 main。

## 执行范围

- Broad494 的 2015–2023 九折模型与完整年度 prediction → Broad494 独立重放 →
  Strict332 九折模型与 prediction → Strict332 独立重放。一次一个 fit，8 线程、固定 100 轮。
- 复用 `v3_recompute_audit_20260909_v1` 的不可变 P0、训练资格及 2010–2022 标签缓存。
  每次训练标签只按该折合法 train 日期读取；rank 在池内 feature mask 之前计算。
- 完整保留每年的 prediction 日期，包括 2023 年末尚不具备成熟标签的日期。
- 不做 outcome evaluation、IC、收益、重要性分析、pool comparison、模型选择或近期诊断。
  本次授权不改变 Strategy V1/V2，也不宣布 P3 competition ready。

## PowerShell 命令

```powershell
Set-Location E:\qlib_prj\qlib_baseline
& .\scripts\precompute_research_protocol_v3.ps1 `
  -RunId v3_precompute_broad494_strict332_20260909_v1
```

只检查环境、代码/冻结元数据、九折日历及训练资格，可加 `-Preflight`。
这不会创建运行目录，不训练、不生成预测、不扫描 canonical 特征值。
默认 Python 为 `E:\anaconda_envs\qlib_env\python.exe`。

输出根目录为 `outputs/research_protocol_v3_precompute/<RunId>/`：

- `Broad494/annual_YYYY/`、`Strict332/annual_YYYY/`：模型、prediction、资源记录、访问记录与回执。
- `verification/<Pool>/result.json`：该池九折独立重放结果；成功状态 `all_nine_exact`。
- `status.json`：执行状态；两个池完成后为 `all_precompute_and_replay_complete`。
- 日志在仓库 `tmp/<RunId>-<Pool>-precompute.log` 与 `tmp/<RunId>-<Pool>-replay.log`，追加保存。

## 数据边界与完整性

部分 canonical parent Parquet 同时包含 2021–2026 数据。因此本入口不沿用旧 runner 的
全 provider 价格文件/整 parent 文件哈希扫描。每次只对 2023 年及以前的 canonical
投影切片进行读取，并与已经审计的 `access.json` 中 `slice_hash` 精确核对。
源 manifest、代码、审计回执和池定义仍绑定；2023 特征证据来自既有 Broad494 宽表 canary，
其覆盖包含 Strict332，入口检查该条件。审计事件元数据共 1672 条，已检查覆盖全部所需特征/日期。
跨期文件通过日期 predicate 和列投影读取；不请求 2024+ 行，不重新读取 provider 日历或价格。
已有 protocol/manifest 的日期元数据用于绑定来源，不作为近期研究输入。

历史源代码 hash 接受 Windows checkout 引入的纯 CRLF→LF 还原；除此之外任何源代码变化
均拒绝。新的运行合同绑定当前工作区原始字节 hash。旧合同、回执、模型及预测均不改写。

独立重放在独立 Python 进程重新加载 model.txt，从 canonical 特征直接调用 LightGBM，
不调用 runner 的 predict，也不读取标签值。按月核对全部 keys、score（精确含 NaN）、reason、
年度日期覆盖、模型 hash/迭代/列顺序与访问边界。此处“重放”不指再次拟合模型。

## 资源与恢复

既有 Broad494 首折/末折各耗时约 12.6/30.0 分钟，RSS 约 2.60/4.55 GiB。
这是既有 canary 证据，不能视为九折或 Strict332 实测。18 次 fit 加切片完整性扫描和独立重放
请预留半天或过夜；本轮没有实测总时长。

每折至少要求 30 GiB 空闲磁盘；预检时 E 盘约 161.6 GiB。每折结束后先记录月度 float64
临时块 hash，再仅删除本次未发布目录里的临时块，随后发布模型及预测。不会积累两池全部
训练矩阵。12 GiB RSS 是沿用的资源记录预算，不是操作系统硬限制。

失败立即停止；保留输出与隐藏临时目录。相同代码、环境和输入下再次运行同一命令，严格校验
后跳过已完成折；未完成折重新开始。独立重放作为整池单元，失败后重新重放该池。
失败留下的临时块不会自动清理，可能额外占空间。合同不匹配或回执损坏应停止诊断，
不能删除回执、改 hash 或覆盖旧证据来续跑；代码变化必须换新 RunId。

## 本轮交付验证

- PowerShell 实际 `-Preflight` 通过；Broad494=494、Strict332=332，各九折全部 train eligible。
- V3 原有与新增定向测试共 26 项通过；fast lint/测试 46 项通过。
- 新增测试约束 Sequence 数值循环与 `f2f3fc3` 完全一致，并覆盖独立日历、Strict 顺序门禁、
  无标签重放、prediction 篡改和有日期边界的特征完整性核验。
- 未执行真实训练、真实 prediction 重放或 canonical 特征扫描。
  未运行包含其他研究/evaluation 工作流的 full validators，保持本轮禁止 outcome evaluation 的边界。
  全部真实切片 hash 核验由用户执行时完成，失败会在 fit 之前停止。
