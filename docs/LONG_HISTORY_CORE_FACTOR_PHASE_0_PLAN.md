# Long-History Core Factor Selection V1 — Phase 0 Development Plan

> Status: **READY FOR IMPLEMENTATION / NOT STARTED**
>
> Scope: freeze old conclusions and perform an unchanged-membership,
> unchanged-direction backward replication on canonical history.
>
> This plan does not authorize Phase 1+, factor reselection, or Strategy V1 changes.

## 1. Deliverable

Build one small, read-only workflow that converts the relevant old conclusions into
a frozen comparison inventory and evaluates those fixed conclusions across declared
canonical periods. It must produce evidence about long-history portability without
changing any old factor role, direction, membership, report, or artifact.

Definition of done:

```text
verified old-conclusion snapshot
        +
predeclared period calendar
        +
fixed-direction backward metrics
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
| Old stability roles/directions | `outputs/factor_rolling_stability_v2/current/factor_stability_board.csv` and `factor_direction_history.csv` | Freeze roles and directions with `outer_split_id` retained |
| Old selected/rejected history | `outputs/factor_rolling_stability_v2/current/factor_selection_history.csv` | Preserve old decisions and reason fields |
| Old clustering | `outputs/factor_clustering_v2/current/representatives_by_split.csv` and `factor_clusters_by_split.csv` | Freeze representative and cluster metadata only |
| Mature 39/economic sleeves | `reports/economic_multi_factor_research_v1/economic_map.csv` and `literature_evidence_map.csv` | Select exactly `research_role == selected_sleeve_member`; attach mechanism and expected direction |
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
old_cluster_id
old_is_representative
old_order
source_path
source_artifact_id_or_sha256
```

Rules:

- Strategy V1 order is immutable and must contain exactly 52 unique factors.
- The mature economic set must contain exactly 39 unique factors.
- Conflicting directions across old sources are retained as separate contextual
  rows and reported; they are not resolved using backward results.
- Missing factors, duplicate keys, unverified source identities, or disagreement
  with the frozen factor count fail closed.
- Phase 0 emits no `selected`, `promoted`, `rejected`, or new `stable_core` decision.

## 4. Period Contract

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
to change old directions.

## 5. Minimal Code Shape

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
- module: verified inventory assembly, period alignment, fixed-direction metric
  aggregation, and comparison-table construction as ordinary functions;
- script: thin CLI orchestration and explicit error reporting;
- tests: small synthetic frames for frozen-direction, period, identity, and
  immutability semantics.

Do not add a manager, registry, new evaluator backend, new cache layer, or a general
pipeline framework.

## 6. Metrics and Outputs

Compute only the evidence needed for replication:

- raw and frozen-direction Rank IC per day;
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
period_calendar.csv
factor_period_metrics.csv
old_vs_new_comparison.csv
conflicts_and_gaps.csv
resolved_config.json
run_summary.json
```

The tracked closeout report, created only after a successful run, belongs at:

```text
reports/long_history_core_factor_selection_v1/PHASE_0_REPORT.md
```

`old_vs_new_comparison.csv` must describe observations with fixed reason categories
such as `consistent`, `weaker_early`, `stronger_early`, `direction_conflict`,
`insufficient_history`, or `not_comparable`. These are interpretations, not new
selection roles.

## 7. Implementation Sequence

### Work unit A — Preflight and freeze

1. Verify canonical manifest identity and required runtime parents.
2. Load the Strategy V1, stability, selection-history, clustering, and economic
   sources.
3. Build and validate `old_conclusion_inventory.csv` without loading factor values.
4. Stop if counts, uniqueness, hashes, or source relationships fail.

Acceptance:

- 52 Strategy V1 names and 39 mature names are independently verified;
- split-specific old roles/directions remain intact;
- the workflow can prove which source supplied every field;
- no existing file changes.

### Work unit B — Calendar and one-factor smoke

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

### Work unit C — Fixed-union replication

1. Evaluate the deduplicated union of frozen factors once; join results back to all
   old-source/context rows.
2. Reuse cached factor frames/daily IC when identities match.
3. Generate comparison and conflict tables.
4. Record runtime, row counts, cache hits, and peak-memory observation in the
   summary; do not optimize prematurely.

Acceptance:

- changing an old direction is impossible through result data;
- duplicate factors are computed once but preserve all old contexts;
- repeated identical runs are deterministic;
- no Strategy V1, old report, or old output is written.

### Work unit D — Closeout

1. Run focused pytest tests and the repository fast quality tier.
2. Run Markdown link/documentation checks and `git diff --check`.
3. Write a compact report separating backward evidence from the later Phase 1–6
   selection work.
4. Review the full diff before any commit; commit/push only on a separate explicit
   instruction.

## 8. Focused Tests

At minimum:

1. wrong canonical identity fails before data reads;
2. effective-date filters exclude invalid partition rows;
3. 52/39 count drift fails;
4. duplicate inventory keys fail;
5. frozen directions remain unchanged when early IC has the opposite sign;
6. period endpoints and label maturity are enforced;
7. insufficient coverage is explicit and never filled with zero;
8. one computed factor can map back to multiple old contexts;
9. output ordering and interpretation reason codes are deterministic;
10. all parent sources remain byte-identical after the run.

## 9. Explicit Non-Goals

- no evaluation of all 765 factors;
- no Feature Quality Gate implementation;
- no new pillar grades or thresholds;
- no candidate promotion or Core Team Selector;
- no factor direction flip, membership change, or old-report correction;
- no model training, TopK/rebalance/horizon search, or portfolio optimization;
- no Strategy V1 or Forward evidence mutation.

Phase 0 closes only the backward-replication question. Phase 1 begins later under a
separate implementation task after Phase 0 outputs and limitations are reviewed.
