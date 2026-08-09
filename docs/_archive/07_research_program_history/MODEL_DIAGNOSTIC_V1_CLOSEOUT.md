# Model Diagnostic V1 Closeout

> ARCHIVED / CLOSED：本文件是冻结的历史诊断收尾记录。

## Stage Status

```text
MODEL DIAGNOSTIC V1
===================

Core Diagnostic                         PASS / COMPLETE
External PIT Style Data V1              PASS / COMPLETE
Style Attribution Extension             PASS / COMPLETE
Market Cap Coverage                     >= 99.35%
Industry Coverage                       >= 99.85%

Persistent Small-cap Exposure           NOT SUPPORTED
Liquidity == Size                       NOT SUPPORTED
Extreme Industry Concentration          NOT SUPPORTED
Top10 Concentration Hypothesis           NOT SUPPORTED BY OBSERVED HOLDOUT
Transaction Cost As Primary Cause       NOT SUPPORTED

Size Regime Change                      OBSERVED
Size-Conditional Model Behavior         SUPPORTED FOR FUTURE TEST
Independent Model Alpha                 MIXED
Model / Relationship Non-stationarity   LEADING FUTURE-TEST HYPOTHESIS
Benchmark Constituent Attribution       UNRESOLVED / NON-BLOCKING

Historical Diagnosis                    COMPLETE
Model V2                                NOT YET TRAINED
```

This closeout freezes Model Diagnostic V1 as historical, post-observation evidence.
It does not convert `split_003` into a fresh holdout and does not authorize a Model
V1, P01, factor, TopK, rebalance, or forward-track change.

## Authoritative Evidence

- Core manifest and report: `outputs/post_model_diagnostics_v1/current/`
- External PIT manifest and report: `outputs/external_pit_style_data_v1/current/`
- Style Attribution manifest and report:
  `outputs/model_diagnostic_style_attribution_v1/current/`
- Implementation and execution record:
  `docs/_archive/07_research_program_history/MODEL_DIAGNOSTIC_V1_IMPLEMENTATION_PLAN.md`

All three stage manifests are `pass/complete`. External PIT Style Data V1 covers
368 decision dates and 735,882 standardized rows. Minimum market-cap and SW L1
industry coverage are 0.993493 and 0.998499. Formal research data was built by the
project's Tushare Python SDK pipeline; MCP was used only for discovery and canaries.

## Evidence Summary

Prediction quality weakened in the observed holdout. Model V1 20-day Rank IC is
0.051802 in `split_003`, 0.058702 below the mean of the two development splits.
The `split_003` Top10 20-day excess return is -0.010924, so the observed holdout does
not support the claim that alpha was concentrated in the first ten names or that
shrinking P01 from Top50 to Top10 would have solved the deterioration.

P01 cost drag is 0.058019 in `split_003`. Cost materially reduced realized return,
but approximate gross return still trailed the benchmark. Transaction cost alone is
therefore not supported as the primary cause.

Model V1 consistently favors lower liquidity and lower volatility observable
proxies. These are not interchangeable with market capitalization. The mean daily
cross-sectional correlation between `amount_mean_20` and true Size is about 0.537:
the variables are related, but they are not equivalent.

Persistent Small Cap exposure is not supported. Top50 mean Size percentile is
0.456, 0.623, and 0.637 in `split_001/002/003`, respectively, against a daily
universe mean near 0.500. The model is Small-leaning only in `split_001` and is
Large-leaning in `split_002/003`.

A Size regime change is observed: the development mean Small-minus-Large future-
return spread is about +0.0303, versus -0.0091 in `split_003`. This does not establish
that Size caused Model V1's deterioration because the model itself was already
Large-leaning in `split_003`. It supports future testing of unstable Size-conditional
model behavior, not a pure Small Cap explanation.

The largest absolute Top50 SW L1 active industry exposure is about 0.104. Moderate
industry exposures exist, but extreme single-industry concentration is not supported
as the primary explanation.

After daily Size and SW L1 controls, model-score coefficients are +0.000314,
+0.004054, and -0.000580 in `split_001/002/003`. Independent model alpha is therefore
mixed. The important finding is that the model-score relationship after observable
style controls is not stable across periods.

## Closed Explanations

Current historical evidence does not support these simple explanations:

- Model V1 is persistently a Small Cap strategy.
- `split_003` failed mainly because a persistent Small Cap exposure reversed.
- One extreme industry bet caused the deterioration.
- Top50 dilution was the problem and Top10 would have fixed it.
- Transaction cost was the primary cause.

These conclusions apply to the current observed evidence. They do not prohibit a
future preregistered study, but `split_003` cannot be reused to select a preferred
alternative and then be described as fresh OOS evidence.

## Future-Test Hypotheses

The combined historical evidence is more consistent with time-varying or
conditional predictive relationships than with a single persistent Size exposure,
extreme industry concentration, TopK dilution, or transaction cost alone. This is a
hypothesis-generating interpretation, not a proven causal explanation.

- Model/factor-return relationship non-stationarity: leading future-test hypothesis.
- Size/style-conditional factor effectiveness: supported for future test.
- Time adaptation: supported for future test.
- Conditional or expert modeling: plausible future test.
- Turnover reduction: supported as a portfolio-level future test.
- Benchmark constituent attribution: unresolved and non-blocking.

## Frozen Boundary And Handoff

Model Diagnostic V1, External PIT Style Data V1, and the Style Attribution Extension
are closed. Their research specifications may change only to correct a proven data
error, leakage, contract failure, or implementation bug. Other additions must be an
append-only clarification or a new version/stage; retrospective optimization is
forbidden.

The next possible stage is **Model V2 Research Protocol**. It must freeze its research
questions, development/validation design, model candidates, selection criteria, and
new forward evidence boundary before training. Non-binding candidates are a
V1-compatible LightGBM baseline, rolling-window LightGBM, time-decay LightGBM,
conditional/style-aware LightGBM, a Qlib DoubleEnsemble benchmark, and an optional
LightGBM ranking-objective benchmark.

This closeout does not train Model V2, select a winner, run a new holdout scan, use
Optuna, reselect the 52 factors, scan TopK or rebalance periods, or modify P01.
