# Canonical Historical Dataset Assembly & Data Engineering Closure V1

> 状态：`canonical_research_authority`；Historical Data Engineering：`CLOSED`。本阶段未读取模型 outcomes，未启动 Dataset / Research Protocol redesign、Structured ML 或任何模型/策略工作。

## 最终数据 authority

- Canonical dataset identity: `canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423`
- Final range: `2010-01-29` 至 `2026-06-09`
- Defined / research-usable / blocked factors: `774` / `765` / `9`
- Canonical manifest rows: `498`
- Historical recomputed / referenced partitions: `48` / `384`
- Continuation corrected annual partitions: `36`
- Continuation frozen parent references: `30`

该 identity 是后续 Dataset / Protocol research 的唯一推荐 Matrix 输入。旧 frozen Matrix、旧 partial-extension 与 lineage-resolved historical Matrix 继续作为 immutable evidence，不再作为新研究默认输入。

## 2021+ continuation decisions

实际在 2021+ 重算 `35` 个因子：15 个 Alpha101、`ta_momentum_kama` 与 19 个 Fundamental。15 个 Alpha101 还对 2010–2021 historical segment 重新生成 48 个 versioned partitions，以保证 warm-up 与 target period 使用完整 dated membership axis；每个横截面 rank 继续重新施加 PIT eligibility。KAMA 在完整时间轴上统一为从 2000-01-04 anchor 开始的 causal recursive state；Fundamental 使用合并 2008+ historical cache 与 frozen continuation cache 后的 practical reconstructed PIT。

其他因子只在既有 overlap lineage 已证明语义一致时引用 frozen continuation；没有为了 overlap 好看而恢复 frozen bug，也没有无意义地全量重算。

Corrected factors:

```text
kunquant_alpha101_alpha015, kunquant_alpha101_alpha017, kunquant_alpha101_alpha034, kunquant_alpha101_alpha038, kunquant_alpha101_alpha050, kunquant_alpha101_alpha050_canonical_vwap_v2, kunquant_alpha101_alpha062, kunquant_alpha101_alpha062_canonical_vwap_v2, kunquant_alpha101_alpha077, kunquant_alpha101_alpha077_canonical_vwap_v2, kunquant_alpha101_alpha078, kunquant_alpha101_alpha078_canonical_vwap_v2, kunquant_alpha101_alpha085, kunquant_alpha101_alpha098, kunquant_alpha101_alpha098_canonical_vwap_v2, mature_accruals_to_assets, mature_asset_growth_yoy, mature_book_leverage, mature_book_to_market_pit, mature_cash_ratio, mature_cashflow_quality, mature_cashflow_to_price_pit, mature_cashflow_to_sales, mature_current_ratio, mature_earnings_to_price_pit, mature_gross_margin, mature_gross_profitability, mature_net_income_growth_yoy, mature_net_margin, mature_operating_cashflow_to_assets, mature_operating_profitability, mature_return_on_assets, mature_revenue_growth_yoy, mature_sales_to_price_pit, ta_momentum_kama
```

## 连续性与边界验证

- Partition integrity: `True`
- Timeline/key continuity: `True`
- Factor semantic continuity: `True`
- Implementation regime breaks: `0`
- 2021-01 / 2021-02 boundary implementation breaks: `0`
- Practical PIT checks: `True`
- Practical historical universe checks: `True`
- Causal KAMA continuation/state contract: `True`
- Alpha101 prefix/full-horizon stability: `True`
- Unexplained lineage mismatch: `0`

`boundary_jump_analysis.csv` 记录边界前后每个因子的横截面中位数与 coverage 变化。数值跳变没有被自动解释为实现断点；本阶段通过相同 authoritative implementation、逐因子 lineage 和 parent-difference evidence 排除了静默 regime change。市场变化、财报事件与月度 universe 变化仍保留为真实输入变化。

## PIT、universe 与 qualification

Fundamental 继续执行 `information_available_date <= decision_date`、latest-public-revision 和 same-day atomic event contract；没有重新开启大规模 statement authority 研究。Universe 继续采用 practical historical universe，并逐年验证 continuation keys 与 dated intervals 完全一致。

774 个 schema definitions 不等于 774 个均可研究使用。Factor Universe V2 的 765 个 global physical-data-qualified candidates 与 9 个 blocked factors 原样继承；blocked 清单及原因见 `factor_lineage.csv`，其中 KCP 仍因 non-finite values blocked。

## Lineage 与 immutability

- Parent lineage-resolved Matrix: `extended-matrix:22fbf692d22e97a90d3b63ad1258f4867be38f5476494e27fbf68d5825cc38f0`
- Frozen continuation evidence: `a6aa2d7298d13842c8112939f485a628e1b755bf03e4609276068595032a1899`
- Old artifact integrity: `True`
- Old artifacts overwritten: `False`

`partition_manifest.csv` 明确每个 effective segment 的 source path、hash、parent、reused/recomputed action 与 implementation version；`old_artifact_integrity.csv` 对 frozen、partial-extension 和 lineage-resolved evidence 做独立完整性核验。

## 阶段关闭

Historical Data Engineering 正式 `CLOSED`。项目不再保留“继续寻找更早历史、继续 source authority、继续 lifecycle canary”之类默认开放项；只有发现明确 data bug、leakage 或 provenance failure 时才重开。

Canonical dataset 已具备下一阶段 Dataset / Research Protocol redesign 的数据条件：`True`。本任务到此停止；没有设计 folds/windows、没有修改 Research Protocol、没有运行任何模型或 Structured ML。
