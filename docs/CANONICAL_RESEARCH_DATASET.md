# Canonical Research Dataset Authority

## Authority

后续 Dataset / Research Protocol research 的唯一推荐历史 Matrix 输入是：

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

机器入口：

- `outputs/canonical_historical_dataset_assembly_v1/current/manifest.json`
- `outputs/canonical_historical_dataset_assembly_v1/current/partition_manifest.csv`
- `outputs/canonical_historical_dataset_assembly_v1/current/factor_lineage.csv`

运行时 outputs 默认不进入 Git；tracked authority、结论和小型审计证据见
[final report](../reports/canonical_historical_dataset_assembly_v1/REPORT.md)。任何后续任务必须先校验
上述 identity，再按 partition manifest 的 `effective_start` / `effective_end` 读取数据；不能直接把
底层 parent parquet 的完整日期范围视为 canonical range。

## Contract

- 日期范围：`2010-01-29` 至 `2026-06-09`；
- schema：774 个 Factor Universe V2 definitions；
- qualification：765 个 global physical-data-qualified candidates，9 个 blocked / non-research-usable；
- Alpha101：每个横截面 rank 都施加 dated PIT eligibility，并使用贯穿 canonical horizon 的稳定 membership axis；直接读取的 `$vwap` 也遵守同一 PIT mask；
- KAMA：从 `2000-01-04` anchor 开始的 causal recursive state；
- Fundamental：`information_available_date <= decision_date` 的 practical reconstructed PIT，
  continuation 使用合并 historical/frozen statement window；
- Universe：dated Qlib lifecycle + market presence 的 practical historical universe；
- 同一 factor name 在全时间轴上只有一种 authoritative semantics。

774 个定义不等于 774 个模型特征。后续任何带时间依赖的 factor eligibility、selection、IC 或模型输入
仍必须在 development-only、split-local 边界内决定，不能用后期 coverage 反向选择早期 membership。

## Evidence versus authority

以下对象继续 immutable，但只承担历史 evidence / parent lineage 角色：

- old frozen Factor Universe V2 Matrix；
- Historical Data Engineering Extension V1 `partial_extension`；
- Extended Matrix Overlap Lineage Resolution V1 historical Matrix。

Canonical dataset 引用其已证明一致的分区，并为 2021+ 重算 15 个 Alpha101、KAMA 与 19 个
Fundamental；它没有覆盖或改写上述 evidence。新研究不得默认回退到 old frozen Matrix，也不得把
旧 bug 的 value overlap 当成 authority。

## Stage status

Historical Data Engineering 已正式 `CLOSED`。只有明确的数据 bug、leakage 或 provenance failure
可以重新开启；“继续寻找更早历史”“继续 source authority”“继续扩大 lifecycle canary”不再是默认任务。

该关闭状态只说明 canonical input 已准备好，不代表 Research Protocol redesign 或 Structured ML 已启动。
当前两者仍为 `false`，必须由单独任务授权。
