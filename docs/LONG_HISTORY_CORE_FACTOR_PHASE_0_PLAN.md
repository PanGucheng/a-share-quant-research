# Long-History Core Factor Selection V1 — Phase 0 Development Plan

> Status: **CLOSED / COMPLETED**
>
> Scope: freeze old conclusions and perform an unchanged-membership,
> unchanged-direction backward replication on canonical history.
>
> This plan does not authorize Phase 1+, factor reselection, or Strategy V1 changes.
>
> Closeout: [Phase 0 Report](../reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md)

## 1. Deliverable

Build one small, read-only workflow that converts the relevant old conclusions into
a frozen provenance inventory, defines a much smaller explicit computation universe,
reconciles old evidence against canonical data in the same era, and only then
evaluates backward portability across declared canonical periods. It must not change
any old factor role, direction, membership, report, or artifact.

Definition of done:

```text
verified old-conclusion snapshot
        +
explicit computation-universe snapshot
        +
same-era reconciliation
        +
predeclared period calendar
        +
direction-aware backward metrics
        +
old-versus-new interpretation table
        +
focused tests and a compact report
```

## 2. Inputs to Reuse

All inputs are read-only.

| Evidence | Existing source | Phase 0 use |
|---|---|---|
| Canonical identity/partitions | `outputs/canonical_historical_dataset_assembly_v1/current/{manifest.json,partition_manifest.csv,factor_lineage.csv}` | Validate identity; read partitions through effective-date filters |
| Canonical reader | `research_validation/canonical_dataset.py` | Reuse `read_effective_partition` and segment/continuity validation |
| Strategy V1 52 | tracked `artifacts/prospective_forward_candidate_v1/.../forward_candidate_preprocessing.json` plus frozen candidate receipt | Read `feature_names` in frozen order and verify count/hash |
| Old stability roles/directions and metrics | `outputs/factor_rolling_stability_v2/current/{factor_stability_board.csv,factor_direction_history.csv,factor_window_metrics.csv,resolved_config.json}` | Freeze roles/directions with `outer_split_id`, recover documented metric/range semantics, and retain metadata without implying computation inclusion |
| Old selected/rejected history | `outputs/factor_rolling_stability_v2/current/factor_selection_history.csv` | Preserve old decisions and reason fields as provenance only |
| Old clustering | `outputs/factor_clustering_v2/current/representatives_by_split.csv` and `factor_clusters_by_split.csv` | Freeze representative and cluster metadata only; cluster membership does not imply computation inclusion |
| Mature 39/economic sleeves | `reports/economic_multi_factor_research_v1/{economic_map.csv,literature_evidence_map.csv,daily_rank_ic.csv,manifest.json}` | Select exactly `research_role == selected_sleeve_member`; attach mechanism/direction and use recorded evidence only where metric semantics and era are compatible |
| Evaluation math | Factor Evaluation V4/project evaluator, `research_validation.multiple_testing`, and existing rolling helpers | Reuse metric semantics; do not copy evaluator formulas |

If a runtime-only parent is absent, fail with a precise missing-input message. Do not
silently substitute an older artifact with a similar filename.

## 3. Frozen Semantics

Before any metric calculation, write an inventory with one row per
`factor × old_source × old_context`. Preserve split-specific roles rather than
collapsing them into a synthetic global role.

Required fields:

```text
factor
old_source
old_context
old_role
old_direction
direction_status
direction_authority
old_cluster_id
old_is_representative
old_order
computation_included
computation_inclusion_reason
source_path
source_artifact_id_or_sha256
```

Rules:

- Strategy V1 order is immutable and must contain exactly 52 unique factors.
- The mature economic set must contain exactly 39 unique factors.
- Conflicting directions across old sources are retained as separate contextual
  rows and reported; they are not resolved using backward results.
- Strategy V1 feature membership alone has `direction_status=unsigned` and
  `direction_authority=unsigned_membership`. It does not create a signed-alpha claim.
- A signed direction may only come from a documented old authority, such as
  `inherited_from_rolling_stability` or `economic_predeclared`.
- Without an authoritative direction, `old_direction` is null, frozen-direction
  metrics are not computed or interpreted, and standalone direction is
  `not_comparable`; backward results may not fill the gap.
- Missing factors, duplicate keys, unverified source identities, or disagreement
  with the frozen factor count fail closed.
- Phase 0 emits no `selected`, `promoted`, `rejected`, or new `stable_core` decision.

## 4. Actual Computation Universe

The provenance inventory may retain all old stability, selection, rejection, and
cluster records, but the metric engine consumes only a separate frozen computation
allowlist.

Default membership is the deduplicated union of:

1. the frozen Strategy V1 52-factor membership;
2. the 39 mature economic factors; and
3. optional explicit extras listed in configuration with a frozen conclusion source
   and a non-performance-based inclusion reason.

No old rejected, monitor, conditional, or cluster member enters computation merely
because its metadata was loaded. Before loading factor values, write:

```text
computation_universe.csv
factor
strategy_v1_member
mature_economic_member
explicit_extra
inclusion_reason
direction_status
direction_authority
```

The run summary must report provenance-row count, unique provenance-factor count,
computation-factor count, source-set overlap, and optional-extra count. It must fail
if the actual computation set differs from the frozen allowlist. Phase 0 must remain
far smaller than a 669- or 765-factor run.

## 5. Same-Era Reconciliation and Period Contract

### Same-Era Reconciliation

For each comparable old conclusion, locate its recorded metric, metric definition,
evaluation range, universe, factor semantics, and direction authority. Replay the
factor from canonical data over the same documented signal range before interpreting
early-history differences.

Required fields:

```text
factor
old_source
old_metric_name
old_metric_value
old_signal_start
old_signal_end
canonical_same_era_metric_value
metric_definition_compatible
factor_semantics_compatible
universe_comparable
direction_comparable
reconciliation_status
reconciliation_reason
```

Allowed status values are `consistent`, `small_semantic_drift`,
`material_data_semantic_change`, and `not_comparable`. Missing definitions or ranges
must become `not_comparable`, not guessed. The fixed `legacy_2021_2026` period below
is not a substitute for exact same-era reconciliation.

### Backward Portability

Declare these wall-clock environments in configuration before running:

| Period ID | Requested range | Role |
|---|---|---|
| `early_2010_2014` | `2010-01-29`–`2014-12-31` | backward replication |
| `mid_2015_2018` | `2015-01-01`–`2018-12-31` | backward replication |
| `preexisting_2019_2020` | `2019-01-01`–`2020-12-31` | backward replication |
| `legacy_2021_2026` | `2021-01-01`–`2026-06-09` | comparison with the era that informed old work |

Use `label_20d_t1` only. For each period, intersect the requested range with the
canonical trading calendar, factor effective dates, and label maturity. Record
requested and actual signal start/end, eligible date count, and exclusion reason.
Do not move period boundaries after metrics are visible. Do not use period outcomes
to change old directions. Backward portability interpretation must carry the
same-era reconciliation status so data/semantic drift is not mislabeled as a time
regime effect.

## 6. Minimal Code Shape

Add only:

```text
configs/long_history_core_factor_phase0_v1.yaml
factor_research/backward_replication.py
scripts/run_long_history_core_factor_phase0_v1.py
tests/test_backward_replication.py
```

Responsibilities:

- config: canonical identity, exact source paths, fixed periods, label, minimum
  computability rules, and output locations;
- module: verified provenance and computation-universe assembly, same-era
  reconciliation, period alignment, direction-aware metric aggregation, and
  comparison-table construction as ordinary functions;
- script: thin CLI orchestration and explicit error reporting;
- tests: small synthetic frames for frozen-direction, period, identity, and
  immutability semantics.

Do not add a manager, registry, new evaluator backend, new cache layer, or a general
pipeline framework.

## 7. Metrics and Outputs

Compute only the evidence needed for replication:

- raw Rank IC per day and frozen-direction Rank IC only where an old direction
  authority exists;
- period median/mean Rank IC, ICIR, positive-date ratio, date/sample coverage;
- direction consistency versus the frozen direction;
- optional existing quantile spread only if it is already available without a
  second factor-frame pass.

Write runtime outputs under:

```text
outputs/long_history_core_factor_selection_v1/phase0/current/
```

Required files:

```text
old_conclusion_inventory.csv
computation_universe.csv
period_calendar.csv
factor_period_metrics.csv
same_era_reconciliation.csv
backward_portability.csv
old_vs_new_comparison.csv
conflicts_and_gaps.csv
resolved_config.json
run_summary.json
```

The tracked closeout report, created only after a successful run, belongs at:

```text
reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md
```

`same_era_reconciliation.csv` separates data/semantic compatibility from temporal
portability. `backward_portability.csv` may use fixed reason categories such as
`consistent`, `weaker_early`, `stronger_early`, `direction_conflict`,
`insufficient_history`, or `not_comparable`, but must retain the reconciliation
status. These are interpretations, not new selection roles.

## 8. Implementation Sequence

### Work unit A — Preflight and freeze

1. Verify canonical manifest identity and required runtime parents.
2. Load the Strategy V1, stability, selection-history, clustering, and economic
   sources.
3. Build and validate `old_conclusion_inventory.csv` without loading factor values.
4. Materialize and freeze the smaller `computation_universe.csv`.
5. Stop if counts, uniqueness, hashes, source relationships, or allowlist identity
   fail.

Acceptance:

- 52 Strategy V1 names and 39 mature names are independently verified;
- split-specific old roles/directions remain intact;
- unsigned Strategy V1 membership remains unsigned unless another old authority is
  explicitly joined;
- provenance factors outside the frozen computation allowlist are not read by the
  metric engine;
- the workflow can prove which source supplied every field;
- no existing file changes.

### Work unit B — Same-era reconciliation smoke

1. Select one comparable factor deterministically from configuration.
2. Load its old metric definition, exact range, universe, semantics, and direction
   authority.
3. Replay that exact range from canonical data.
4. Produce one reconciliation row and exercise each compatibility status in
   synthetic tests.

Acceptance:

- missing old definitions/ranges yield `not_comparable`;
- metric, semantic, universe, and direction compatibility are separate fields;
- canonical replay never mutates the old record;
- no backward portability claim is produced without reconciliation status.

### Work unit C — Calendar and one-factor backward smoke

1. Materialize `period_calendar.csv` from canonical calendar and label maturity.
2. Choose one factor from the frozen inventory by deterministic config, not by
   performance.
3. Read it through the canonical effective-partition API.
4. Produce four period rows and verify actual dates/coverage.

Acceptance:

- no row lies outside its period or factor effective range;
- the final signal date has a mature 20D label;
- a deliberate future-label fixture fails;
- missing early history becomes `insufficient_history`, not zero IC.

### Work unit D — Fixed-universe replication

1. Evaluate the deduplicated frozen computation universe once; join results back to
   all relevant old-source/context rows.
2. Reuse cached factor frames/daily IC when identities match.
3. Generate comparison and conflict tables.
4. Record runtime, row counts, cache hits, and peak-memory observation in the
   summary; do not optimize prematurely.

Acceptance:

- changing an old direction is impossible through result data;
- unsigned factors remain unsigned and have no interpreted signed metric;
- duplicate factors are computed once but preserve all old contexts;
- repeated identical runs are deterministic;
- no Strategy V1, old report, or old output is written.

### Work unit E — Closeout

1. Run focused pytest tests and the repository fast quality tier.
2. Run Markdown link/documentation checks and `git diff --check`.
3. Write a compact report separating backward evidence from the later Phase 1–6
   selection work.
4. Review the full diff before commit and push under the repository's direct-main
   workflow when the implementation task explicitly includes delivery.

## 9. Focused Tests

At minimum:

1. wrong canonical identity fails before data reads;
2. effective-date filters exclude invalid partition rows;
3. 52/39 count drift fails;
4. provenance-only factors never enter the metric engine;
5. computation allowlist count/identity drift fails;
6. duplicate inventory keys fail;
7. unsigned membership cannot acquire a direction from replay results;
8. frozen directions remain unchanged when early IC has the opposite sign;
9. incompatible or missing same-era definitions yield `not_comparable`;
10. reconciliation status accompanies every backward interpretation;
11. period endpoints and label maturity are enforced;
12. insufficient coverage is explicit and never filled with zero;
13. one computed factor can map back to multiple old contexts;
14. output ordering and interpretation reason codes are deterministic;
15. all parent sources remain byte-identical after the run.

## 10. Explicit Non-Goals

- no evaluation of all 765 factors;
- no Feature Quality Gate implementation;
- no new pillar grades or thresholds;
- no candidate promotion or Core Team Selector;
- no factor direction flip, membership change, or old-report correction;
- no model training, TopK/rebalance/horizon search, or portfolio optimization;
- no Strategy V1 or Forward evidence mutation.

Phase 0 closed only the backward-replication question. Phase 1 remains NOT STARTED
and begins later under a separate implementation task after Phase 0 outputs and
limitations are reviewed.
