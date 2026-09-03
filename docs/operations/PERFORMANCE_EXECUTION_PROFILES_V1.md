# Performance Execution Profiles V1

> Program status: **CLOSED**. This document is the compact operational contract for
> the qualified Fast V2 and Full V3 execution profiles. Historical qualification
> plans and closeout context are archived in
> `docs/_archive/09_model_research_and_productivity_history/`.

## Status And Boundary

This is an execution-protocol engineering contract. It does not start Structured
ML, Phase 1 feature selection, Strategy V2, or any model competition. Frozen
`research_lightgbm_v1` and `fast_research_v1` remain unchanged 1-thread references.

The implementation separates frozen scientific inputs from execution-only choices:

```text
frozen LightGBM / Fast V1 semantics
        +
explicit execution-only thread override
        +
real-input identity and parity audit
        =
versioned performance evidence
```

No profile in this document grants scientific model-selection or Strategy authority.
The default Full performance/development profile is `full_research_accelerated_v3`;
its exact qualification and reference chain are pinned by the profile YAML and V3
report. `full_research_exact_mt_v2` remains the exact execution reference.

## Repository Audit Conclusion

- The frozen loader in `model_research/lightgbm_models.py` correctly enforces
  `num_threads == resources.threads == 1` for historical V1.
- Before this change, only the small policy canary accepted a thread override. The
  real development arm and Fast V1 were coupled directly to the frozen 1T config.
- Prediction did not consistently receive an explicit execution thread policy.
- Projection/spool cache already had content-addressed identity and corruption
  checks, but Full remained cache-off and no reusable real thread audit existed.
- Prior broad 1T/8T results were useful evidence, but their aggregate metric delta
  could not locate the first divergence or distinguish topology from leaf changes.
- This workstation has 8 physical / 16 logical cores. The prior broad peak near
  17 GiB means worker count must be bounded by RAM as well as CPU.

## Thread Determinism Audit

Bounded real-workload diagnostic:

```powershell
python scripts/audit_lightgbm_thread_determinism_v1.py `
  --config configs/lightgbm_thread_determinism_audit_v1.yaml `
  --output-dir outputs/performance_execution_v1/thread_audit_<run_id>
```

Fail-closed complete Full qualification:

```powershell
python scripts/audit_lightgbm_thread_determinism_v1.py `
  --config configs/lightgbm_thread_determinism_full_qualification_v1.yaml `
  --output-dir outputs/performance_execution_v1/full_qualification_<run_id>
```

The audit holds one prepared train/validation dataset constant and records hashes
for feature order, dates, transformed matrices, target, weights, row keys, labels,
preprocessing, LightGBM version, seeds, candidate table, and thread environment.
Only `num_threads` changes.

Machine-readable outputs include:

- `input_identity.json`;
- `runs.csv` and `thread_scaling.csv`;
- `candidate_metrics.csv`;
- `parity.csv` with exact, numerical, and scientific/ranking comparisons;
- `runtime_timing.csv` and `access_audit.csv`;
- `summary.json` with the fastest exact and scientifically equivalent thread counts.

Tree comparison separately hashes split feature, threshold, decision type, default
direction, missing type, and child topology, then compares aligned leaf values.
Prediction comparisons include exact hash/array, max and mean absolute difference,
RMSE, Pearson, Spearman, daily rank agreement, daily Rank IC, mean Rank IC, ICIR,
candidate ordering, and selected candidate.

The bounded config can never authorize Full MT. The Full qualification config is
accepted only when it uses complete development folds, all three representative
policies, all four structural rows, and all four checkpoints. Even then, the summary
sets `full_authoritative_eligible` only when a thread count above 1 reaches exact
parity and every same-thread repeat is exact.

After that evidence exists, the guarded Full runner accepts only a thread count in
the summary's exact set, re-hashes every qualification output, and verifies that the
evidence belongs to the unchanged frozen LightGBM config:

```powershell
python scripts/run_research_lightgbm_full_mt_v2.py `
  --output-dir outputs/performance_execution_v1/full_mt_<run_id> `
  --runtime-dir outputs/research_lightgbm_v1/runtime/full_mt_<run_id>
```

The default `full_research_exact_mt_v2` profile pins the frozen 1T config, the 8T
thread count, and the exact qualification summary hash. Without complete and intact
exact-parity evidence, this command fails closed.

## Fast MT V2

`fast_research_mt_v2` inherits the frozen Fast V1 dates, candidates, preprocessing,
metrics, and resource-gate semantics. It changes only the execution thread count and
remains non-authoritative screening evidence.

First run the dedicated calibration scope, which covers both development splits,
all three policies, and the exact frozen Fast dates/candidates:

```powershell
python scripts/audit_lightgbm_thread_determinism_v1.py `
  --config configs/lightgbm_thread_determinism_fast_mt_qualification_v1.yaml `
  --output-dir outputs/performance_execution_v1/fast_mt_qualification_<run_id>
```

```powershell
python scripts/run_fast_research_mt_v2.py `
  --proposal <proposal_id> `
  --output-dir outputs/research_productivity_v1/fast_runs/<run_id>
```

The coordinator runs 8T first. It automatically runs unchanged Fast V1 at 1T when
the MT result is inconclusive or lies within the configured margin of the promotion,
rejection, or zero-delta boundary. If confirmation runs, the final resource-gate
status comes from 1T. Fast remains a resource allocator, never a scientific winner
selector.

The dedicated Fast qualification has completed. Across both development splits,
all three policies, four frozen Fast candidates, 1/2/4/8T, and two repeats, every
tree, leaf value, prediction, metric, candidate order, and selected candidate was
exact. The guarded loader revalidated all output hashes and accepted 8T. Observed
8T speedups versus 1T were:

| Workload | split_001 | split_002 |
|---|---:|---:|
| strict | 3.27x | 3.27x |
| conditional | 2.87x | 3.31x |
| broad | 3.30x | 3.06x |

Fast MT V2 is therefore execution-qualified at 8T for screening, with the automatic
1T boundary fallback retained. This does not grant scientific selection authority.

## Full MT Qualification Result

The complete-fold Full qualification has completed for real `split_001` strict,
conditional, and broad workloads, all 16 frozen candidates, and two repeats at each
thread count.

- 8T versus 1T: exact topology, leaf values, predictions, daily Rank IC, mean Rank
  IC, ICIR, candidate ordering, and selected candidate on every workload/candidate.
- 8T same-thread repeats: exact.
- 2T and 4T: topology and ranking/metrics remained identical, but seven of 48
  candidates had leaf differences up to `4.07e-19` and prediction differences up to
  `2.78e-17`; these counts are scientific-parity only, not exact.
- First divergence for 2T/4T was `leaf_values`; for 8T it was `none`.
- 8T speedup versus 1T was 3.65x strict, 3.81x conditional, and 3.99x broad.
- Broad peak RSS rose from about 9,695 MiB at 1T to 10,234 MiB at 8T.

The evidence therefore authorizes the new `full_research_exact_mt_v2` execution
profile at 8T. Historical Full V1 remains the immutable 1T reference. No old artifact
is modified, and this execution result does not change model selection or Strategy
authority.

## CPU And RAM Planning

Generate worker/thread combinations that do not oversubscribe physical cores or
the current available RAM budget:

```powershell
python scripts/plan_research_resources_v1.py `
  --output-dir outputs/performance_execution_v1/resource_plan_<run_id>
```

The output is a benchmark candidate list, not an authorization. Workload-specific
wall time, CPU utilization, peak RSS, and I/O evidence must still choose among the
safe combinations. A broad worker is omitted when current available RAM cannot fit
its configured peak plus reserve.

## Current Evidence And Remaining Qualification

A real-input smoke run on `split_001 × strict_current_baseline`, 10 train dates,
5 validation dates, and `structure_01 @ 100` verified the end-to-end audit path:

- LightGBM 4.6.0;
- 1T and 2T each repeated twice;
- same-thread repeats exact;
- 2T versus 1T tree topology, leaf values, predictions, daily Rank IC, candidate
  order, and selected candidate exact;
- mean training-run wall time: 1T `0.3447 s`, 2T `0.2510 s`, or `1.37x` speedup.

This smoke evidence is deliberately non-qualifying and does not authorize Full MT.
The broader controlled evidence below supersedes it for thread diagnosis.

The bounded three-policy audit has now also completed on real `split_001` inputs
using 120 train dates, 77 validation dates, the four frozen Fast candidates, and two
repeats at 1/2/4/8T. Every comparison was exact:

| Workload | 2T speedup | 4T speedup | 8T speedup | 8T peak RSS |
|---|---:|---:|---:|---:|
| strict | 1.66x | 2.53x | 3.20x | 731 MiB |
| conditional | 1.65x | 2.72x | 3.26x | 1,133 MiB |
| broad | 1.53x | 2.10x | 2.95x | 3,241 MiB |

Across all three workloads, topology, leaf values, prediction arrays, daily Rank IC,
mean Rank IC, ICIR, candidate ordering, and selected candidate had zero difference.
The first divergence was therefore `none`; same-thread repeats were also exact.

This controlled result changes the interpretation of the older broad evidence. The
old 1T baseline predated stage instrumentation, while the 8T run came from the later
instrumented/optimized execution. Its report did not retain matched input arrays or
tree evidence, so the observed `0.03324` aggregate metric delta cannot be uniquely
attributed to thread count. The new single-runner audit controls those variables and
does not reproduce the divergence on the bounded real scope. Complete-fold Full
qualification is still required before authorizing Full MT, and the two-split Fast
qualification is still required before running Fast MT V2.
