# Research Protocol V2 Authority

## Status

Research Protocol V2 / Purged Rolling Split V2 is the frozen time-series research
protocol for the next separately authorized Structured ML V1 development stage. The
protocol is ready; formal LightGBM, DoubleEnsemble, representation, hyperparameter,
or training-window competition has not started.

The machine-readable design is
[`configs/research_protocol_v2.yaml`](../../../configs/research_protocol_v2.yaml). Exact
date assignments, audits, source receipts, Qlib capability findings, comparison
tables, and the final report are under
[`reports/research_protocol_v2/`](../../../reports/research_protocol_v2/REPORT.md).

## Evidence authority

```text
Historical Matrix V2 (frozen)
        ↓
5 development validation environments
        ↓
development-only candidate comparison
        ↓
candidate or inconclusive conclusion frozen
        ↓
7 historical diagnostic environments + 3 legacy V1 anchors
        ↓
future naturally arriving evidence
```

- Development evidence may select architecture, representation, registered
  hyperparameters, expanding versus `sliding_504`, and retraining cadence.
- Historical diagnostic evidence is `post_observation_research /
  historical_diagnostic_only`. It may explain stability or failure but may not
  change a selected candidate.
- Forward evidence remains the only prospective evidence. Existing Strategy V1
  predictions, paper portfolio, and Forward Track are unchanged.

## Temporal contract

The label interval is `[t+1, t+21]`: next-session entry and 20-session holding
return. Every training sample must have `label_end < evaluation_start`. This exact
interval purge removes 21 pre-boundary feature dates.

V2 applies no additional fixed embargo. V1 first removed the 21 overlapping dates
and then removed another 20 already-safe dates from the same side of each boundary.
That V1 behavior remains preserved for historical reproduction but is not carried
forward without a distinct dependence hypothesis.

Five development environments use two-month validation periods at three-month
cadence from May 2023 through June 2024. The intervening month lets labels mature;
the generator additionally checks the actual trading calendar and removes any tail
whose label would reach the next environment. All development labels mature before
the 2024-08-01 diagnostic boundary.

Two training-history hypotheses are registered:

- `expanding`: all legally mature prior dates;
- `sliding_504`: the last 504 legally mature dates, approximately two trading years.

No other training length may be added after outcomes are observed within the same
experiment version.

## Model-selection contract

Every candidate is evaluated on the same five environments. The primary summary is
the equal-fold mean of daily Rank IC; paired fold delta, worst fold, dispersion,
negative-fold count, prediction coverage, and failures are mandatory.

A challenger replaces a simpler incumbent only when paired mean and median deltas
are positive, at least three of five folds are wins, and no fold fails. Otherwise
the result is tie/inconclusive. Each registered experiment changes one axis and may
contain at most eight candidates; failed trials count toward the budget.

Time-dependent feature eligibility, preprocessing, feature selection, and fitting
use task train dates only. Validation and historical diagnostic data cannot decide
eligibility. The globally qualified 765 factors remain a physical candidate set,
not a model whitelist.

## Qlib boundary

The pinned Qlib commit remains
`d5379c520f66a39953bad76234a7019a72796fd0`; no upgrade is required. Its
`RollingGen` can materialize ordinary expanding/sliding segments after legal dates
are known, but it is not the split authority because it does not express exact
per-sample label intervals or project evidence roles. Recorder, TaskManager, and
Collector integration is deferred until actual Structured ML experiment volume
demonstrates a net reduction in complexity.

## Next-stage gate

Structured ML V1 may begin only in a later task that:

1. reads this frozen protocol and exact assignments;
2. preregisters candidate manifests before fitting;
3. runs development tasks first;
4. freezes a candidate or inconclusive decision before unlocking diagnostics;
5. never treats historical diagnostics as fresh OOS;
6. leaves Strategy V1 and its Forward evidence untouched.
