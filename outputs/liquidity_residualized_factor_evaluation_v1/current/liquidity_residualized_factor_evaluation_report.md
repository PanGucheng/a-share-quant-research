# Liquidity Residualized Factor Evaluation V1 Report

V3.39 -- Residualized evaluation of 19 tradability-exposed probes.

## Status

- Watchlist factors: 19
- Factors present in frames: 19
- Residualized factors: 19
- Minimum residualized coverage: 0.1495
- Labels available: none (diagnostics-only)
- Daily diagnostics rows: 2242
- Comparison rows: 19
- Contract status rows: 8
- Downstream default included: 0

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| watchlist_rows | pass | watchlist_rows=19 |
| residualized_factor_count | pass | residualized_factor_count=19 |
| residualized_coverage_min | blocked | residualized_coverage_min=0.1495 |
| daily_diagnostics_rows | pass | daily_diagnostics_rows=2242 |
| raw_vs_residualized_metric_rows | pass | raw_vs_residualized_metric_rows=19 |
| contract_status_rows | pass | contract_status_rows=8 (target fulfilled) |
| downstream_default_included | pass | downstream_default_included=0 |
| residualized_factor_frame_produced | pass | residualized_columns_in_frame=19 |

## Factor Coverage Summary

| factor | residualized_factor | raw_coverage | residualized_coverage | n_raw_valid_rows | n_residualized_valid_rows | n_total_rows |
| --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha083 | kunquant_alpha101_alpha083__resid_liquidity | 0.952517 | 0.651157 | 84774 | 57953 | 89000 |
| ta_volatility_atr | ta_volatility_atr__resid_liquidity | 0.229472 | 0.149506 | 20423 | 13306 | 89000 |
| kunquant_alpha101_alpha042 | kunquant_alpha101_alpha042__resid_liquidity | 0.993685 | 0.657888 | 88438 | 58552 | 89000 |
| kunquant_alpha101_alpha041 | kunquant_alpha101_alpha041__resid_liquidity | 0.993685 | 0.657888 | 88438 | 58552 | 89000 |
| kunquant_alpha101_alpha005 | kunquant_alpha101_alpha005__resid_liquidity | 0.935899 | 0.651180 | 83295 | 57955 | 89000 |
| ta_volatility_kch | ta_volatility_kch__resid_liquidity | 0.238618 | 0.157326 | 21237 | 14002 | 89000 |
| ta_trend_ichimoku_conv | ta_trend_ichimoku_conv__resid_liquidity | 0.225764 | 0.156169 | 20093 | 13899 | 89000 |
| ta_trend_ema_fast | ta_trend_ema_fast__resid_liquidity | 0.224169 | 0.157326 | 19951 | 14002 | 89000 |
| ta_volatility_kcc | ta_volatility_kcc__resid_liquidity | 0.224270 | 0.156034 | 19960 | 13887 | 89000 |
| ta_volume_vwap | ta_volume_vwap__resid_liquidity | 0.218292 | 0.155483 | 19428 | 13838 | 89000 |
| ta_trend_sma_fast | ta_trend_sma_fast__resid_liquidity | 0.221281 | 0.155764 | 19694 | 13863 | 89000 |
| ta_volatility_kcl | ta_volatility_kcl__resid_liquidity | 0.238618 | 0.157326 | 21237 | 14002 | 89000 |
| ta_momentum_kama | ta_momentum_kama__resid_liquidity | 0.218978 | 0.150831 | 19489 | 13424 | 89000 |
| ta_trend_ichimoku_b | ta_trend_ichimoku_b__resid_liquidity | 0.239112 | 0.157326 | 21281 | 14002 | 89000 |
| kunquant_alpha101_alpha094 | kunquant_alpha101_alpha094__resid_liquidity | 0.923146 | 0.649753 | 82160 | 57828 | 89000 |
| kunquant_alpha101_alpha011 | kunquant_alpha101_alpha011__resid_liquidity | 0.974292 | 0.655584 | 86712 | 58347 | 89000 |
| kunquant_alpha101_alpha040 | kunquant_alpha101_alpha040__resid_liquidity | 0.935899 | 0.651180 | 83295 | 57955 | 89000 |
| ta_volatility_kcw | ta_volatility_kcw__resid_liquidity | 0.224270 | 0.156034 | 19960 | 13887 | 89000 |
| kunquant_alpha101_alpha088 | kunquant_alpha101_alpha088__resid_liquidity | 0.948663 | 0.652618 | 84431 | 58083 | 89000 |

## Daily Diagnostics (first 20 rows)

| datetime | factor | n_total | n_valid | coverage | corr_raw_residual | r2_approx | var_factor_z | var_residual_z |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-01-04 00:00:00 | kunquant_alpha101_alpha083 | 500 | 493 | 0.986000 | 0.119414 | 0.676194 | 1.830482 | 0.592720 |
| 2021-01-05 00:00:00 | kunquant_alpha101_alpha083 | 500 | 492 | 0.984000 | 0.261699 | 0.654153 | 1.851394 | 0.640299 |
| 2021-01-06 00:00:00 | kunquant_alpha101_alpha083 | 500 | 495 | 0.990000 | 0.338715 | 0.681150 | 1.889444 | 0.602450 |
| 2021-01-07 00:00:00 | kunquant_alpha101_alpha083 | 500 | 496 | 0.992000 | 0.235219 | 0.705770 | 1.939289 | 0.570598 |
| 2021-01-08 00:00:00 | kunquant_alpha101_alpha083 | 500 | 497 | 0.994000 | 0.176924 | 0.682124 | 1.990743 | 0.632810 |
| 2021-01-11 00:00:00 | kunquant_alpha101_alpha083 | 500 | 497 | 0.994000 | 0.275776 | 0.676917 | 1.897219 | 0.612959 |
| 2021-01-12 00:00:00 | kunquant_alpha101_alpha083 | 500 | 497 | 0.994000 | 0.256881 | 0.616184 | 1.854854 | 0.711922 |
| 2021-01-13 00:00:00 | kunquant_alpha101_alpha083 | 500 | 498 | 0.996000 | 0.190317 | 0.693437 | 1.912597 | 0.586330 |
| 2021-01-14 00:00:00 | kunquant_alpha101_alpha083 | 500 | 496 | 0.992000 | 0.162359 | 0.703028 | 1.980277 | 0.588086 |
| 2021-01-15 00:00:00 | kunquant_alpha101_alpha083 | 500 | 497 | 0.994000 | 0.254042 | 0.690204 | 2.013358 | 0.623731 |
| 2021-01-18 00:00:00 | kunquant_alpha101_alpha083 | 500 | 495 | 0.990000 | 0.360302 | 0.622929 | 1.795443 | 0.677009 |
| 2021-01-19 00:00:00 | kunquant_alpha101_alpha083 | 500 | 493 | 0.986000 | 0.228748 | 0.649936 | 1.909313 | 0.668381 |
| 2021-01-20 00:00:00 | kunquant_alpha101_alpha083 | 500 | 494 | 0.988000 | 0.255316 | 0.643392 | 1.958284 | 0.698341 |
| 2021-01-21 00:00:00 | kunquant_alpha101_alpha083 | 500 | 495 | 0.990000 | 0.203054 | 0.651982 | 1.863273 | 0.648453 |
| 2021-01-22 00:00:00 | kunquant_alpha101_alpha083 | 500 | 497 | 0.994000 | 0.188917 | 0.689572 | 1.956994 | 0.607506 |
| 2021-01-25 00:00:00 | kunquant_alpha101_alpha083 | 500 | 496 | 0.992000 | 0.216951 | 0.731460 | 1.961557 | 0.526758 |
| 2021-01-26 00:00:00 | kunquant_alpha101_alpha083 | 500 | 496 | 0.992000 | 0.277865 | 0.678752 | 1.963964 | 0.630920 |
| 2021-01-27 00:00:00 | kunquant_alpha101_alpha083 | 500 | 497 | 0.994000 | 0.176821 | 0.644893 | 1.964523 | 0.697615 |
| 2021-01-28 00:00:00 | kunquant_alpha101_alpha083 | 500 | 495 | 0.990000 | 0.213660 | 0.670127 | 2.000751 | 0.659994 |
| 2021-01-29 00:00:00 | kunquant_alpha101_alpha083 | 500 | 494 | 0.988000 | 0.212865 | 0.729848 | 1.848792 | 0.499456 |

## Raw vs Residualized Comparison

| factor | label | raw_mean_rank_ic | residualized_mean_rank_ic | rank_ic_retention | residualized_coverage | residualization_r2_mean |
| --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha083 | no_label |  |  |  | 0.651157 | 0.608898 |
| ta_volatility_atr | no_label |  |  |  | 0.149506 | 0.519507 |
| kunquant_alpha101_alpha042 | no_label |  |  |  | 0.657888 | 0.292500 |
| kunquant_alpha101_alpha041 | no_label |  |  |  | 0.657888 | 0.429172 |
| kunquant_alpha101_alpha005 | no_label |  |  |  | 0.651180 | 0.428025 |
| ta_volatility_kch | no_label |  |  |  | 0.157326 | 0.422661 |
| ta_trend_ichimoku_conv | no_label |  |  |  | 0.156169 | 0.419502 |
| ta_trend_ema_fast | no_label |  |  |  | 0.157326 | 0.416768 |
| ta_volatility_kcc | no_label |  |  |  | 0.156034 | 0.417015 |
| ta_volume_vwap | no_label |  |  |  | 0.155483 | 0.416612 |
| ta_trend_sma_fast | no_label |  |  |  | 0.155764 | 0.415760 |
| ta_volatility_kcl | no_label |  |  |  | 0.157326 | 0.410265 |
| ta_momentum_kama | no_label |  |  |  | 0.150831 | 0.411252 |
| ta_trend_ichimoku_b | no_label |  |  |  | 0.157326 | 0.400956 |
| kunquant_alpha101_alpha094 | no_label |  |  |  | 0.649753 | 0.305683 |
| kunquant_alpha101_alpha011 | no_label |  |  |  | 0.655584 | 0.128880 |
| kunquant_alpha101_alpha040 | no_label |  |  |  | 0.651180 | 0.174925 |
| ta_volatility_kcw | no_label |  |  |  | 0.156034 | 0.130216 |
| kunquant_alpha101_alpha088 | no_label |  |  |  | 0.652618 | 0.183464 |

## Candidate Actions

| factor | label | source_family | raw_action | primary_exposure_proxy | raw_mean_rank_ic | residualized_mean_rank_ic | residualized_rank_icir | rank_ic_retention | residualized_coverage | residualization_r2_mean | decision | decision_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha083 | no_label | alpha101 | holdout_before_residualization | liquidity_value |  |  |  |  | 0.651157 | 0.608898 | needs_manual_review | coverage=0.6512 below 0.80 |
| ta_volatility_atr | no_label | ta | holdout_before_residualization | liquidity_value |  |  |  |  | 0.149506 | 0.519507 | needs_manual_review | coverage=0.1495 below 0.80 |
| kunquant_alpha101_alpha042 | no_label | alpha101 | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.657888 | 0.292500 | needs_manual_review | coverage=0.6579 below 0.80 |
| kunquant_alpha101_alpha041 | no_label | alpha101 | holdout_before_residualization | liquidity_value |  |  |  |  | 0.657888 | 0.429172 | needs_manual_review | coverage=0.6579 below 0.80 |
| kunquant_alpha101_alpha005 | no_label | alpha101 | holdout_before_residualization | liquidity_value |  |  |  |  | 0.651180 | 0.428025 | needs_manual_review | coverage=0.6512 below 0.80 |
| ta_volatility_kch | no_label | ta | holdout_before_residualization | liquidity_value |  |  |  |  | 0.157326 | 0.422661 | needs_manual_review | coverage=0.1573 below 0.80 |
| ta_trend_ichimoku_conv | no_label | ta | holdout_before_residualization | liquidity_value |  |  |  |  | 0.156169 | 0.419502 | needs_manual_review | coverage=0.1562 below 0.80 |
| ta_trend_ema_fast | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.157326 | 0.416768 | needs_manual_review | coverage=0.1573 below 0.80 |
| ta_volatility_kcc | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.156034 | 0.417015 | needs_manual_review | coverage=0.1560 below 0.80 |
| ta_volume_vwap | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.155483 | 0.416612 | needs_manual_review | coverage=0.1555 below 0.80 |
| ta_trend_sma_fast | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.155764 | 0.415760 | needs_manual_review | coverage=0.1558 below 0.80 |
| ta_volatility_kcl | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.157326 | 0.410265 | needs_manual_review | coverage=0.1573 below 0.80 |
| ta_momentum_kama | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.150831 | 0.411252 | needs_manual_review | coverage=0.1508 below 0.80 |
| ta_trend_ichimoku_b | no_label | ta | holdout_redundant_liquidity_proxy | liquidity_value |  |  |  |  | 0.157326 | 0.400956 | needs_manual_review | coverage=0.1573 below 0.80 |
| kunquant_alpha101_alpha094 | no_label | alpha101 | residualization_candidate_review | liquidity_value |  |  |  |  | 0.649753 | 0.305683 | needs_manual_review | coverage=0.6498 below 0.80 |
| kunquant_alpha101_alpha011 | no_label | alpha101 | manual_review_before_training | liquidity_value |  |  |  |  | 0.655584 | 0.128880 | needs_manual_review | coverage=0.6556 below 0.80 |
| kunquant_alpha101_alpha040 | no_label | alpha101 | manual_review_before_training | liquidity_value |  |  |  |  | 0.651180 | 0.174925 | needs_manual_review | coverage=0.6512 below 0.80 |
| ta_volatility_kcw | no_label | ta | manual_review_before_training | liquidity_value |  |  |  |  | 0.156034 | 0.130216 | needs_manual_review | coverage=0.1560 below 0.80 |
| kunquant_alpha101_alpha088 | no_label | alpha101 | manual_review_before_training | liquidity_value |  |  |  |  | 0.652618 | 0.183464 | needs_manual_review | coverage=0.6526 below 0.80 |

## Decision Summary

| decision | count |
| --- | --- |
| needs_manual_review | 19 |

## Notes

- Residualization suffix: `__resid_liquidity`; raw factors never overwritten.
- Proxies: `liquidity_value`, `liquidity_bucket`, `tradability_score` (constant proxies auto-excluded per day).
- Each trading day is residualized independently via OLS after winsorized z-scoring.
- R^2 is computed in z-score / regression space (var of residual vs var of z-scored factor).
- `residual_signal_survives` -> signal remains positive after removing liquidity exposure.
- `liquidity_proxy_confirmed` -> raw alpha largely explained by liquidity/tradability.
- `holdout` -> no stable residual signal; hold back from training.
- `needs_manual_review` -> insufficient data, low coverage, or unclear signal for automated decision.

- Large `residualized_factor_frame.pkl` is a local re-generable cache; CSV artefacts are the canonical record.

## Fallback Notice

No forward-return label columns were found in the factor frames or feature cache.
IC-based metrics (mean_ic, mean_rank_ic, icir, rank_icir, ic_retention) are NaN.
The comparison table still contains actual computed diagnostics:
- `residualized_coverage` -- proportion of rows with a valid residualized value.
- `residualization_r2_mean` -- mean daily R^2 in z-score space (var(residual_z) / var(factor_z)).
Candidate decisions rely on coverage and R^2 instead of IC retention.
