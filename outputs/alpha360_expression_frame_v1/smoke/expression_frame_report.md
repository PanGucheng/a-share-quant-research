# Alpha360 Expression Frame Smoke V1

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2020-10-01` to `2021-06-30`
- Max instruments: `500`
- Factor count: `24`
- Catalog: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha360_v1/alpha360_catalog_smoke.yaml`
- Inventory: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha360_v1/alpha360_formula_inventory.csv`

## Expression Table

| catalog_name | factor_name | family | lag | category | expression |
| --- | --- | --- | --- | --- | --- |
| alpha360_CLOSE0 | CLOSE0 | CLOSE | 0 | alpha360_close_window | $close/$close |
| alpha360_CLOSE5 | CLOSE5 | CLOSE | 5 | alpha360_close_window | Ref($close, 5)/$close |
| alpha360_CLOSE20 | CLOSE20 | CLOSE | 20 | alpha360_close_window | Ref($close, 20)/$close |
| alpha360_CLOSE59 | CLOSE59 | CLOSE | 59 | alpha360_close_window | Ref($close, 59)/$close |
| alpha360_OPEN0 | OPEN0 | OPEN | 0 | alpha360_open_window | $open/$close |
| alpha360_OPEN5 | OPEN5 | OPEN | 5 | alpha360_open_window | Ref($open, 5)/$close |
| alpha360_OPEN20 | OPEN20 | OPEN | 20 | alpha360_open_window | Ref($open, 20)/$close |
| alpha360_OPEN59 | OPEN59 | OPEN | 59 | alpha360_open_window | Ref($open, 59)/$close |
| alpha360_HIGH0 | HIGH0 | HIGH | 0 | alpha360_high_window | $high/$close |
| alpha360_HIGH5 | HIGH5 | HIGH | 5 | alpha360_high_window | Ref($high, 5)/$close |
| alpha360_HIGH20 | HIGH20 | HIGH | 20 | alpha360_high_window | Ref($high, 20)/$close |
| alpha360_HIGH59 | HIGH59 | HIGH | 59 | alpha360_high_window | Ref($high, 59)/$close |
| alpha360_LOW0 | LOW0 | LOW | 0 | alpha360_low_window | $low/$close |
| alpha360_LOW5 | LOW5 | LOW | 5 | alpha360_low_window | Ref($low, 5)/$close |
| alpha360_LOW20 | LOW20 | LOW | 20 | alpha360_low_window | Ref($low, 20)/$close |
| alpha360_LOW59 | LOW59 | LOW | 59 | alpha360_low_window | Ref($low, 59)/$close |
| alpha360_VWAP0 | VWAP0 | VWAP | 0 | alpha360_vwap_window | $vwap/$close |
| alpha360_VWAP5 | VWAP5 | VWAP | 5 | alpha360_vwap_window | Ref($vwap, 5)/$close |
| alpha360_VWAP20 | VWAP20 | VWAP | 20 | alpha360_vwap_window | Ref($vwap, 20)/$close |
| alpha360_VWAP59 | VWAP59 | VWAP | 59 | alpha360_vwap_window | Ref($vwap, 59)/$close |
| alpha360_VOLUME0 | VOLUME0 | VOLUME | 0 | alpha360_volume_window | $volume/($volume+1e-12) |
| alpha360_VOLUME5 | VOLUME5 | VOLUME | 5 | alpha360_volume_window | Ref($volume, 5)/($volume+1e-12) |
| alpha360_VOLUME20 | VOLUME20 | VOLUME | 20 | alpha360_volume_window | Ref($volume, 20)/($volume+1e-12) |
| alpha360_VOLUME59 | VOLUME59 | VOLUME | 59 | alpha360_volume_window | Ref($volume, 59)/($volume+1e-12) |

## Coverage

| factor | coverage | missing_rate | valid_rows | total_rows |
| --- | --- | --- | --- | --- |
| alpha360_CLOSE0 | 0.995957 | 0.004043 | 88438 | 88797 |
| alpha360_CLOSE5 | 0.994257 | 0.005743 | 88287 | 88797 |
| alpha360_CLOSE20 | 0.993277 | 0.006723 | 88200 | 88797 |
| alpha360_CLOSE59 | 0.993085 | 0.006915 | 88183 | 88797 |
| alpha360_OPEN0 | 0.995957 | 0.004043 | 88438 | 88797 |
| alpha360_OPEN5 | 0.994257 | 0.005743 | 88287 | 88797 |
| alpha360_OPEN20 | 0.993277 | 0.006723 | 88200 | 88797 |
| alpha360_OPEN59 | 0.993085 | 0.006915 | 88183 | 88797 |
| alpha360_HIGH0 | 0.995957 | 0.004043 | 88438 | 88797 |
| alpha360_HIGH5 | 0.994257 | 0.005743 | 88287 | 88797 |
| alpha360_HIGH20 | 0.993277 | 0.006723 | 88200 | 88797 |
| alpha360_HIGH59 | 0.993085 | 0.006915 | 88183 | 88797 |
| alpha360_LOW0 | 0.995957 | 0.004043 | 88438 | 88797 |
| alpha360_LOW5 | 0.994257 | 0.005743 | 88287 | 88797 |
| alpha360_LOW20 | 0.993277 | 0.006723 | 88200 | 88797 |
| alpha360_LOW59 | 0.993085 | 0.006915 | 88183 | 88797 |
| alpha360_VWAP0 | 0.995957 | 0.004043 | 88438 | 88797 |
| alpha360_VWAP5 | 0.994257 | 0.005743 | 88287 | 88797 |
| alpha360_VWAP20 | 0.993277 | 0.006723 | 88200 | 88797 |
| alpha360_VWAP59 | 0.993085 | 0.006915 | 88183 | 88797 |
| alpha360_VOLUME0 | 0.995957 | 0.004043 | 88438 | 88797 |
| alpha360_VOLUME5 | 0.994257 | 0.005743 | 88287 | 88797 |
| alpha360_VOLUME20 | 0.993277 | 0.006723 | 88200 | 88797 |
| alpha360_VOLUME59 | 0.993085 | 0.006915 | 88183 | 88797 |

## Boundary

- This is an adapter smoke run only.
- Catalog entries stay disabled/non-runnable until V4 evaluation and promotion pass.
- Downstream evaluation must keep data_quality and tradability as mandatory prefilters.

## Output Files

- `factor_frame.pkl`
- `expression_table.csv`
- `expression_frame_summary.csv`
- `expression_frame_sample.csv`
- `expression_frame_manifest.json`
