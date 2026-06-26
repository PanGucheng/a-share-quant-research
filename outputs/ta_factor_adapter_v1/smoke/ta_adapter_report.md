# TA Factor Adapter Smoke V1

- Source: `E:/qlib_prj/qlib_baseline/tmp/reference_repos/ta`
- Commit: `a890410710a6e483c9ba08da7f3dd5089e4b9dff`
- License: `MIT`
- Date range: `2020-10-01` to `2021-06-30`
- Max instruments: `120`
- fillna: `false`
- vectorized: `false`
- Eligible factors: `79`
- Excluded factors: `7`

## Category Counts

| category | eligible_count |
| --- | --- |
| momentum | 18 |
| trend | 32 |
| volatility | 21 |
| volume | 8 |

## Selected Smoke Factors

| factor | category | eligible | coverage | missing_rate | exclusion_reason |
| --- | --- | --- | --- | --- | --- |
| ta_momentum_roc | momentum | True | 0.925206 | 0.074794 |  |
| ta_momentum_rsi | momentum | True | 0.926709 | 0.073291 |  |
| ta_trend_macd_diff | trend | True | 0.813296 | 0.186704 |  |
| ta_volatility_bbw | volatility | True | 0.875828 | 0.124172 |  |
| ta_volume_cmf | volume | True | 0.875828 | 0.124172 |  |

## Excluded Columns

| factor | category | exclusion_reason |
| --- | --- | --- |
| ta_others_cr | others | excluded_return_label_overlap |
| ta_others_dlr | others | excluded_return_label_overlap |
| ta_others_dr | others | excluded_return_label_overlap |
| ta_trend_visual_ichimoku_a | trend | excluded_visual_ichimoku_forward_shift |
| ta_trend_visual_ichimoku_b | trend | excluded_visual_ichimoku_forward_shift |
| ta_volume_nvi | volume | excluded_pct_change_default_fill_method_warning |
| ta_volume_vpt | volume | excluded_pct_change_default_fill_method_warning |

## Notes

- Upstream `ta` formulas are called directly from the local reference repository.
- `fillna=false` keeps warm-up NaN values instead of silently imputing them.
- `ta_trend_visual_ichimoku_*` is excluded because upstream `visual=True` shifts values forward.
- `ta_others_*` is excluded because return-like outputs overlap with project labels and basic return factors.
- `ta_volume_vpt` and `ta_volume_nvi` are excluded because the upstream implementation currently relies on pandas pct_change default fill behavior.
- The generated catalog is disabled/non-runnable until V4 smoke evaluation promotes selected factors.

## Output Files

- `factor_frame.pkl`
- `ta_factor_inventory.csv`
- `ta_factor_catalog_smoke.yaml`
- `ta_factor_frame_summary.csv`
- `ta_factor_frame_sample.csv`
- `ta_selected_smoke_factors.csv`
- `ta_adapter_manifest.json`
