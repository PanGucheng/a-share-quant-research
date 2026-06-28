# Tradability Exposure Attribution V1

- Scope: attribution for probes already marked `tradability_exposure_review`.
- Boundary: no model training, no strategy optimization, no evaluator definition changes.
- Review board: `outputs/new_source_probe_review_v1/current/probe_review_board.csv`
- Diagnostic exposure: `outputs/new_source_probe_diagnostics_v1/current/selected_probe_tradability_exposure.csv`

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| watchlist_rows | pass | watchlist_rows=19 |
| attribution_rows | pass | attribution_rows=19 |
| source_family_coverage | pass | source_families=2 |
| primary_proxy_present | pass | missing_proxy=0 |
| diagnostic_exposure_available | pass | diagnostic_exposure_rows=120 |
| no_downstream_default | pass | downstream_default=0 |

## Source Summary

| source_family | exposure_direction | exposure_strength | attribution_label | factor_count |
| --- | --- | --- | --- | --- |
| alpha101 | negative | moderate | moderate_tradability_review | 3 |
| alpha101 | negative | strong | strong_liquidity_proxy | 2 |
| alpha101 | negative | material | material_liquidity_proxy | 1 |
| alpha101 | negative | strong | material_liquidity_proxy | 1 |
| alpha101 | positive | strong | strong_liquidity_proxy | 1 |
| ta | positive | material | material_liquidity_proxy | 7 |
| ta | positive | strong | strong_liquidity_proxy | 3 |
| ta | positive | moderate | moderate_tradability_review | 1 |

## Action Summary

| recommended_action | exposure_strength | factor_count |
| --- | --- | --- |
| holdout_before_residualization | strong | 6 |
| holdout_redundant_liquidity_proxy | material | 7 |
| holdout_redundant_liquidity_proxy | strong | 1 |
| manual_review_before_training | moderate | 4 |
| residualization_candidate_review | material | 1 |

## Attribution Board

| factor | source_family | source_project | category | judgement_label | max_abs_mean_ic | max_abs_qlib_ir | primary_exposure_proxy | primary_exposure_value | primary_abs_exposure | exposure_direction | exposure_strength | mean_spearman_liquidity_value | mean_spearman_liquidity_bucket | mean_spearman_tradability_score | high_liquidity_z_mean | low_liquidity_z_mean | high_minus_low_liquidity_z | redundancy_compounded | redundancy_representative | attribution_label | recommended_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kunquant_alpha101_alpha083 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.072538 | 5.668160 | liquidity_value | -0.784104 | 0.784104 | negative | strong | -0.784104 | -0.761590 | -0.628829 | -0.356860 | 0.471912 | -0.828772 | False | nan | strong_liquidity_proxy | holdout_before_residualization |
| ta_volatility_atr | ta | ta | ta_volatility | strong_signal_probe | 0.127568 | 9.604630 | liquidity_value | 0.721224 | 0.721224 | positive | strong | 0.721224 | 0.697949 | 0.525581 | 0.370638 | -0.450581 | 0.821220 | True | nan | strong_liquidity_proxy | holdout_before_residualization |
| kunquant_alpha101_alpha042 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.065690 | 5.387349 | liquidity_value | -0.657406 | 0.657406 | negative | strong | -0.657406 | -0.634948 | -0.489410 | -0.267459 | 0.269146 | -0.536605 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| kunquant_alpha101_alpha041 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.065687 | 5.385930 | liquidity_value | 0.657051 | 0.657051 | positive | strong | 0.657051 | 0.634574 | 0.489918 | 0.386002 | -0.463089 | 0.849090 | True | ta_momentum_kama | strong_liquidity_proxy | holdout_before_residualization |
| kunquant_alpha101_alpha005 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.062534 | 5.124935 | liquidity_value | -0.656661 | 0.656661 | negative | strong | -0.656661 | -0.634614 | -0.488510 | -0.563299 | 0.670108 | -1.233407 | True | ta_momentum_kama | strong_liquidity_proxy | holdout_before_residualization |
| ta_volatility_kch | ta | ta | ta_volatility | strong_signal_probe | 0.118736 | 9.061716 | liquidity_value | 0.654013 | 0.654013 | positive | strong | 0.654013 | 0.631549 | 0.487921 | 0.385063 | -0.460832 | 0.845895 | True | ta_momentum_kama | strong_liquidity_proxy | holdout_before_residualization |
| ta_trend_ichimoku_conv | ta | ta | ta_trend | strong_signal_probe | 0.118935 | 9.110528 | liquidity_value | 0.651987 | 0.651987 | positive | strong | 0.651987 | 0.629777 | 0.487376 | 0.387102 | -0.463416 | 0.850519 | True | ta_momentum_kama | strong_liquidity_proxy | holdout_before_residualization |
| ta_trend_ema_fast | ta | ta | ta_trend | strong_signal_probe | 0.118668 | 9.011919 | liquidity_value | 0.649670 | 0.649670 | positive | material | 0.649670 | 0.627139 | 0.484550 | 0.388857 | -0.461152 | 0.850009 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| ta_volatility_kcc | ta | ta | ta_volatility | strong_signal_probe | 0.119373 | 9.147213 | liquidity_value | 0.649433 | 0.649433 | positive | material | 0.649433 | 0.627335 | 0.485562 | 0.385588 | -0.462591 | 0.848179 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| ta_volume_vwap | ta | ta | ta_volume | strong_signal_probe | 0.120504 | 9.053554 | liquidity_value | 0.648960 | 0.648960 | positive | material | 0.648960 | 0.626905 | 0.485329 | 0.387869 | -0.464278 | 0.852146 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| ta_trend_sma_fast | ta | ta | ta_trend | strong_signal_probe | 0.119505 | 9.062298 | liquidity_value | 0.648570 | 0.648570 | positive | material | 0.648570 | 0.626371 | 0.485077 | 0.385574 | -0.462696 | 0.848270 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| ta_volatility_kcl | ta | ta | ta_volatility | strong_signal_probe | 0.117208 | 8.963050 | liquidity_value | 0.644547 | 0.644547 | positive | material | 0.644547 | 0.622254 | 0.482805 | 0.388524 | -0.462677 | 0.851201 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| ta_momentum_kama | ta | ta | ta_momentum | strong_signal_probe | 0.117594 | 9.190937 | liquidity_value | 0.642989 | 0.642989 | positive | material | 0.642989 | 0.621540 | 0.482527 | 0.426164 | -0.481823 | 0.907988 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| ta_trend_ichimoku_b | ta | ta | ta_trend | strong_signal_probe | 0.114848 | 8.553694 | liquidity_value | 0.636455 | 0.636455 | positive | material | 0.636455 | 0.613776 | 0.477290 | 0.388400 | -0.459344 | 0.847744 | True | ta_momentum_kama | material_liquidity_proxy | holdout_redundant_liquidity_proxy |
| kunquant_alpha101_alpha094 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.058646 | 6.151593 | liquidity_value | -0.463381 | 0.463381 | negative | material | -0.463381 | -0.446381 | -0.301414 | -0.443568 | 0.521929 | -0.965498 | False | nan | material_liquidity_proxy | residualization_candidate_review |
| kunquant_alpha101_alpha011 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.056459 | 5.625899 | liquidity_value | -0.443038 | 0.443038 | negative | moderate | -0.443038 | -0.418437 | -0.336248 | -0.285677 | 0.365132 | -0.650809 | False | nan | moderate_tradability_review | manual_review_before_training |
| kunquant_alpha101_alpha040 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.064238 | 11.004408 | liquidity_value | -0.430243 | 0.430243 | negative | moderate | -0.430243 | -0.418429 | -0.327467 | -0.361895 | 0.489752 | -0.851646 | False | nan | moderate_tradability_review | manual_review_before_training |
| ta_volatility_kcw | ta | ta | ta_volatility | strong_signal_probe | 0.094221 | 8.151400 | liquidity_value | 0.331646 | 0.331646 | positive | moderate | 0.331646 | 0.320855 | 0.180566 | 0.311398 | -0.319188 | 0.630586 | False | nan | moderate_tradability_review | manual_review_before_training |
| kunquant_alpha101_alpha088 | alpha101 | kunquant_alpha101 | alpha101 | strong_signal_probe | 0.067655 | 10.102395 | liquidity_value | -0.317993 | 0.317993 | negative | moderate | -0.317993 | -0.314466 | -0.175520 | -0.307111 | 0.325709 | -0.632820 | False | nan | moderate_tradability_review | manual_review_before_training |

## Notes

- High tradability exposure does not prove a factor is invalid, but it blocks direct training admission.
- `holdout_before_residualization` means the next useful experiment is neutralized/residualized evaluation, not raw-factor training.
