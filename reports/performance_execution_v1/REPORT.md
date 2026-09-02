# Performance Execution V1

## Decision

Controlled real-input audits qualify LightGBM 8T for both new execution profiles:

- `fast_research_mt_v2`: exact across the complete frozen Fast scope and still
  protected by automatic 1T confirmation near resource-gate boundaries;
- `full_research_exact_mt_v2`: exact across complete-fold strict, conditional, and
  broad representative workloads and eligible for authoritative Full execution.

Frozen Fast V1 and Full V1 remain unchanged 1T historical references. These are
execution decisions only; model selection, Strategy V1, Structured ML, and Strategy
V2 authority are unchanged.

## Determinism

Fast qualification covered both development splits, three policies, four frozen
Fast candidates, 1/2/4/8T, and two repeats. Every thread count was bitwise exact.

Full qualification covered complete train/validation folds for `split_001`, three
policies, all 16 candidates, 1/2/4/8T, and two repeats:

- 8T: exact tree topology, leaf values, prediction arrays, daily Rank IC, mean Rank
  IC, ICIR, candidate order, and selected candidate;
- 2T/4T: topology and all ranking/scientific outputs identical, with leaf differences
  up to `4.07e-19` and prediction differences up to `2.78e-17` in seven of 48
  candidates;
- same-thread repeats: exact for every thread count;
- first divergence: `leaf_values` for affected 2T/4T candidates, `none` for 8T.

The older `0.03324` broad delta compared an uninstrumented historical 1T baseline
with a later instrumented/optimized 8T execution and did not retain matched inputs or
tree evidence. It was not a controlled thread-only comparison. The new audit fixes
all non-thread variables and does not reproduce that divergence.

## Performance

Full-scope mean wall-clock speedup versus 1T:

| Workload | 2T | 4T | 8T | 8T peak RSS |
|---|---:|---:|---:|---:|
| strict | 1.38x | 2.36x | 3.65x | 1,388 MiB |
| conditional | 1.39x | 2.36x | 3.81x | 2,426 MiB |
| broad | 1.38x | 2.43x | 3.99x | 10,234 MiB |

Fast-scope 8T speedups were 2.87x–3.31x across the six split/policy workloads.

The RAM-aware planner omits unsafe worker/thread combinations. With broad Full near
10 GiB RSS on this 8-core workstation, the current safe broad default is one worker
with 8 LightGBM threads. Outer-worker throughput benchmarking remains required for
lighter arms before selecting a multi-worker default.

## Evidence

- `bounded_real_audit_v1/`: initial three-policy real audit;
- `fast_mt_qualification_v1/`: complete Fast MT qualification;
- `full_mt_qualification_v1/`: complete Full MT qualification;
- `resource_plan_v2/`: CPU/RAM-safe benchmark candidates.

Each qualification directory contains input identity, candidate metrics, tree/leaf/
prediction/ranking parity, timing, access audit, scaling, and a hashed summary. The
runtime loaders re-hash these files before enabling the pinned profiles.

## Remaining Work

- benchmark actual outer-worker contention for light/medium arms;
- run explicit Full cache-off/cache-on parity before enabling projection/spool cache
  in the Full execution path;
- evaluate preprocessing-matrix cache only if measured reuse benefit justifies its
  disk and memory cost;
- continue non-LightGBM batching/vectorization work separately.
