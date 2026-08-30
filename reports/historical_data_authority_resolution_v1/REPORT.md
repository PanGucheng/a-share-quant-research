# Historical Data Authority Resolution V1

> 状态：`QUALIFICATION COMPLETE / AUTHORITY UNRESOLVED / EXTENDED MATRIX NOT GENERATED`。

## 结论

- Lifecycle 的最佳可复现候选是 **Community Qlib interval + Tushare stock_basic/namechange + Tushare/BaoStock dated market presence cross-check**。这能构造 listing/delisting/rename 的候选区间，但 Qlib 是 release snapshot、Tushare stock_basic 是 current snapshot，故不能证明任意历史日期的 historical vintage；survivorship-control gate 仍 blocked。
- Fundamental retrieval 已改为 broad offset pagination 与 2010–2017 exact report-period segmentation（使用 `period=YYYYMMDD`，避免公告跨年导致的 calendar-window 漏行）。`statement_completeness_summary.csv` 记录每个 issuer/API 是否所有页终止、是否触及 cap、以及目标期 key set 是否一致。即使通过，这只证明当前 endpoint 的 retrieval completeness，不证明 provider 保存的 revision vintage 完整；PIT authority 仍 blocked。
- `recomputed_frontiers.csv` 重新计算 daily_basic/moneyflow 的 coverage candidate，但 `authoritative=false`，不能把此前 `2016-07` 等候选升级为正式 frontier。
- Full Factor Universe V2 common frontier：`not_admitted`；Extended Matrix：`not_generated`。

## 证据与限制

本轮没有读取 model outcomes，没有修改 Research Protocol V2、Factor Universe V2 definitions、Strategy V1、Forward Track 或旧 frozen Matrix。网络请求 receipts、statement retrieval receipts、raw parquet 与 manifest 均保留；token 未写入 artifacts。

治理状态：

```text
extended_matrix_generated = false
formal_structured_ml_competition_started = false
research_protocol_v2_changed = false
factor_universe_v2_definitions_changed = false
frozen_matrix_changed = false
strategy_v1_changed = false
forward_track_changed = false
model_outcomes_read = false
```

复现：

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_historical_data_authority_resolution_v1.py --stage all
```
