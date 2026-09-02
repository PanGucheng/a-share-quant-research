# Long-History Robust Core Factor Selection V1

> Status: **ACTIVE RESEARCH MAINLINE / PLANNING**
>
> Authorized now: route adoption, Phase 0 implementation planning, and continued
> time-priority Forward operations.
>
> Not started by this document update: research code, historical runs, candidate
> selection, or Core construction.

## 1. Objective

The canonical 2010–2026 research dataset is complete. The next historical research
mainline is no longer a generic Dataset / Research Protocol redesign and is not a
model competition. It is:

> From the 765 research-usable factors, identify the smallest maintainable set of
> long-history, stable, interpretable, mutually useful, and tradable alpha factors.

The target output is a **Small Stable Alpha Core plus complete research evidence**,
not Strategy V2. The work must answer what each retained alpha factor adds to the
team and what is lost if it is removed. Risk, conditioning, neutralization, market
state, and tradability controls remain a separate research object; lack of
standalone alpha does not remove a useful control from future research.

Canonical input identity:

```text
canonical-dataset:27518ddbb28ba2b4b1247375d4e3d32d7d5be9935a5f2074dc272f84285f6423
```

It covers `2010-01-29` through `2026-06-09`, with 774 definitions, 765
research-usable factors, and nine blocked factors. Effective-date filters and
lineage rules in [CANONICAL_RESEARCH_DATASET.md](CANONICAL_RESEARCH_DATASET.md)
remain mandatory.

## 2. Boundaries

This stage does not authorize:

- Strategy V2 or changes to frozen Strategy V1;
- model competition or large LightGBM/XGBoost/CatBoost comparisons;
- TopK, rebalance-frequency, or prediction-horizon search;
- neural networks, AutoML, or live trading;
- reinterpretation of observed history as fresh OOS evidence.

The Forward Track remains ACTIVE and time-priority. Strategy V1 predictions,
decisions, positions, trades, and NAV remain append-only. All 2010–2026 results from
this route are retrospective development evidence. `split_003` remains observed.

## 3. Implementation Principle

Use adaptation, orchestration, and a few small modules. Do not duplicate existing
evaluators or build a new governance framework.

Strongly reuse:

- canonical partitions and `research_validation/canonical_dataset.py`;
- `model_research/feature_eligibility.py`;
- Factor Evaluation V4 and its Alphalens Reloaded, jqfactor_analyzer, Qlib Eval,
  project evaluator, quantile, turnover, tradability, and context outputs;
- BH-FDR and rolling stability code;
- `reports/economic_multi_factor_research_v1/economic_map.csv` and
  `literature_evidence_map.csv`;
- Size, liquidity, microcap, limit/tradability diagnostics;
- daily-IC/exposure hierarchical clustering;
- canonical partitions, factor-frame/daily-IC caches, and the safe pure-compute
  projection/spool caches already established by Fast Research.

Keep but upgrade the ideas of `stable_core`, `conditional_signal`, rolling
stability, and clustering. Clustering becomes information-group metadata; one
representative per cluster is no longer a hard selection rule because Clustering
Ablation V1 produced mixed historical evidence.

## 4. Mainline

```text
Canonical Dataset 2010–2026
        ↓
Phase 0 — freeze old conclusions and backward replication
        ↓
Phase 1 — feature quality gate
        ↓
Phase 2 — long-history factor evidence
        ↓
Phase 3 — robust candidate board
        ↓
Phase 4 — economic and redundancy map
        ↓
Phase 5 — core team selector
        ↓
Phase 6 — stopping rule and sensitivity
        ↓
Small Stable Alpha Core + Robust Candidate Reserve
```

### Phase 0 — Old-conclusion freeze and backward replication

Freeze the Strategy V1 52-factor set, 39 mature economic factors, old stability
roles and directions, old economic sleeves, old selected/rejected decisions, and
old clustering representatives. The stability, selection, rejection, monitor,
conditional, and cluster records are provenance metadata; loading them does not
place their roughly 669-factor historical universe into Phase 0 computation.

The default Phase 0 computation universe is the deduplicated union of:

- frozen Strategy V1 52-factor membership;
- the 39 mature economic factors; and
- only a small number of explicitly allowlisted extras that have a concrete frozen
  historical conclusion and a documented inclusion reason.

The actual computation universe, count, source membership, and inclusion reason
must be written before factor values are loaded. Old rejected/monitor/conditional
factors and cluster members remain metadata-only unless explicitly allowlisted.
Phase 0 must not become a 669- or 765-factor run.

Strategy V1 membership is not a standalone signed-alpha claim. Each inventory row
must carry `direction_status` and `direction_authority`. Valid authorities include
`inherited_from_rolling_stability`, `economic_predeclared`, and
`unsigned_membership`. If no prior authority exists, `old_direction` is null,
backward results may not infer it, frozen-direction metrics are not interpreted,
and standalone direction is `not_comparable`.

Phase 0 has two ordered analyses:

1. **Same-Era Reconciliation** — compare old recorded evidence with a canonical
   replay over the same documented era and record metric-definition, factor-semantic,
   universe, and direction compatibility. Outcomes include `consistent`,
   `small_semantic_drift`, `material_data_semantic_change`, and `not_comparable`.
2. **Backward Portability** — only after reconciliation, compare canonical recent
   evidence with canonical early history, keeping data/semantic change separate
   from temporal instability.

Compare at least `2010–2014`, `2015–2018`, `2019–2020`, and the original `2021+`
era. Calendar and label maturity may trim actual signal dates, but boundaries may
not be chosen after viewing results. The output is interpretive evidence, not a new
selection decision, and old reports/artifacts remain unchanged.

Required comparison fields include:

```text
factor
old_source
old_role
old_direction
direction_status
direction_authority
computation_inclusion_reason
old_metric
canonical_same_era_metric
reconciliation_status
early_period_ic
mid_period_ic
recent_period_ic
direction_consistency
backward_portability_status
```

The concrete implementation plan is
[LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md](LONG_HISTORY_CORE_FACTOR_PHASE_0_PLAN.md).

### Phase 1 — Feature Quality Gate

Answer only whether a factor is research-eligible, not whether its alpha is strong.
Reuse the existing eligibility profiler and check canonical eligibility, PIT and
dependency correctness, enabled/runnable state, coverage, missingness, finite
dates/samples, variance, exact value duplicates, and deterministic numerical
duplicates.

Allowed outcomes:

```text
eligible
blocked
quality_failed
exact_duplicate
```

IC must not be used to reject a factor in this phase.

### Phase 2 — Long-History Factor Evidence

Adapt Factor Evaluation V4 to the canonical long-history input instead of
reimplementing IC, quantiles, turnover, or context analysis. Evaluate every eligible
factor with `label_20d_t1` as the main horizon and 10D only as auxiliary robustness;
do not start a horizon search.

Use a small set of historically meaningful, predeclared environments, initially:

```text
2010–2014
2015–2018
2019–2022
2023–2026
```

Actual valid signal boundaries must be derived from the trading calendar, canonical
effective dates, data availability, and label maturity and recorded in outputs.
Rolling statistics supplement these environments; they do not create dozens of
optimized windows.

### Phase 3 — Robust Candidate Board

Create the first genuinely new core module. Normalize evaluator outputs into four
economic pillars; multiple evaluator backends are measurements, not independent
votes.

1. **Predictive Strength** — median Rank IC, ICIR, BH-FDR, quantile spread,
   monotonicity, frozen-direction spread, and long-short behavior.
2. **Temporal Stability** — period median/worst IC, sign consistency, rolling
   stability, regime concentration, degradation, persistence, and coverage. This is
   the highest-priority pillar.
3. **Tradability** — rank autocorrelation, turnover, gross and cost-adjusted spread,
   liquidity/Size/microcap dependence, tradable-universe robustness, and limit or
   untradeable effects.
4. **Economic Robustness** — existing economic and literature maps used for
   priority, explanation, and tie-breaking, not as a no-literature hard reject.

Use `Data Gate + Pillar Grade + Pareto`, not a tunable 100-point weighted score.
Grades may be `A/B/C/D`, with fixed reason codes and thresholds justified from
existing distributions, literature, and engineering semantics—not reverse-engineered
to obtain a desired candidate count.

### Phase 4 — Economic and Redundancy Map

Combine economic family, literature evidence, exact duplicates, daily-IC
similarity, exposure similarity, and existing hierarchical clusters. Correlation and
cluster membership explain information groups and later grouped ablations; they do
not automatically delete `N-1` factors.

### Phase 5 — Core Team Selector

Build the core incrementally rather than taking a Top-N ranking. Version 1 must be
transparent: daily cross-sectional rank, frozen direction, standardization, and
equal or economic-family-balanced weights. It does not optimize weights.

For `Core(N) + candidate X`, compare paired changes in:

- median IC, ICIR, quantile spread;
- worst-period IC, dispersion, positive-period count, and rolling stability;
- turnover, cost-adjusted spread, and liquidity dependence;
- correlation, economic-mechanism overlap, and worst-period diversification;
- Size, liquidity, microcap, and concentration exposure.

Forward greedy selection may be used, but admission must be a multi-objective
marginal improvement, not optimization of a single metric. Greedy construction is
itself a potential data-mining surface, so admission requires stable improvement
across historical environments: period-wise paired marginal evaluation,
worst-period behavior, and leave-one-environment-out robustness. Full-history
aggregate improvement alone may not admit a factor. The selector must identify
factors that repeatedly improve the team, not the ex-post optimal 2010–2026
combination.

### Phase 6 — Stopping Rule and Sensitivity

Generate a deterministic marginal-benefit/core-size curve. Do not predetermine a
target count. Stop when consecutive additions provide little predictive, worst-period,
net-spread, or stability improvement relative to turnover, complexity, instability,
and redundancy. Stopping thresholds must be declared independently of the desired
Core size and may not be tuned until a preferred count appears.

At minimum inspect sizes such as `1, 2, 3, 5, 8, 12, ...`, while retaining the full
sequential trace. Run focused sensitivity checks that preserve the declared horizon,
periods, costs, directions, and evidence boundary.

## 5. Required Final Outputs

1. **Small Stable Alpha Core** — a small, stable, interpretable, economically
   complementary, and tradable set whose primary role is expected-return prediction;
   it is the alpha candidate input to a future separately authorized Strategy V2
   research stage.
2. **Robust Candidate Reserve** — quality-passing factors with useful evidence that
   did not earn a place in the Core. It is not a 765-factor active ML pool.
3. **Risk / Conditioning Controls** — a separate inventory for Size, liquidity,
   industry, market state, tradability, and other neutralization, risk-control,
   conditional-modeling, or exposure-monitoring variables. These controls do not
   need standalone alpha and are not counted as Alpha Core members.
4. **Old-versus-new comparison** — Strategy V1 52 factors, 39 mature factors, old
   rejected factors, and the independent mechanisms contributed by Alpha101,
   Alpha158, Alpha360, and TA.
5. **Core-size and marginal-contribution evidence** — every admission and stopping
   decision must be reproducible and explainable.

The remaining factors stay in Factor Universe V2 without becoming Strategy V2
active features.

## 6. High-Risk Tests

Focus tests on:

1. canonical dataset identity and effective-date filtering;
2. no future data and label maturity;
3. exact duplicate detection;
4. frozen factor direction consistency;
5. period and calendar alignment;
6. no promotion of historical/observed evidence to fresh holdout;
7. pillar aggregation and reason codes;
8. period-wise paired `Core(N)` versus `Core(N+1)` comparison;
9. leave-one-environment-out admission robustness;
10. deterministic stopping with no target-size tuning;
11. clustering metadata never auto-deleting `N-1`;
12. Alpha Core membership remaining separate from risk/conditioning controls;
13. Strategy V1 artifacts never being modified.

## 7. Completion Criteria

The stage is complete only when it can answer:

- how many of 765 factors pass quality, predictiveness, stability, and tradability;
- which economic mechanisms the robust candidates cover;
- which old 52 and mature 39 receive long-history confirmation;
- whether any old rejected factors are rediscovered and why;
- how predictive and trading value change as core size grows;
- where marginal benefit becomes negligible;
- which factors form the Small Stable Alpha Core;
- which non-alpha variables remain Risk / Conditioning Controls; and
- for every core factor, what the team loses if it is removed.

Only after this stage closes may a separate decision authorize a simple
linear/composite baseline, then LightGBM, to test whether nonlinear interaction adds
value. Portfolio construction and Strategy V2 remain later, separately authorized
work.
