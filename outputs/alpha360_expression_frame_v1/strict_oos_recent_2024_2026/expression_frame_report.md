# Alpha360 Expression Frame Smoke V1

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Max instruments: `500`
- Factor count: `3`
- Catalog: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha360_v1/alpha360_catalog_promoted358.yaml`
- Inventory: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha360_v1/alpha360_formula_inventory.csv`

## Expression Table

| catalog_name | factor_name | family | lag | category | expression |
| --- | --- | --- | --- | --- | --- |
| alpha360_HIGH36 | HIGH36 | HIGH | 36 | alpha360_high_window | Ref($high, 36)/$close |
| alpha360_HIGH37 | HIGH37 | HIGH | 37 | alpha360_high_window | Ref($high, 37)/$close |
| alpha360_HIGH40 | HIGH40 | HIGH | 40 | alpha360_high_window | Ref($high, 40)/$close |

## Coverage

| factor | coverage | missing_rate | valid_rows | total_rows |
| --- | --- | --- | --- | --- |
| alpha360_HIGH36 | 0.996236 | 0.003764 | 285864 | 286944 |
| alpha360_HIGH37 | 0.996243 | 0.003757 | 285866 | 286944 |
| alpha360_HIGH40 | 0.996243 | 0.003757 | 285866 | 286944 |

## Boundary

- This is an adapter smoke run only. Catalog entries stay disabled/non-runnable until V4 evaluation and promotion pass.
- Downstream evaluation must keep data_quality and tradability as mandatory prefilters.

## Output Files

- `factor_frame.pkl`
- `expression_table.csv`
- `expression_frame_summary.csv`
- `expression_frame_sample.csv`
- `expression_frame_manifest.json`
