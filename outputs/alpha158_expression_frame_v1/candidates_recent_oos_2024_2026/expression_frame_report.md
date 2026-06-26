# Alpha158 Expression Frame V1

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Factor count: `14`
- Catalog: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha158_v1/alpha158_catalog_all.yaml`
- Inventory: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv`

## Expression Table

| catalog_name | factor_name | category | expression |
| --- | --- | --- | --- |
| alpha158_ROC10 | ROC10 | rolling_price | Ref($close, 10)/$close |
| alpha158_ROC30 | ROC30 | rolling_price | Ref($close, 30)/$close |
| alpha158_ROC60 | ROC60 | rolling_price | Ref($close, 60)/$close |
| alpha158_MIN5 | MIN5 | rolling_price | Min($low, 5)/$close |
| alpha158_MIN10 | MIN10 | rolling_price | Min($low, 10)/$close |
| alpha158_MIN30 | MIN30 | rolling_price | Min($low, 30)/$close |
| alpha158_MIN60 | MIN60 | rolling_price | Min($low, 60)/$close |
| alpha158_QTLD10 | QTLD10 | rolling_price | Quantile($close, 10, 0.2)/$close |
| alpha158_QTLD30 | QTLD30 | rolling_price | Quantile($close, 30, 0.2)/$close |
| alpha158_QTLD60 | QTLD60 | rolling_price | Quantile($close, 60, 0.2)/$close |
| alpha158_IMIN20 | IMIN20 | rolling_price | IdxMin($low, 20)/20 |
| alpha158_IMIN30 | IMIN30 | rolling_price | IdxMin($low, 30)/30 |
| alpha158_IMIN60 | IMIN60 | rolling_price | IdxMin($low, 60)/60 |
| alpha158_VSUMN60 | VSUMN60 | volume_liquidity | Sum(Greater(Ref($volume, 1)-$volume, 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12) |

## Coverage

| factor | coverage | missing_rate | valid_rows | total_rows |
| --- | --- | --- | --- | --- |
| alpha158_ROC10 | 0.996012 | 0.003988 | 1091859 | 1096231 |
| alpha158_ROC30 | 0.995898 | 0.004102 | 1091734 | 1096231 |
| alpha158_ROC60 | 0.996052 | 0.003948 | 1091903 | 1096231 |
| alpha158_MIN5 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_MIN10 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_MIN30 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_MIN60 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_QTLD10 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_QTLD30 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_QTLD60 | 0.997657 | 0.002343 | 1093663 | 1096231 |
| alpha158_IMIN20 | 0.999573 | 0.000427 | 1095763 | 1096231 |
| alpha158_IMIN30 | 0.999777 | 0.000223 | 1095986 | 1096231 |
| alpha158_IMIN60 | 0.999985 | 0.000015 | 1096215 | 1096231 |
| alpha158_VSUMN60 | 0.999984 | 0.000016 | 1096214 | 1096231 |

## Output Files

- `factor_frame.pkl`
- `expression_table.csv`
- `expression_frame_summary.csv`
- `expression_frame_sample.csv`
- `expression_frame_manifest.json`
