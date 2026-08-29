# Factor Universe V2 Historical Data & Matrix Readiness

> Status: `research_ready_with_blocked_factors`; scope: `full`. This is data qualification only and does not authorize Strategy V2.

## Outcome

- Matrix dates: `2021-02-01` to `2026-06-09`; instruments: `3983`; rows: `2,587,671`.
- Definitions/materializable/coverage-qualified/research-usable/blocked: `774/770/769/765/9`.
- `765 research-usable` is the global physical data-qualified candidate universe, not
  a fixed feature whitelist for every outer split. Time-dependent eligibility and
  selection must remain development-only and split-local.
- Qualification requires overall coverage >= `50%`, monthly coverage >= `35%` in at least `90%` of months, plus non-constant finite values.
- Bootstrap begins `2020-01-17`, exactly 252 provider trading sessions before the first research date; statement announcements begin `2018-01-01` to cover the prior-year comparators visible at research start.
- The 669 V1 factors and Matrix v4 partitions are referenced byte-for-byte; no old matrix, label, split, prediction, Forward, or Strategy V1 artifact was changed.

## Required answers

1. Required raw layers are Qlib OHLCV/amount/direct VWAP, a contemporaneous PIT-universe equal-weight market return, Tushare daily_basic, moneyflow, income, balancesheet, cashflow, and fina_indicator cross-check fields.
2. Only those frozen dependency layers were bootstrapped; no unrelated Tushare collection was added.
3. Per-source real coverage is listed below and in `raw_source_coverage.csv`.
4. Financial PIT is enforced from f_ann_date then ann_date; report period is never used as availability.
5. Same-day revisions prefer Tushare update_flag=1, then deterministic revision/hash order; independent statement revisions are joined as-of before factor computation.
6. Real data exposed same-date update_flag 0/1 duplicates, requiring the explicit priority above; Qlib amount was also confirmed as thousand CNY and is converted to CNY only in the V2 mature adapter.
7. Materializable definitions: `770` of 774.
8. Research-ready factors: `765`.
9. Temporarily blocked factors: `9`.
10. Block reasons are coverage failure, zero finite history, non-finite values, or constant/degenerate real values; definitions remain frozen and no values are fabricated.
11. Economic-family coverage is listed below and in `family_coverage.csv`.
12. Factor-month, instrument-family, split/fold, source and factor audits are preserved separately; expected listing/warm-up/PIT gaps are not forward-filled.
13. Units and magnitudes are checked in `unit_sanity.csv`; Tushare total_mv is converted from 10,000 CNY for PIT valuation and moneyflow is reconciled to Qlib amount converted from 1,000 CNY.
14. Canonical direct-VWAP factors are compared with legacy proxies in `canonical_legacy_comparison.csv`; recovered factors are independently materialized on real provider data.
15. V1 immutability is a critical manifest/hash contract.
16. Matrix shape is `2,587,671 × 774 defined factors` in partitioned form; only the explicit research-usable list is approved for later research.
17. The matrix covers every existing split range plus the configured label tail through 2026-06-09.
18. Bootstrap timing is recorded in `full_bootstrap_timing.csv`; finalization timing is in `resource_timing.csv`; disk sizes are summarized below and in the manifest.
19. Daily APIs are date-segmented; issuer statements are segment-cached with receipts, integrity hashes, gap detection and revision-aware re-fetch compatibility, so incremental updates reuse the same contract.
20. Economic Multi-Factor Research data readiness is `yes` for the qualified list only; no IC/model/winner/portfolio work occurred.

## Raw-source coverage

- `daily_basic`: 7,564,464 rows, 1546/1546 segments, observation=2020-01-17 00:00:00..2026-06-09 00:00:00, availability=NaT..NaT, missing availability=0, integrity=True.
- `moneyflow`: 7,328,434 rows, 1546/1546 segments, observation=2020-01-17 00:00:00..2026-06-09 00:00:00, availability=NaT..NaT, missing availability=0, integrity=True.
- `income`: 179,609 rows, 3983/3983 segments, observation=2013-12-31 00:00:00..2026-03-31 00:00:00, availability=2018-01-03 00:00:00..2026-08-28 00:00:00, missing availability=0, integrity=True.
- `balancesheet`: 176,102 rows, 3983/3983 segments, observation=2013-12-31 00:00:00..2026-03-31 00:00:00, availability=2018-01-03 00:00:00..2026-08-28 00:00:00, missing availability=0, integrity=True.
- `cashflow`: 187,051 rows, 3983/3983 segments, observation=2013-12-31 00:00:00..2026-03-31 00:00:00, availability=2018-01-03 00:00:00..2026-08-28 00:00:00, missing availability=0, integrity=True.
- `fina_indicator`: 132,779 rows, 3983/3983 segments, observation=2018-03-31 00:00:00..2026-03-31 00:00:00, availability=2018-04-04 00:00:00..2026-08-28 00:00:00, missing availability=0, integrity=True.

Later availability dates in the raw statement snapshot are provider revisions of
earlier report periods retrieved at bootstrap time. They do not enter earlier matrix
rows: the no-future contract checks all 2,587,671 aligned PIT keys against each
revision's actual availability date.

## Cross-check and resource evidence

- The provider `current_ratio` cross-check has 103,834 matched rows, correlation
  0.99999 and median relative difference 0.0012%. `cash_ratio` has 103,831 matched
  rows and correlation 0.856, but a 56.7% median relative difference; it is therefore
  supporting evidence of scale/direction only, not a claim of formula identity.
- Of 28 direct-VWAP canonical comparisons, 24 have observed real-data differences.
  `alpha027_canonical_vwap_v2` has no common finite observations because its adapter
  is blocked. `alpha062`, `alpha073`, and `alpha086` each have roughly 2.49–2.59
  million common finite observations but are exactly equal to legacy on this history.
  No positional relabel or fabricated value was used.
- Runtime raw cache: 1.14 GB across 38,048 data/receipt files. New V2 partitions:
  1.07 GB. Referenced byte-immutable V1 partitions: 7.27 GB.
- The completed restart pass validated 3,092 daily and 15,932 statement segments in
  1,682 seconds, reusing 10,652 statement segments and fetching the remaining 5,280.
  Recovery finalization took 1,272 seconds and peaked at about 6.24 GiB RSS. The
  original full factor build was observed at about 48 minutes with a 13.2 GiB peak;
  partition-level recovery avoids repeating that computation after late audit/report
  failures.

## Economic-family coverage

- `CashFlow`: coverage=99.995%, usable=2/2.
- `GrowthInvestment`: coverage=99.681%, usable=3/3.
- `Leverage`: coverage=100.000%, usable=1/1.
- `Liquidity`: coverage=99.767%, usable=125/125.
- `MomentumTrend`: coverage=97.577%, usable=84/85.
- `Multi`: coverage=94.242%, usable=71/76.
- `PriceTrend`: coverage=99.747%, usable=299/299.
- `Profitability`: coverage=98.307%, usable=5/5.
- `Quality`: coverage=97.916%, usable=4/4.
- `Reversal`: coverage=98.547%, usable=4/4.
- `Size`: coverage=99.867%, usable=3/3.
- `TradingBehavior`: coverage=96.402%, usable=49/51.
- `Value`: coverage=94.092%, usable=8/8.
- `VolatilityRisk`: coverage=99.291%, usable=107/108.

## Temporarily blocked definitions

- `kunquant_alpha101_alpha021` — zero_finite_values
- `kunquant_alpha101_alpha023` — zero_finite_values
- `kunquant_alpha101_alpha027` — zero_finite_values
- `kunquant_alpha101_alpha027_canonical_vwap_v2` — zero_finite_values
- `kunquant_alpha101_alpha068` — constant_or_degenerate
- `kunquant_alpha101_alpha086` — constant_or_degenerate
- `kunquant_alpha101_alpha086_canonical_vwap_v2` — constant_or_degenerate
- `ta_trend_psar_up` — insufficient_historical_coverage
- `ta_volatility_kcp` — non_finite_values

## Qualification semantics and closeout

- Hard readiness gates are the `critical=true` rows in `contract_status.csv`. Per-factor
  usability additionally requires materialization, temporal/overall coverage,
  non-degeneracy and finite values. Unit checks, provider cross-checks, canonical
  comparisons and detailed coverage distributions remain diagnostic evidence rather
  than independent hard publication gates.
- The ignored/local factor-month, split-fold and instrument-family audits are bound to
  this tracked artifact by SHA-256, row count and schema in `artifact_manifest.json`.
  Validate the complete closeout with
  `python scripts/validate_factor_universe_v2_matrix_closeout.py`.
- Matrix Readiness is `CLOSED`. Economic Multi-Factor Research and model research have
  not started, and Strategy V2 remains unauthorized.

## Boundary

No IC, FDR, clustering, SHAP, model training, feature importance, portfolio optimization or Strategy V2 change was performed. `split_003` remains observed and cannot become new selection evidence.
