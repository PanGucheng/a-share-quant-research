# Historical Data Engineering Extension V1

> 状态：`partial_extension`。本阶段采用 practical reconstructed PIT 与 practical historical universe；未读取模型 outcomes，未修改旧 frozen Matrix。

## 实施结果

- Extended Matrix generated: `True`
- Extended Matrix identity: `extended-matrix:af96ac22035f884b120d18a4a92e06febdff52e9e94e3cb4cbc074241b40cce1`
- Historical partitions: `762`
- Historical key rows: `8014460`
- Historical dates / instruments / maximum factors: `4913` / `3874` / `774`
- Historical range: `2000-11-01` — `2021-01-29`
- Partition integrity / continuous cumulative state: `True` / `True`
- Practical PIT leakage checks: `pass`
- Historical universe 2021+ overlap: `pass`
- Matrix 2021+ overlap: `fail` (774 factors；36 factors / 937301 common-key values differ；0 key-set differences)

## Factor-family frontiers

```text
                        layer                                                          source  factor_count                                                 frontier_basis   frontier  tail_date_count  tail_passing_fraction  minimum_tail_coverage  admitted
                  daily_basic                           Tushare daily_basic market-date cache            12                90% dated market presence with 98% passing tail 2010-01-04             2732               1.000000               0.998979      True
                    moneyflow                             Tushare moneyflow market-date cache            10                90% dated market presence with 98% passing tail 2010-01-04             2732               0.999268               0.537124      True
long_history_transparent_core          Community Qlib OHLCV/amount/VWAP + practical lifecycle            34             first non-empty practical-universe effective month 2000-11-01             2732               1.000000               1.000000      True
         full_price_volume_v2         Community Qlib + frozen V2 price-factor implementations           733 full 733-factor annual shards plus continuous cumulative state 2000-11-01             2732               1.000000               1.000000      True
              fundamental_pit Tushare statements/revisions reconstructed by announcement date            19 monthly practical market presence with leakage-safe as-of join 2010-01-29              135               1.000000               0.997312      True
      full_factor_universe_v2 intersection of price, daily_basic, moneyflow and practical PIT           774                     maximum admitted dependency-layer frontier 2010-01-29              135               0.999268               0.537124      True
```

## 数据层

- `full-feature common history`: `2010-01-29` 至 `2021-01-29`；2021-02-01 起引用 byte-immutable frozen V2 parent。
- `full price-factor history`: `2000-11-01` 起的 733 个 price/volume 因子；VPT/NVI/ADI/OBV 使用跨年度连续状态缓存。
- `long-history transparent core`: 上述长历史中的 34 因子显式子集，不删除其余可可靠 materialize 的价格因子。

## 十二项结论

1. 数据工程实际推进到 `2000-11-01`；底层市场 raw 从 2000-01-04 起，practical universe 的首个有效月决定 Matrix 首日。
2. Full Factor Universe V2 的 774 因子共同层从 `2010-01-29` materialize；733 因子价格层更早。
3. 各 family frontier 见上表和 `factor_family_frontiers.csv`；frontier 使用 dated market presence，而非 current-universe 分母。
4. Qlib 补齐长期 OHLCV/amount/VWAP 与 lifecycle；Tushare 分段缓存补齐 daily_basic、moneyflow 和公告/修订 statements。
5. 真正缺口是 pre-2010 moneyflow 等价全市场信息、未构建的 pre-2010 daily_basic 层，以及无法证明不存在的旧 revision；详见 `remaining_data_gaps.csv`。
6. 已形成 full-feature、full price-volume、transparent core subset 三层，而不是强迫所有因子共用起点。
7. Practical reconstructed PIT 仅允许 `information_available_date <= decision date`，并独立验证 latest-public-event、revision 顺序和单日唯一状态：`pass`。
8. Historical universe 由 Qlib lifecycle interval、实际市场存在和 point-in-time rolling selection 重建；2021 overlap：`pass`。
9. Extended Matrix generated：`True`；身份与 frozen parent 分离。
10. 实际覆盖 `4913` dates、`3874` instruments、最多 `774` factors。
11. 2021-02-01 至 2021-03-31 overlap：`fail`；key set 完全一致，剩余值差异集中于 Alpha101，并含极少 TA 与 practical-PIT statement-vintage residual；逐因子差异和 lineage 分类分别写入 `matrix_overlap_validation.csv`、`overlap_lineage_summary.csv`，不静默接受。
12. 后续可预注册比较四个 dataset hypotheses，见 `historical_dataset_hypotheses.csv`；本阶段不选择最佳训练起点。

## Lineage 与缺口

`source_lineage.csv` 记录每个 source 的实际角色、缓存证据和未解决限制；`annual_matrix_summary.csv`、`historical_partition_manifest.csv` 和 manifest 共同定义独立 Matrix identity。BaoStock/AkShare 只保留为早期可得性与调整 canary，没有在 Qlib 字段完整时人为混源。

## 治理边界

Factor Universe V2 definitions、Research Protocol V2、Strategy V1、Forward Track 与旧 frozen Matrix 均未改变；Structured ML/model/portfolio 阶段未启动。
