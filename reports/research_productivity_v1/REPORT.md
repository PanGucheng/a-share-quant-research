# Research Productivity V1

## Conclusion

This stage adds a strict filesystem projection/spool cache and a separately named,
non-authoritative Fast Research execution class. It does not change the model,
candidate table, dates, preprocessing, float64/single-thread defaults, selection
rules, final refit, freeze, historical release, or portfolio behavior of the existing
Full development path. The shared timing schema only gained
`execution_class`/`execution_profile` context.

Fast Research V1 is useful as a development-only resource screen, but not as a
scientific winner selector. On two existing mixed feature-pool proposals it reproduced
all four split-level Rank IC delta directions and achieved delta Spearman 0.60, while
the aggregate ordering of the two proposals was reversed. Both calibration proposals
therefore remain `inconclusive` and require Full development evaluation.

## Reviewed reality

With split, feature pool, development dates, and Matrix v4 fixed, changing only model
hyperparameters previously repeated feature authority resolution, projection, label
join, spooling, preprocessing, memmap materialization, and Dataset construction. The
existing runner already reused one LightGBM Dataset within an arm and trained each
structural row once to its maximum checkpoint; there was no hidden 16-fit bug.

The representative instrumented broad Full arm measured projection at 194.73s and
spooling at 98.31s, about 11.9% of the controlled 8-thread run. The exact shares of the
older 180-minute single-thread arm remain unrecoverable because it predates stage
timing. In the final Fast broad cache benchmark, projection plus spooling was 99.07s,
or 66.7% of cold pre-model preparation.

Canary cannot replace Fast Research. It uses only 20 train dates, 10 validation dates,
two structural rows at 100 rounds, and repeated fits to test determinism. It emits no
paired proposal promotion decision and is primarily a correctness/smoke test; its
date and candidate scope is too small for reliable research ranking.

## Cache design and benchmark

The implemented cache covers the raw development projection/spool artifact, including
row keys, labels, transformed target, and daily weights. Its content-addressed identity
binds Matrix artifact and selected partition hashes, factor catalog, split and fold,
feature membership and order, exact date scope, Labels artifact and payload hash,
target configuration, dtype, date batch size, and normalized producer AST hash.
`policy_id` is deliberately not part of the identity.

Every hit verifies manifest identity, Parquet file hash/size/schema/row count, feature
order, eligibility receipt hash, and row-key hashes. Test scope is rejected before any
materialization. Missing entries rebuild automatically; corrupt entries are rejected
and explicitly rebuilt under `corrupt_rebuilt`. Cache files live under ignored `tmp/`
and are immutable/content-addressed.

Representative `split_001 × broad_data_qualified`, 659 features, 120 train dates and
77 validation dates:

| Measure | Cold | Warm |
|---|---:|---:|
| Projection | 69.78s | 0.00s |
| Spooling | 29.29s | 0.00s |
| Cache validation | 0.00s | 3.37s |
| Overall pre-model preparation | 148.48s | 37.24s |
| Peak RSS | 4228.59 MiB | 4284.49 MiB |
| Cache footprint | 1,415,606,559 bytes | same |

Cold-to-warm pre-model speedup is **3.99×**. The 55.9 MiB higher warm RSS is an
order/process-residency effect, so the cache is not claimed to reduce peak memory.
Cold and warm feature, target, weight, feature-order, row-key, downstream prediction,
and downstream metric hashes are identical. Detailed evidence is in
`cache_benchmark.csv`, `cache_parity.json`, and `cache_receipt.json`.

Other intermediates were deliberately not cached:

| Intermediate | Decision |
|---|---|
| Matrix feature loading | Matrix partitions are already persistent; authority/hash validation remains fail-closed each run. |
| Projection/raw spool | Cross-model reusable under the implemented strict identity. |
| Preprocessed train/validation matrix | Depends on train scope and preprocessing config; large lifecycle/disk cost, so V1 rematerializes it. |
| LightGBM Dataset | Reused only inside one arm; depends on Dataset params and is not a safe portable cross-process artifact. |
| Labels/targets | Labels are already persistent; eligible target/weight arrays are cached only as part of the identity-bound spool. |
| Row/index metadata | Row keys are included and hashed in the spool; standalone metadata is not cached. |

## Fast Research V1 profile

The frozen profile is `configs/fast_research_v1.yaml`:

- execution class `exploratory_fast`;
- `split_001` and `split_002`; observed `split_003` is excluded;
- 120 deterministic, evenly spaced train dates across each complete development train
  history, kept in chronological order;
- the complete 77-date validation fold for each split;
- full real feature membership/order for baseline and proposal;
- structural rows `structure_01` and `structure_04`, checkpoints 100/200: four logical
  candidates from two max-200 fits;
- the same label, target transform, train-only preprocessing, metric implementation,
  seed, float64 dtype, and single thread as Full;
- no final refit, model serialization, test release, replay, or portfolio release.

The CLI accepts alternate feature/policy manifests for a preregistered proposal and
binds their hashes into the proposal receipt, so a later authorized clustering
ablation can use the same frozen compute profile without adding its policy id to
source code. Structural model-parameter experiments are not silently accepted by V1;
changing the frozen LightGBM parent requires a new Fast profile version.

One split was rejected because existing Full development evidence has opposite delta
directions between splits 001 and 002. A 60/30 trial was fast but achieved only 50%
sign agreement and delta Spearman -1. A tail-120/full-validation trial still produced
a false rejection. The final evenly sampled train history restored 4/4 direction
agreement while remaining minutes-scale.

## Fast versus Full development

| Proposal pair | Fast | Full reference | Speedup | Fast peak RSS | Full peak RSS |
|---|---:|---:|---:|---:|---:|
| Conditional signal vs strict | 288.28s (4.80m) | 9,934.79s (2.76h) | 34.46× | 2506.65 MiB | 11202.36 MiB |
| Broad vs strict | 596.94s (9.95m) | 25,587.49s (7.11h) | 42.86× | 4610.36 MiB | 17985.63 MiB |

Calibration across the four proposal/split comparisons:

- Rank IC delta sign agreement: **100% (4/4)**;
- ICIR delta sign agreement: **75% (3/4)**;
- Rank IC delta Spearman: **0.60**;
- aggregate ordering of the two proposals: **not reproduced**.

This is adequate for quickly rejecting proposals that are clearly and consistently
bad, retaining proposals that are clearly and consistently promising for Full, and
marking mixed/small deltas inconclusive. Marginal proposals, cross-split instability,
exact candidate winners, full candidate ordering, final-fit behavior, and any
historical/portfolio conclusion must wait for Full.

The pre-registered promotion rule is only a compute-resource gate. It requires a mean
Rank IC delta of at least +0.005 with both splits positive to emit
`promote_to_full`, or at most -0.005 with both splits non-positive to emit
`reject_before_full`; all other cases are `inconclusive`. None of these statuses is a
selected model, production winner, Strategy V2 authorization, or scientific result.

## Scientific and access contract

Both real calibration pairs recorded:

```text
test_feature_read_count       = 0
test_label_read_count         = 0
historical_replay_count       = 0
portfolio_test_release_count  = 0
```

Fast output paths are restricted to the configured ignored non-authoritative root;
cache paths are restricted to `tmp/research_productivity_v1`. The Fast module exposes
no historical replay operation and refuses a `test` fold before loading dates. Its
artifacts always carry all four authority flags as false. The representative receipt
is preserved as `fast_research_receipt.json`.

The Full model path remains cache-off by default and retains its prior execution
semantics. The reusable cache is consumed by Fast V1 only in this change; using it in
Full can be considered later from the demonstrated numerical parity without coupling
this stage to the frozen path.

## Limitations and next stage

Calibration covers only two existing feature-pool proposals and two development
splits. It supports screening utility, not universal ranking reliability. Cache disk
cost is substantial for broad pools (1.32 GiB for one split/profile scope), and warm
validation still hashes all files and row keys. Fast uses fewer candidates and fewer
train dates, so it cannot identify the Full candidate winner.
Fast V1 directly supports feature-pool/projection proposals; a hyperparameter or
architecture Fast profile must be separately versioned because V1 binds the complete
parent LightGBM and preprocessing contracts.

The workflow is now technically suitable for reopening a separately authorized
clustering ablation as `Canary → Fast Research → Full Research`. Fast results must be
used only to allocate Full-run resources; they do not reopen Strategy V1, create
Strategy V2, or provide new holdout evidence.
