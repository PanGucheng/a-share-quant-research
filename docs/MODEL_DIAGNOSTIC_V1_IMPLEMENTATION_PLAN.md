# Model Diagnostic V1 Implementation Plan

## 1. Research Boundary

`post_model_diagnostics_v1` is post-observation historical diagnosis. It reuses the
three frozen LightGBM predictions and P01 artifacts. It must not retrain Model V1,
regenerate official predictions, reselect factors, scan TopK/rebalance parameters,
or change P01. `split_003` has already been observed; findings can only motivate a
future, separately frozen V2 hypothesis.

The authoritative split feature counts are 45, 46, and 52. Their union is 77 and
intersection is 22. Each split is interpreted with its actual frozen allowlist.

## 2. Independent Layers

The stage has three independently keyed layers:

```text
Frozen diagnostic base
  -> frozen prediction + selected features + 1/5/10/20D returns + PIT proxies
Core diagnostics
  -> structure, conditional IC, concentration, decay, stability, importance,
     SHAP, portfolio/cost attribution
Optional external style extension
  -> PIT market cap and SW Level-1 industry analyses
```

Base keys bind only the prediction, selection, matrix, label/raw-market and proxy
configuration hashes. Expensive Core components bind the base key plus their own
metric configuration. External style keys bind the base identity and external input
hash only. Adding Tushare data later must not rerun SHAP, permutation, ranking,
decay, stability, or prediction generation.

## 3. Core Analysis

Ranking buckets are fixed at 1-10, 11-20, 21-30, 31-50, 51-100, 101-200 and
201+. Forward horizons are 1D, 5D, 10D and 20D. Stability lags are 1, 5, 10 and
20 trading days, with Top10/20/50/100 retention and Top50 41-60 edge churn.

Existing PIT conditions use only correctly named proxies: `amount_mean_20` is a
liquidity proxy, `alpha158_STD20` is a volatility proxy, and `alpha158_ROC20` is
monotonically converted to a momentum proxy. None is labelled market cap or Size.

Qlib supplies IC and prediction analysis semantics; the repository-pinned Alphalens
Reloaded source supplies its original metric implementations; sklearn supplies
permutation importance; SHAP TreeExplainer explains the frozen boosters. Metric
names retain their source definitions when Qlib and Alphalens differ.

## 4. External PIT Style Contract

The optional schema freezes `(datetime, instrument)`, total/circulating market cap,
derived size quantile/bucket, SW Level-1 code/name, industry effective intervals and
source snapshot/hash provenance. Historical rows must be point-in-time and inside
their classification effective interval. Current values and future classifications
must never be backfilled into history.

Until an eligible source exists, Core still publishes with:

```text
historical_pit_market_cap_available = false
historical_pit_industry_available = false
external_style_extension_status = unavailable_data
```

Future Tushare work may source `daily_basic.total_mv/circ_mv` and
`index_member_all` in/out intervals, but it is a separate task and cannot modify
Model V1, P01, or the genuine forward track.

## 5. Runtime And Acceptance

SHAP runs in a separate diagnostics environment. The frozen `qlib_env` and its
environment lock remain unchanged. Diagnostics record Python, LightGBM, numpy,
pandas, sklearn and SHAP versions, and verify model, preprocessing, feature order,
prediction hashes, dates and key ordering. Sample predictions use strict relative
and absolute tolerances and publish maximum differences and mismatch counts.

Core completion requires all three splits, exact feature counts/hashes, 20D label
equivalence, non-empty diagnostic tables, deterministic smoke results and unchanged
frozen artifacts. Missing optional style data was a warning, not a critical failure.
Before the extension existed, the Core-only report explicitly recorded that external
style evidence was unavailable. Sections 7-9 supersede that capability status while
preserving the distinction between historical diagnosis and unbiased future evidence.

## 6. Execution Record

The three-split Core was completed on 2026-08-08 with the isolated runtime at
`E:/anaconda_envs/model_diagnostics_v1`. It preserves the frozen runtime's Python,
numpy, pandas, sklearn and LightGBM versions and adds only `shap==0.49.1` to the
diagnostics clone. The frozen `E:/anaconda_envs/qlib_env` remains SHAP-free.

Formal outputs are published under `outputs/post_model_diagnostics_v1/current`.
All critical contracts passed, prediction and 20D label equivalence reported zero
mismatches for all three splits, and the repository test suite passed 312 tests.
At that Core execution point, the independent external PIT market-cap/industry
extension still had status `unavailable_data`; Sections 7-8 record its later completion.

## 7. External PIT Style Data V1

The external stage is implemented by
`scripts/run_external_pit_style_data_v1.py` with the frozen configuration in
`configs/external_pit_style_data_v1.yaml`. It reads `TUSHARE_TOKEN` only from the
process environment and uses the Tushare Python SDK in the isolated
`E:/anaconda_envs/model_diagnostics_v1` runtime. MCP was limited to API discovery,
permission canaries and small response checks; no MCP response is a formal research
input.

The canary verified `daily_basic`, SW2021 L1 `index_classify`, and both current and
historical `index_member_all` records (`is_new=Y` and `is_new=N`). Formal retrieval
then fetched one full-market `daily_basic` cross-section for each of 368 required
decision dates. Raw payloads are cached by request with retrieval time, row count
and SHA256 receipts, and the fetcher supports retry, throttling, checkpoints and
resume without silently publishing a partial dataset.

The standardized table uses Tushare's raw `total_mv` and `circ_mv` unit of ten
thousand CNY. `size_percentile` is ranked inside the project's effective daily
universe, with Small/Mid/Large boundaries at 30/70 percent. SW L1 membership uses
the inclusive interval `in_date <= decision_date <= out_date`; no current or future
record is backfilled. The evidence is described as a historical effective-date
classification reconstructed today, not an original database-vintage snapshot.

The formal artifact was published at
`outputs/external_pit_style_data_v1/current`. It contains 735,882 standardized rows
over 368 dates, backed by 1,985,222 cached raw daily rows and 7,533 normalized SW L1
membership intervals. Minimum daily market-cap and industry coverage are 0.993493
and 0.998499. All critical checks passed: no missing request segment, duplicate
style key, ambiguous membership, or future/current backfill was found.

## 8. Style Attribution Extension

The independent extension is implemented by
`scripts/run_model_diagnostic_style_attribution_v1.py` and
`configs/model_diagnostic_style_attribution_v1.yaml`. It consumes the frozen Core
base cache and the passing External PIT artifact. It does not call the diagnostic
Core runner and therefore does not recompute SHAP, permutation importance, ranking
concentration, signal decay, ranking stability, or predictions.

Published analyses cover Universe and Top10/20/50/100 Size exposure, conditional
Size Rank IC for the model and economic factor groups, Size-regime attribution,
SW2021 L1 exposure and active share, industry-conditional IC with explicit
insufficient-coverage status, and daily equal-weighted cross-sectional OLS:

```text
return_20d_t1 ~ model_score_z + size_percentile_z + SW_L1 fixed effects
```

The result does not support a persistent Small Cap bias. Top50 mean Size percentile
is 0.456, 0.623 and 0.637 for split_001/002/003 against a daily universe mean of
0.500. `amount_mean_20` is partly, but not exclusively, associated with Size: its
mean daily rank correlation with Size is 0.544, 0.471 and 0.595. The Small-minus-
Large forward-return spread changes from a development-split mean of 0.030345 to
-0.009101 in split_003, while split_003 model Rank IC is 0.1359/0.0780/-0.0378 in
Small/Mid/Large. This supports Size regime mismatch only as a future hypothesis,
not as a new selection decision.

Top50's largest positive SW L1 active shares are Utilities at 0.044 in split_001
and Banks at 0.096 in split_002/003; maximum absolute industry active share is
0.104. After Size and SW L1 controls, mean model-score coefficients are 0.000314,
0.004054 and -0.000580, so independent alpha evidence is mixed. Benchmark-relative
attribution remains optional and unresolved because the monthly `000985.CSI`
weights were MCP-canary verified but not admitted as formal SDK input.

Formal outputs are under
`outputs/model_diagnostic_style_attribution_v1/current`. Its manifest is
`pass/complete`; every split has at least 120 valid controlled-attribution days.
The stage verifies before/after hashes for the Core manifest, Core P01 attribution,
Model V1 and portfolio manifests, prediction receipt, and all three frozen
prediction files. All hashes were unchanged. The repository suite passed 323 tests
on 2026-08-09; four pre-existing Qlib synthetic exchange warnings remain.

Reproduction commands:

```powershell
E:\anaconda_envs\model_diagnostics_v1\python.exe scripts\run_external_pit_style_data_v1.py
E:\anaconda_envs\model_diagnostics_v1\python.exe scripts\run_model_diagnostic_style_attribution_v1.py
E:\anaconda_envs\model_diagnostics_v1\python.exe -m pytest -q
```

## 9. Formal Closeout

Model Diagnostic V1 Core, External PIT Style Data V1, and the Style Attribution
Extension are formally `PASS / COMPLETE`. The concise authoritative stage status,
combined interpretation, rejected explanations, surviving future-test hypotheses,
frozen boundary, and Model V2 handoff are recorded in
`docs/MODEL_DIAGNOSTIC_V1_CLOSEOUT.md`.

Detailed statistics remain authoritative in the three published artifact directories;
the closeout does not alter those artifacts or promote historical diagnosis into new
OOS evidence. Benchmark constituent attribution remains unresolved/non-blocking and
does not prevent this stage from closing.
