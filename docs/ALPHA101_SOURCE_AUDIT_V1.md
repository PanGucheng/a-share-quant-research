# Alpha101 Source Audit V1

本文档记录 V3.23 的第一步：为大规模扩张因子池选择 Alpha101 开源来源。当前只做 source audit 和 metadata catalog，不实现 adapter，不运行 V4，不训练模型。

## 结论

优先来源：

```text
tmp/reference_repos/KunQuant/KunQuant/predefined/Alpha101.py
```

原因：

- license 为 Apache-2.0。
- 本地源码包含 `AllData`、`alpha001` 等函数和 `all_alpha` 列表。
- `tests/test_alpha101.py` 提供了 KunQuant 自己的 Alpha101 测试路径。
- 适合作为公式来源，后续 adapter 可以调用其定义，而不是手写公式。

备用来源：

```text
tmp/reference_repos/Ginkgo_Alpha101
```

当前本地克隆只有 README/LICENSE，没有公式实现文件，因此只能作为 metadata/reference，不能作为计算 adapter 来源。

## 运行

```powershell
cd E:\qlib_prj\qlib_baseline
E:\anaconda_envs\qlib_env\python.exe scripts\audit_alpha101_sources_v1.py --config configs\alpha101_source_audit_v1.yaml
```

## 输出

```text
outputs/factor_catalog_alpha101_v1/source_audit/alpha101_source_summary.csv
outputs/factor_catalog_alpha101_v1/source_audit/kunquant_alpha101_inventory.csv
outputs/factor_catalog_alpha101_v1/source_audit/alpha101_source_audit_report.md
outputs/factor_catalog_alpha101_v1/kunquant_alpha101_catalog_metadata.yaml
```

## 当前审计结果

```text
KunQuant parsed formula functions: 82
KunQuant all_alpha entries: 82
Ginkgo runnable implementation files: 0
metadata catalog entries: 82
```

KunQuant 当前 `all_alpha` 未覆盖 1..101 的所有编号，缺失：

```text
48,56,58,59,63,67,69,70,76,79,80,82,87,89,90,91,93,97,100
```

这意味着下一阶段不能宣称已经接入完整 101 个 Alpha101 因子；应以 KunQuant 当前可用的 82 个公式为第一批。

## 边界

生成的 metadata catalog 中所有条目均为：

```text
enabled: false
runnable: false
stage: alpha101_source_audit_adapter_pending
compute_adapter: kunquant_alpha101_adapter_pending
```

这能防止未适配、未评价的 Alpha101 公式被 batch runner 误跑。

## 下一步

1. 实现最小 KunQuant Alpha101 adapter smoke，先选 3-5 个字段依赖简单、窗口较短的公式。
2. 从 Qlib OHLCV/amount panel 构造 KunQuant 所需的 `open/high/low/close/volume/amount` 矩阵。
3. 优先使用 KunQuant Python API 或其 pandas reference 作为公式来源，不手写公式。
4. 输出 factor frame、coverage summary、smoke catalog。
5. 走 V4 smoke -> promotion/holdout -> multi-source screening contract。
