# Long-History Robust Core Factor Selection V1 — Phase 0 Report

> Status: **CLOSED / COMPLETED**
>
> Completed: 2026-09-02
>
> Evidence class: retrospective development evidence; not fresh OOS evidence and
> not Strategy V2 authority.

## 1. Scope and result

Phase 0 completed the authorized sequence:

```text
Old-Conclusion Freeze
        → Same-Era Reconciliation
        → Canonical Backward Replication
```

It did not evaluate 765 factors, select a new core, change a direction, train a
model, run a portfolio search, or begin Phase 1. Strategy V1 and Forward evidence
remain unchanged.

The preflight froze 21,073 provenance rows covering 708 historical factors. The
actual metric engine consumed exactly 91 unique factors:

| Source membership | Count |
|---|---:|
| Strategy V1 only | 52 |
| Mature economic only | 39 |
| Overlap | 0 |
| Explicit extras | 0 |
| Total unique computation factors | 91 |

Each Strategy V1 membership row remains `unsigned_membership`: membership alone is
not a standalone alpha-direction claim. All 52 factors also have a separate,
consistent rolling-stability direction authority, so the factor-level replication
can calculate frozen-direction metrics for them. The mature 39 use their
`economic_predeclared` directions. Consequently, the computation universe has 91
signed factors and zero factors whose only available authority is membership.

## 2. Old evidence provenance and same-era reconciliation

The workflow verified the canonical identity, the Strategy V1 52 count and ordered
feature hash, the mature 39 count, source SHA256 identities, computation-universe
identity, canonical research eligibility, and unique inventory keys before reading
factor values. Old stability, selection, rejection, direction, and cluster records
were retained as provenance; they did not add factors to computation.

The old rolling-stability evidence supplies 936 comparable
`factor × inner-fold × train/validation` metrics for the 52 Strategy V1 factors.
Canonical replay over the exact old dates produced:

| Reconciliation status | Row count |
|---|---:|
| `consistent` | 911 |
| `minor_drift` | 22 |
| `material_data_semantic_change` | 3 |
| `not_comparable` | 39 |

The 39 `not_comparable` rows are the mature economic factors: their old report
records sleeve-level outcomes, not factor-level metrics. Phase 0 therefore records
`no_old_factor_level_metric` instead of manufacturing a pseudo-precise comparison.
This limitation does not prevent a canonical-with-canonical period comparison, but
it must accompany its interpretation.

Fifty of the 52 Strategy V1 factors are fully consistent at factor level. The only
material fold differences are:

| Factor | Material rows | Maximum observed absolute mean-IC difference |
|---|---:|---:|
| `kunquant_alpha101_alpha050` | 1 | 0.00555 |
| `kunquant_alpha101_alpha062` | 2 | 0.00736 |

Both factors are explicitly identified by canonical lineage as historical and
continuation recomputations under the corrected stable-horizon membership-axis
implementation. The differences are therefore expected data/implementation
semantic reconciliation findings, not evidence that the canonical authority is
broken. Phase 1 must use canonical evidence rather than treating their old metrics
as numerically interchangeable; Historical Data Engineering remains CLOSED.

## 3. Backward portability

The fixed periods use `label_20d_t1`. The final period ends at the label-mature
signal date 2026-05-11, not the canonical data end 2026-06-09.

| Period | Actual signal range | Eligible trading dates |
|---|---|---:|
| `early_2010_2014` | 2010-01-29–2014-12-31 | 1,193 |
| `mid_2015_2018` | 2015-01-05–2018-12-28 | 975 |
| `preexisting_2019_2020` | 2019-01-02–2020-12-31 | 487 |
| `legacy_2021_2026` | 2021-01-04–2026-05-11 | 1,293 |

The 91 factor-level portability classifications are:

| Status | Count |
|---|---:|
| `persistent` | 26 |
| `stronger_early` | 23 |
| `weaker_early` | 16 |
| `recent_regime_concentrated` | 13 |
| `direction_conflict` | 13 |
| `insufficient_history` | 0 |
| `unsigned_feature` | 0 |

For the mature 39 alone, the counts are 6 persistent, 4 stronger early, 10 weaker
early, 11 recent-regime concentrated, and 8 direction conflict.

### Economic conclusions

- **Speculation:** all four factors are `persistent`. Abnormal turnover, amount
  intensity, turnover volatility, and volume ratio retain their frozen negative
  directions in every period. This is the clearest backward-confirmed sleeve.
- **Reversal:** `mature_reversal_1m` is `stronger_early`; overnight return is
  `direction_conflict`. The broad reversal idea survives, but its two measurements
  are not interchangeable.
- **Liquidity:** Amihud illiquidity is positive in 2010–2018 and 2021+, but reverses
  in 2019–2020, yielding `direction_conflict`. The old liquidity conclusion is
  regime-sensitive rather than uniformly portable.
- **Value:** the eight-factor sleeve has positive average frozen-direction IC in all
  four periods, but factor-level evidence is heterogeneous: two persistent, one
  stronger early, two weaker early, and three direction conflicts. Value is broadly
  portable as a family, not as a claim that every valuation measure is stable.
- **Low risk / lottery:** sleeve-average directional IC is positive in every period.
  Two factors are stronger early, two weaker early, and two recent-regime
  concentrated. The family is portable with material component/regime variation.
- **Momentum / trend:** raw 12–1 momentum and the 52-week-high anchor are positive
  mainly in 2019–2020 and negative in the other broad periods. Their predeclared
  continuation directions are recent-window concentrated and conflict with a
  general long-history persistence claim.
- **Fundamentals:** profitability is positive in the earlier three periods but near
  zero on average in 2021+; accounting quality is slightly negative in 2010–2014
  and stronger later; investment/growth remains positive on average in all four
  periods. Fundamentals are mixed and measurement-dependent, not one stable block.
- **Institutional flow:** the four factors are positive mainly in 2015–2020 and
  negative on average in both 2010–2014 and 2021+, so the old flow hypothesis is
  strongly regime-dependent.

These labels describe unchanged-direction historical behavior only. They are not
new `selected`, `rejected`, `promoted`, `stable_core`, or core-candidate decisions.

## 4. Engineering evidence

The cold fixed-union metric pass read 272 effective canonical partition segments,
produced 358,294 daily Rank IC rows, and observed a largest in-memory factor block
of about 417 MiB. Metric computation took 3,147.7 seconds; the full cold run took
3,223.4 seconds. A cache-backed closeout replay took 75.5 seconds and read no factor
partition again. Parent Strategy V1, stability, clustering, economic, and canonical
sources were rehashed after the run and remained byte-identical.

Runtime outputs are under
`outputs/long_history_core_factor_selection_v1/phase0/current/` and include the
frozen inventory, actual computation universe, period calendar, factor-period
metrics, reconciliation, portability, comparison, conflicts/gaps, resolved config,
and run summary.

## 5. Limitations and authority boundary

- The old mature-economic evidence is sleeve-level, so its factor-level same-era
  comparison is explicitly unavailable.
- Same-era thresholds classify metric differences; they do not prove a causal data
  source for every small drift.
- The 2010–2026 results are retrospective development evidence and cannot become a
  fresh holdout through relabeling.
- Phase 0 does not authorize a Small Stable Alpha Core, Feature Quality Gate,
  candidate board, clustering pruning, FDR rescreen, Structured ML, portfolio
  optimization, Strategy V2, or a change to Strategy V1/Forward evidence.

Phase 0 is CLOSED / COMPLETED. Phase 1 remains NOT STARTED and requires a separate
implementation instruction after this evidence is reviewed.
