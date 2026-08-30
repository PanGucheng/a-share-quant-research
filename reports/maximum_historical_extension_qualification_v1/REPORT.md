# Maximum Historical Extension & Qualification V1

> 状态：`QUALIFICATION COMPLETE / EXTENDED MATRIX NOT GENERATED`。本阶段最大化调查历史深度，未修改 frozen Matrix、Factor Universe V2 definitions、Research Protocol V2、Strategy V1 或 Forward Track；未读取模型 outcomes。

## 结论

本次审计复用了仓库已有的 Community Qlib、Tushare、BaoStock、AkShare、冻结 raw caches、Factor Universe V2 inventory/qualification 与 lifecycle interval 文件。技术上，Community Qlib 的 price/volume/amount/VWAP/factor/adjclose 可追溯至 `2000-01-04`；BaoStock、AkShare 与 Tushare 对代表性长期上市股票均能返回 2000 年代早期日线。这个结果只证明“可获得”，不自动证明“当时可得信息可重建”。

当前可保留的 frontier map 是：

- price-volume：技术起点 `2000-01-04`；研究候选从 `2008/2010` 起，须完成 corporate-action/adjustment continuity；
- daily_basic：早期 API rows 可得，但 stable/full-market qualification 暂定 `2010` candidate；
- moneyflow：既有年度 receipts 显示 `2007–2009` partial，`2010` 起稳定；
- fundamental PIT：代表性 Tushare 报告期可见至 `1995–2000`，但多组 responses 触及单次 row cap，且 revisions/update_flag 证明了修订对象，不证明早期完整 PIT vintage；当前 research-grade frontier 暂定 `2018` pending qualification；
- lifecycle/universe：Qlib interval files 具有 2000 起的 listing/delist proxy，但 current stock_basic/namechange 不能替代历史数据库 vintage；需单独的 market-wide lifecycle canary。

因此本阶段**没有生成 extended Matrix**。Full Factor Universe V2 的共同 reliable frontier 仍未被足够证据确定；不能用最早可下载日期替代 research-grade 日期。

## 数据源角色与交叉验证

详见 `source_inventory.csv`、`cross_source_comparison.csv`、`cross_source_close_differences.csv` 与各 source receipts。比较时统一了 instrument、date、close、volume、amount 轴；金额换算保持 source units 可追溯，不要求逐值完全一致，只检查覆盖、数量级和差异是否可解释。Tushare 日线按五年分段以规避 6000 行上限；statement audit 明确标记了达到 100/200 行 cap 的返回，避免将截断响应当成完整历史。

## Factor Universe V2 分层

`factor_family_frontier.csv` 将 774 definitions 按依赖层映射到 price-volume、daily_basic、moneyflow、fundamental PIT。不得为得到更长历史而静默删除 41 个非 price-core factors；如未来证据支持，应保留 `long-history core` 与 `full-feature common-history` 两个明确命名的数据集。

## 资格审计结果

`qualification_decision.csv` 明确记录：price technical history 通过但带 adjustment 限制；full-feature 仅为 2010 candidate；pre-2018 fundamental PIT blocked；common V2 frontier not yet admitted；extended Matrix not generated；Protocol/model stages not started。

## 可复现入口

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts\run_maximum_historical_extension_qualification_v1.py --stage all
```

`probe` 会使用分段、可复核 receipts；参数中不写入 token。AkShare 的 upstream/network 失败会记录为 receipt，不会伪造成功。

## 下一步（仍属于资格化，不是模型阶段）

1. 以当前 frontier map 为候选集合，对 2000–2021 代表性样本补 corporate-action、adjustment continuity 与 Qlib/Tushare/BaoStock 数量级审计；
2. 对 2010–2017 做 market-wide quarterly row-count、announcement-delay、revision duplicate、report-type 和 lifecycle gap canary；
3. 对通过 canary 的最大共同区间才生成独立 identity 的 extended Matrix，并在 2021+ overlap 做 byte/schema/value consistency；
4. 若仍有任何 PIT/lifecycle blocker，保持 qualification 状态，不进入 Research Protocol redesign 或 Structured ML。

Governance flags：

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
