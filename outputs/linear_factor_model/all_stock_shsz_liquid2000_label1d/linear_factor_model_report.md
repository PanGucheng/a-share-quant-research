# Linear Factor Model Sanity Check

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Feature range: `2010-01-01` to `2020-08-01`
- Label: `label_1d_t1`
- Train end: `2016-12-31`
- Test start: `2017-01-01`
- Model: `StandardScaler + Ridge(alpha=1.0)`

| metric | value |
| --- | ---: |
| ic_mean | `0.003672` |
| icir | `0.042713` |
| rank_ic_mean | `0.029948` |
| rank_icir | `0.326393` |
| test_dates | `869` |
| prediction_rows | `1628000` |
