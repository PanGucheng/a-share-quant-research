# R218 / C201 / H358 九折预计算

2026-09-11：**D1 CLOSED / REPRESENTATIONS FROZEN / D2 COMPLETE / ALL FIVE ARMS SEALED**。
用户已完成27模型及独立replay，核验通过，无需重跑；见[完成报告](../reports/literature_factor_representation_d2/COMPLETION_REPORT.md)。
下述命令与资源预估保留为入口交付时运行说明，实际完成状态以上述报告为准。
[D1 正式冻结](../reports/literature_factor_representation_d1/FORMAL_FREEZE.md)已先独立提交为 `d05e7eb`。
[D2 实施报告](../reports/literature_factor_representation_d2/REPORT.md)说明验证范围和局限。

## 执行

```powershell
Set-Location -LiteralPath 'E:\qlib_prj\qlib_baseline'
& '.\scripts\precompute_literature_d2.ps1' `
    -Python 'E:\anaconda_envs\qlib_env\python.exe' `
    -RunId 'd2_rch_20260910_v1'
```

顺序：metadata preflight → 168个月表示缓存 → H2023训练和独立重放 →
R九折及重放 → C九折及重放 → H其余折及重放 → 全27折核验和封存。
H2023属于27个正式模型之一，后续校验通过后复用，不额外拟合第28个模型。
一次一个模型，固定100轮、8线程，未增设调参/early stopping/validation路径。

只预检加 `-Preflight`，不创建运行目录、不读研究值。
只执行缓存及H2023资格检查加 `-CanaryOnly`；完成后同一命令去掉此参数继续即可。
该资格检查包含整折历史训练，仍是长任务，交用户执行。
真实最大折峰值RSS须≤12 GiB才能继续其他折；工程prediction coverage须≥原V3的95%。

## 输入合同和独立性

冻结hash：`29e473cedcefa2715bb770188d64da23db579e509bb2a99982e93b8885d24ccc`。
原recipe hash：`8b688bd098ebafd1c1da2bab32d029624f6da65f7166c59f702fbc18499cf51f`。
recipe内旧diagnostic状态保留作历史记录；正式授权来自独立freeze overlay。
修改配方、列序、U、family、方向、门槛、实现或运行环境会拒绝续跑。

全部表示先按每一个合法日期的完整canonical dated universe计算，不使用label mask、
未来存活名单、跨日期标准化、拟合参数或重新初始化的递归状态。每月只为I/O组织单位。
因此可缓存全开发期的逐日H并按列投影R/C；各折数值读取仍在I/O前检查精确train/predict日轴。
不存在让早期日期的表示依赖后期值的运算。研究设计本身仍是2010–2023回顾性设计，
不能把这一数值因果性解释成selection-past-only或全新OOS发现。

缓存每月重新投影494个批准输入，检查五组aliases，再对所有日期R/C/H输出逐日核对
D1已冻结哈希。只保留H358的union矩阵，R/C从其有序列选择；父节点无新增信息。
Canonical跨期Parquet的日期predicate/列投影在I/O前生效，不读取2024+行或hash整父文件。

训练直接复用V3 `prepare_training_batch`、`Float64FileSequence`、`fit_sequences` 和 `predict`。
目标rank、daily-equal weights、purge、maturity、缺失处理和完整learner config与B/S相同。
另核对每月训练键哈希与行数确实与B/S相同，防止表示mask静默改变训练样本。
只有原审计2010–2022 label cache做完整性checksum，数值读取使用该折合法train日期predicate；
未读取2023 label cache、不生成新价格/标签、不将prediction与label合并。

独立replay进程重读canonical合法预测月份，以独立 `naive_day` 重建秩、ties和分层平均；
不调用生产transform或predict来验证自身。表示mask精确，表示数值rtol=0/atol=1e-12；
这延续D1预先声明的容差。保存Booster后独立计算的prediction仍要求**逐值exact**，无容差fallback。
若表示的浮点舍入触发树分支差异，停止并保存失败；不能放宽验收再宣称all_nine_exact。
keys、日期、reason、行数、model/recipe/receipt身份同时核验；不输出分数分布或效果统计。

## 资源、产物与恢复

根目录：`outputs/literature_factor_representation_d2/d2_rch_20260910_v1/`。

- `contract.json`、`provenance.json`：代码、runtime、freeze、V3配置、B/S工程键轴。
- `cache/YYYY-MM/`：H358 float64 Parquet、canonical slice访问日志、D1来源和资源记录。
- `R|C|H/annual_YYYY/`：model、prediction（含keys/reason）、有序表示身份/依赖/caveats、
  输入及合法label切片hash、月度训练键hash、fit/dataset/prepare/predict耗时、RSS、临时磁盘和完整receipt。
- `replay/R|C|H/annual_YYYY/`：独立重放结果、访问日志、模型回执绑定及receipt。
- `sealed/folds.csv`、`sealed/result.json`：全部27单元通过后才发布的工程汇总。

缓存额外占磁盘，训练还需一折float64临时块。每个模型阶段至少30 GiB空闲；
交付预检约161 GiB空闲。完整运行时间和最大折内存尚未实测，不能用小样本canary外推为保证。
本次未自动执行缓存、真实模型fit或真实年度prediction replay。

原子单位使用固定 `.annual_YYYY.incomplete` 或 `.YYYY-MM.incomplete` staging目录。
完成且完整receipt/hash匹配才跳过；缺文件、坏hash、合同变化、残留incomplete均硬停。
正常完成后先记录scratch哈希和字节数，再删除本次未发布stage内float64临时块；缓存、模型和回执保留。
普通异常记录failure.json；进程强制终止可能没有该文件，但stage及已写块保留。
同一入口可续跑已完成单元；**incomplete不会自动清空或重跑**，需先检查原始失败证据。
不要删receipt、补造hash、复制其他fold回执或换RunId掩盖失败。本实现不提供破坏性清理入口。

## 停止点

成功状态：R/C/H均 `all_nine_exact`，27个模型与独立重放封存。
B/S原有预计算继续复用，不重训。所有五臂的结果仍封闭。
用户运行结束后，核验机器产物再发布真实完成报告；当前不提前宣称D2完成。
禁止outcome evaluation、pool performance comparison、importance/SHAP、returns/portfolio、D3和2024+研究值。
