# ML Feature Pool Performance Optimization V1

## Conclusion

The real `split_001 × broad_data_qualified` profile shows that boosting is the largest measured stage, followed by weighted preprocessing and feature projection/spooling. The original 180-minute arm did not contain stage instrumentation, so its exact historical stage shares cannot be reconstructed; the adjacent timing rows are from the controlled 8-thread experiment and are not silently attributed to the old run.

The preserved nine-arm baseline totals 61,129.60 seconds (16.98 hours): 3,407.65 seconds for `strict_current_baseline`, 18,061.45 seconds for `current_plus_existing_conditional_signal`, and 39,660.50 seconds for `broad_data_qualified`.

## Representative measured profile

- Baseline arm: 10816.31s, 17015.48 MiB peak RSS.
- Experimental 8-thread arm: 2455.79s, 9766.87 MiB peak RSS, 4.40× faster.
- The thread experiment is rejected despite its speed: prediction hashes and candidate ordering changed and metric max-abs difference was 0.0332403585069.
- Selected candidate happened to remain `structure_04 @ 100`; this is insufficient for numerical parity.

| Stage | Wall seconds | Share |
|---|---:|---:|
| `lightgbm_training` | 1223.47 | 49.8% |
| `preprocessing_fit` | 664.00 | 27.0% |
| `feature_projection` | 194.73 | 7.9% |
| `feature_spooling` | 98.31 | 4.0% |
| `final_train_validation_fit` | 61.44 | 2.5% |
| `selected_model_retraining` | 53.77 | 2.2% |

## Kept exact optimizations

- Batched spool preprocessing: 13.48× on the 12,000 × 659 broad canary; median/mean exact, variance within strict float64 rounding.
- Stable weighted median avoids lexsorting canonical strings. Reordering observations tied on the same value cannot change the returned median value.
- Train/validation mappings and Dataset are released before final refit, avoiding overlapping large mapped matrices.
- Checkpoint reuse was already present and measured 1.99× with zero prediction/metric difference versus independent fits.
- Dataset reuse was already present: the four structural rows share one constructed train Dataset; the final train+validation scope correctly builds a separate Dataset.

The synthetic broad canary is reproducible with:

```powershell
E:\anaconda_envs\qlib_env\python.exe scripts/benchmark_ml_feature_pool_performance_v1.py
```

## Research semantics

No feature pool, split, label, target transform, candidate, checkpoint, selection rule, holdout/freeze/lineage rule, portfolio rule, or float64 execution dtype was changed. All benchmark outputs are diagnostic-only and unauthorized for model or Strategy V2 selection.

## Fast research mode

Not implemented in this change. A future profile should be a separately named, non-authoritative one-split proxy with `authoritative_execution=false`, `selection_authorized=false`, and `strategy_v2_authorized=false`.
