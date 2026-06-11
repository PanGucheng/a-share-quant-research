# Linear Factor Model Sanity Check

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `csi500`
- Feature range: `2010-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Train end: `2016-12-31`
- Test start: `2017-01-01`
- Model: `StandardScaler + Ridge(alpha=1.0)`

| metric | value |
| --- | ---: |
| ic_mean | `0.001525` |
| icir | `0.011540` |
| rank_ic_mean | `0.013532` |
| rank_icir | `0.113278` |
| test_dates | `869` |
| prediction_rows | `405956` |
