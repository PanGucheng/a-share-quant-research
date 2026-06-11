# Linear Factor Model Sanity Check

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Feature range: `2010-01-01` to `2020-08-01`
- Label: `label_5d_t1`
- Train end: `2016-12-31`
- Test start: `2017-01-01`
- Model: `StandardScaler + Ridge(alpha=1.0)`

| metric | value |
| --- | ---: |
| ic_mean | `-0.007321` |
| icir | `-0.082846` |
| rank_ic_mean | `-0.000956` |
| rank_icir | `-0.009671` |
| test_dates | `865` |
| prediction_rows | `1614771` |
