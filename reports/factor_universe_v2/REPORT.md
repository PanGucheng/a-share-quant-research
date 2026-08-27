# Factor Universe V2 — Frozen Research Universe

> Status: `frozen_research_only`. This freezes factor definitions and lineage; it does not authorize Strategy V2 or modify Forward Track.

## Outcome

- Final universe: **774 unique factors** = 669 immutable V1 + 19 recovered + 28 canonicalized replacements + 58 new mature public factors.
- V1 catalog remains byte-identical (`7c7f18ff419b59ac2639d332cb5d0dc8edad2cc9d5a0b8bb33b5575dddb96aaa`); all 669 V1 names are inherited unchanged.
- New axes are Size, Value, Profitability, Quality, Growth/Investment, Leverage, Cash Flow, order-size Money Flow, direct liquidity and market/residual risk.
- Admission used formula/data/PIT/dependency gates only. No IC, FDR, return, model, SHAP, clustering or portfolio winner test was run.

## Answers to the required audit questions

1. **V1 composition:** 155 Alpha158 + 358 Alpha360 + 77 TA + 64 Alpha101 + 15 Project Basic = 669.
2. **Historical omissions:** `51` unique missing/held-out names were found after separating duplicate degraded annotations.
3. **Recoverable now:** `41` unique names were technically recoverable; the frozen recovery batch admits 19 distinct factors and keeps non-informative/invalid formulas out.
4. **Degraded implementations:** `32` unique proxy/degraded names are annotated.
5. **Amount/VWAP recovery:** 28 valid Alpha101 formulas receive direct-provider `$vwap` canonical versions; VPT/NVI get explicit missing-value semantics; new direct VWAP deviation, amount momentum and Amihud factors are added.
6. **Tushare dimensions:** verified probes cover daily size/value/turnover, money flow, statements/ratios, events, limits, margin, blocks/top lists, SW reference data and northbound holdings.
7. **Not adopted now:** no probed core API was permission-denied. Sparse event families are deferred for coverage/cost, SW industry factors for vintage uncertainty, and `disclosure_date.actual_date` for backfill risk.
8. **Safely PIT-able:** income, balance sheet and cash-flow fields with `f_ann_date` then `ann_date`; `fina_indicator` and announcement events with `ann_date` can be cross-checked while preserving revisions.
9. **Not safely PIT-able:** report period alone, current disclosure schedules as historical snapshots, and industry effective intervals without database-vintage evidence.
10. **External systems researched:** Qlib Alpha158/360, WorldQuant Alpha101, Alpha191, TA ecosystems, JoinQuant/RiceQuant public taxonomies, MSCI Barra-style families, classic anomaly papers, and China A-share anomaly/liquidity/order-flow literature.
11. **Admitted families:** 17 market/price/liquidity/risk, 12 daily-basic size/value/turnover, 10 order-size flow, and 19 PIT statement factors (`58` total).
12. **Rejected/deferred:** `3` rejected families and `3` deferred families are recorded in `external_factor_inventory.csv` with reasons.
13. **New economic information:** the V1 technical concentration is supplemented by accounting, valuation, capital structure, cash conversion, order-size behavior and systematic/residual risk.
14. **Economic-family counts:** `{'PriceTrend': 299, 'Liquidity': 125, 'VolatilityRisk': 108, 'MomentumTrend': 85, 'Multi': 76, 'TradingBehavior': 51, 'Value': 8, 'Profitability': 5, 'Reversal': 4, 'Quality': 4, 'GrowthInvestment': 3, 'Size': 3, 'CashFlow': 2, 'Leverage': 1}`.
15. **Duplicates:** two known Alpha360 constant formulas remain hard-excluded. Proxy/canonical and conceptual relationships are annotated; no admitted V2 name or explicit formula is duplicated.
16. **Final count:** 774.
17. **Legacy inheritance:** all 669 V1 factors, byte/name immutable.
18. **Recovered:** 19.
19. **Truly new:** 58.
20. **Canonical replacement candidates:** 28 direct-VWAP Alpha101 variants; legacy proxies are retained for lineage.
21. **History coverage:** local OHLCVA/VWAP covers the current split. Tushare documents the required historical ranges and probes pass, but full-market bootstrap coverage is an explicit pre-matrix gate and is not falsely claimed here.
22. **Resource cost:** roughly 6-16 GB raw Parquet for the core new layers; 774 columns are ~15.7% wider than 669 and ~8.1% wider than 716. See `resource_estimate.csv`.
23. **Incremental maintenance:** content-addressed Parquet segments, receipts/hashes, retries, missing-segment detection, one daily segment per post-close API, and revision-aware issuer updates for filings.
24. **Next-stage readiness:** yes for scoped V2 data bootstrap, canary matrix construction and economic-sleeve research. No for Strategy V2/production switching; observed holdout and Forward evidence remain untouched.

## Research basis and A-share interpretation

The [China A-share anomaly review](https://doi.org/10.1016/j.pacfin.2021.101607) finds stronger evidence for value, risk and trading signals than for broad size/quality/past-return groups, with reversal and residual effects as notable exceptions. [Size and Value in China](https://www.nber.org/papers/w24458) motivates China-specific earnings yield, size and turnover treatment. The China liquidity study identifies turnover as a particularly suitable local liquidity proxy, while [Amihud](https://doi.org/10.1016/S1386-4181(01)00024-6) supplies the amount-based price-impact definition. China order-imbalance research motivates, but does not pre-judge, the order-size flow candidates.

The accounting batch follows [gross profitability](https://www.nber.org/papers/w15940), [accrual/cash-flow quality](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2598), and public [MSCI Barra family coverage](https://www.msci.com/documents/1296102/1636401/MSCI_Barra_Market%2BEquity%2BModels_Factsheet%2B.pdf/0c9d381f-e4e6-42fc-b7c2-dfff694dd650). The code is an original, transparent implementation; no proprietary Barra formula and no unlicensed platform code was copied.

## PIT and feature-at-t contract

- Market, `daily_basic`, and `moneyflow` observations dated t are post-close data and first usable in the next trading session.
- Statement factors accept only rows whose `information_available_date <= decision date`; missing or future availability fails closed.
- `end_date` is a report-period key, never an availability fallback. Revisions are retained and selected as of each decision date.
- Tushare money-flow amounts are explicitly converted from 10,000 CNY before division by traded amount in CNY.

## Freeze artifacts

- `outputs/factor_universe_v2/current/factor_catalog_v2.yaml`
- `outputs/factor_universe_v2/current/factor_inventory_v2.csv`
- `outputs/factor_universe_v2/current/factor_dependency_v2.csv`
- `outputs/factor_universe_v2/current/freeze_manifest.json`
- Supporting audits are in `reports/factor_universe_v2/`.

## Boundary

Factor Universe V2 is research-only. It does not change the 52-feature Strategy V1 model, feature order, old matrices, historical releases, daily paper path or Forward evidence. Full data bootstrap and canary materialization must pass their own coverage/missingness/resource gates before empirical multi-factor or ML work.
