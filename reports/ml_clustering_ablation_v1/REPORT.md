# Clustering Ablation V1 — Historical Diagnostic Report

## Outcome

`historical_pattern = mixed`

Removing the one-representative-per-cluster hard gate helped Full development in two of three splits, but historical Rank IC and fixed P01 improved in only one of three splits. The evidence does not support calling the gate either uniformly information-losing or uniformly useful denoising.

- `decision_authority=diagnostic_only`
- `selection_authorized=false`
- `strategy_v2_authorized=false`
- Historical tests were already observed; this is not fresh OOS or an unbiased estimate.

## Policy identity

- split_001: A=45, D=454, D-A=409 stable_core non-representatives.
- split_002: A=46, D=234, D-A=188 stable_core non-representatives.
- split_003: A=52, D=209, D-A=157 stable_core non-representatives.

D preserves frozen A order and appends eligible non-representatives in `source_family,factor` order. Stable-core roles, FDR, windows, thresholds, clustering, eligibility, preprocessing, model candidates, seeds, and P01 were not recomputed.

The frozen eligibility intersection excluded 6/4/5 stable-core factors: 14 split-factor rows were duplicate columns and one had insufficient coverage. All passed correctness checks; exclusions are recorded explicitly.

## Canary and Fast Research

Canary passed deterministic prediction hashes, finite predictions, candidate-table parity, train-only preprocessing, and zero historical-test reads.
- Fast split_001: Rank IC D-A +0.033527; ICIR D-A +0.084543; D cold/warm 165.6/104.4s; D cold/warm peak RSS 3302.0/3159.9 MiB.
- Fast split_002: Rank IC D-A -0.005023; ICIR D-A -0.041143; D cold/warm 99.6/56.1s; D cold/warm peak RSS 2067.7/1977.4 MiB.
- Fast promotion status: `inconclusive`; under frozen semantics this was promoted to Full.
- Cold/warm metric and selected-candidate parity was exact; all warm projection caches hit.

## Full development

- split_001: Rank IC D-A +0.030530; ICIR D-A +0.088870.
- split_002: Rank IC D-A -0.007580; ICIR D-A -0.053391.
- split_003: Rank IC D-A +0.014907; ICIR D-A +0.064744.
- Equal-split mean Rank IC D-A: +0.012619; positive splits: 2/3.

## Historical diagnostic replay

- split_001: Rank IC D-A -0.015196; ICIR D-A -0.151148; positive-IC ratio D-A -0.075000.
- split_002: Rank IC D-A -0.003760; ICIR D-A -0.061785; positive-IC ratio D-A -0.016129.
- split_003: Rank IC D-A +0.009780; ICIR D-A +0.041853; positive-IC ratio D-A +0.016129.
- Equal-split mean Rank IC D-A: -0.003059; positive splits: 1/3; worst split: split_001.

## Fixed P01 at 10 bps

- split_001: net return D-A -0.002195; IR D-A -0.055299; turnover D-A -18.406.
- split_002: net return D-A -0.100596; IR D-A -1.582061; turnover D-A -6.754.
- split_003: net return D-A +0.000494; IR D-A +0.034236; turnover D-A -17.225.
- Net return and IR improved in 1/3 splits; turnover fell in 3/3 splits.
- 0 and 20 bps secondary scenarios are in `portfolio_comparison.csv`; no rule was searched.

## Mechanism and cost

- split_001: 222/409 non-representatives had non-zero split importance; 18 clusters used multiple members; D/A wall 4384.5/914.5s (4.79x); D/A peak RSS 6948.2/1935.4 MiB (3.59x).
- split_002: 82/188 non-representatives had non-zero split importance; 10 clusters used multiple members; D/A wall 2632.3/1058.7s (2.49x); D/A peak RSS 4468.3/2235.9 MiB (2.00x).
- split_003: 140/157 non-representatives had non-zero split importance; 21 clusters used multiple members; D/A wall 3004.3/1434.4s (2.09x); D/A peak RSS 4569.4/2812.8 MiB (1.62x).

The added members were genuinely used by LightGBM, but usage does not prove causal increment. Wider D also materially increased runtime, memory, and model search cost.

## Interpretation and next step

The representative hard gate is currently **mixed**: it may discard useful joint development information in some regimes, while the unrestricted stable-core pool did not generalize consistently and was notably worse in split_002 P01. Do not remove the gate from Strategy V1 and do not create Policy E from this result.

Given the prior B>A diagnostic and the non-consistent A→D result, the next focused study should prioritize the existing conditional-signal mechanism. Any later multiple-representative or group-aware clustering study must be separately preregistered; SHAP, permutation, model-aware pruning, interactions, and LightGBM retuning remain out of scope.

## Limitations

- Historical tests were already observed and cannot authorize production or Strategy V2.
- No bootstrap was added; paired daily values are diagnostic only.
- P01 historical execution remains approximate and retains existing Qlib fallback warnings.
- The frozen clustering parent records an existing universe-artifact lineage inconsistency; D uses cluster metadata only as annotation, while A identity is referenced unchanged.
