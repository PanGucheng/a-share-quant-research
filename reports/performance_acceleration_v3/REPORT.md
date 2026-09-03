# Research Compute Acceleration V3

## Status

Full data-preparation and preprocessing acceleration is qualified as an exact,
non-authoritative performance profile. Frozen `Fast V1`, `Full V1`,
`fast_research_mt_v2`, and `full_research_exact_mt_v2` are unchanged.

## Evidence

The complete `split_001` strict, conditional, and broad workloads were run through
the real Full development path with `cache OFF`, cache cold, and cache warm modes.
All modes matched exactly for feature preparation, targets, weights, row keys,
preprocessing payloads, transformed matrices, candidate predictions, metrics,
candidate ordering, selected candidate, mutation evidence, final model, and feature
importance. The qualification summary is in
[`full_qualification_v1/summary.json`](full_qualification_v1/summary.json).

Measured wall times were:

| Workload | OFF | Cold | Warm |
|---|---:|---:|---:|
| strict | 246.63s | 227.75s | 171.67s |
| conditional | 481.17s | 409.31s | 304.36s |
| broad | 1955.14s | 1647.15s | 1499.38s |

The projection/spool cache occupies about 6.73 GB for this scope; the fitted
preprocessing cache occupies about 1.1 MB. Cache validation is content-addressed
and corruption-rebuilding. The existing cache framework was extended rather than
replaced.

Cold preprocessing was benchmarked on 659 factors across batch sizes 16, 32, 64,
128 and worker counts 1, 2, 4, 8. Every combination was exact. The selected
engineering setting is `factor_batch_size=128`, `median_workers=8`: about 39.4s
versus about 159.6s for `16 × 1`, with about 2.66 GB peak RSS. Detailed evidence is
in [`preprocessing_benchmark_v1/`](preprocessing_benchmark_v1/).

The selected-candidate mutation check now reuses the prediction already produced
by candidate search, removing the duplicate selected-model training while retaining
the label-mutation contract. `WeightedPreprocessingFit.transform()` uses exact
NumPy broadcasting and is checked against the prior per-column implementation.

Runtime timing now records wall time, CPU time, core equivalent, RSS, and process I/O
bytes. The stage breakdown is in
[`full_qualification_v1/stage_breakdown.csv`](full_qualification_v1/stage_breakdown.csv).

## Scheduler and matrix-cache decision

The resource planner can derive per-workload RSS budgets from measured evidence with
a configurable safety multiplier. Broad remains one worker with eight LightGBM
threads; no outer-worker default is enabled without a contention benchmark.
The evidence-driven candidate plan is recorded in
[`resource_plan_v1/`](resource_plan_v1/), using the warm-profile RSS measurements
with a 15% safety multiplier and 2 GiB reserved RAM.

The new measurements show LightGBM training remains the dominant broad stage. A
large transformed-matrix cache was therefore not implemented: its disk footprint
would be materially larger than the fitted-state cache and the current measured
warm path does not justify that complexity.

This profile is performance evidence only. It does not authorize model selection,
Structured ML, Strategy V2, or replacement of any frozen research artifact.
