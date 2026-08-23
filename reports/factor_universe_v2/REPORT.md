# Factor Universe V2 — Pre-Network Checkpoint

> Status: `pre_network_checkpoint_not_frozen`. External mature-factor research and network factor expansion were intentionally not started.

## Outcome

- V1 remains byte-identical: `True` (`7c7f18ff419b59ac2639d332cb5d0dc8edad2cc9d5a0b8bb33b5575dddb96aaa`).
- V1 composition: `155` Alpha158 + `358` Alpha360 + `77` TA + `64` Alpha101 + `15` Project Basic = `669` legacy factors.
- Historical missing/disabled unique factors audited: `51`; recoverable now: `41`.
- Degraded/proxy-based unique implementations annotated: `32`.
- Pre-network local candidate catalog: `716` = `669 legacy + 19 recovered + 28 canonicalized VWAP replacements`.
- Current token probes: `20/20` APIs callable; an empty forecast slice is recorded as accessible-empty, not failure.
- No factor was admitted or rejected because of IC, FDR, return, clustering, or model results.

## What was recovered

- Alpha158: CNTN5, IMAX5 and RANK5 are restored because their old holdout reason was an evaluation partial-pass, not data incorrectness.
- Alpha101: 12 locally valid formulas previously held out by evaluation are restored; 6 zero-valid-output formulas remain blocked.
- TA: BBLI and KCHI evaluation holdouts are restored. VPT and NVI receive new canonical V2 implementations with explicit `pct_change(fill_method=None)`.
- Alpha101 VWAP: 28 locally valid formulas get separate canonical variants using the provider's direct `$vwap`; the historical amount/volume-plus-epsilon versions are retained for lineage.
- Alpha360 CLOSE0/VOLUME0 constants, three TA return duplicates and two forward-shifted visual Ichimoku outputs remain excluded.

## Data capability

The community provider already has open/high/low/close/volume/amount/VWAP plus adjustment fields across the audited 6,106 feature directories. Tushare probes confirm current access to daily size/value/turnover, money flow, statements, financial ratios, events, price limits, margin, block trades, top-list data, SW classification/membership and northbound holdings.

Official references: [permission table](https://tushare.pro/document/1?doc_id=108), [daily_basic](https://tushare.pro/document/2?doc_id=32), [moneyflow](https://tushare.pro/document/2?doc_id=170), [cashflow](https://tushare.pro/document/2?doc_id=44), [fina_indicator](https://tushare.pro/document/2?doc_id=79), [disclosure_date](https://tushare.pro/document/2?doc_id=162).

The 2000-point account can call the probed core APIs, but this does not prove unlimited full-market bootstrap throughput. The implemented segment store therefore caches Parquet segments, writes token-free hashes/receipts, resumes partial downloads, validates schema, and supports incremental updates.

## PIT and revisions

- Statements use `f_ann_date` first and `ann_date` second. `end_date` is never an availability fallback.
- Financial ratios and event tables use their announcement date; missing availability stays `research_pending`.
- All source revisions are retained and deterministically ordered. As-of reads select only revisions announced by the decision date.
- `disclosure_date.actual_date` is not treated as a historical feature because a current table can backfill the eventual actual date.
- No fundamental or flow factor enters this checkpoint catalog until full bootstrap coverage and PIT canaries pass.

## Candidate composition

- Source counts: `{'alpha101': 104, 'alpha158': 158, 'alpha360': 358, 'project_basic': 15, 'ta': 81}`
- Lineage counts: `{'canonicalized': 28, 'legacy_v1': 669, 'recovered': 19}`
- Economic-family counts: `{'PriceTrend': 299, 'Liquidity': 119, 'VolatilityRisk': 100, 'MomentumTrend': 83, 'Multi': 76, 'TradingBehavior': 37, 'Reversal': 2}`

## Explicit stop boundary

Not started: Alpha191, JoinQuant/RiceQuant/BigQuant definitions, new academic anomaly research, A-share literature review, or any other internet-sourced factor expansion. Therefore this checkpoint is not the frozen Factor Universe V2 and is not authorization for Matrix V5, Model/Strategy V2, or multi-factor winner research.

## Files

- `historical_missing_factor_audit.csv`
- `data_capability_v2.csv` and `tushare_probe_receipt.csv`
- `factor_recovery_inventory.csv` and `factor_expansion_candidates.csv`
- `economic_taxonomy.csv`, `duplicate_equivalence_audit.csv`, `pit_audit.csv`
- `data_source_decisions.csv`, `resource_estimate.csv`, `limitations.json`
