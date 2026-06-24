# Alpha158 Expression Frame V1

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2020-10-01` to `2024-02-29`
- Factor count: `20`
- Catalog: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha158_v1/alpha158_catalog_first_batch.yaml`
- Inventory: `E:/qlib_prj/qlib_baseline/outputs/factor_catalog_alpha158_v1/alpha158_formula_inventory.csv`

## Expression Table

| catalog_name | factor_name | category | expression |
| --- | --- | --- | --- |
| alpha158_KMID | KMID | kbar | ($close-$open)/$open |
| alpha158_KLEN | KLEN | kbar | ($high-$low)/$open |
| alpha158_KMID2 | KMID2 | kbar | ($close-$open)/($high-$low+1e-12) |
| alpha158_KUP | KUP | kbar | ($high-Greater($open, $close))/$open |
| alpha158_KUP2 | KUP2 | kbar | ($high-Greater($open, $close))/($high-$low+1e-12) |
| alpha158_KLOW | KLOW | kbar | (Less($open, $close)-$low)/$open |
| alpha158_KLOW2 | KLOW2 | kbar | (Less($open, $close)-$low)/($high-$low+1e-12) |
| alpha158_KSFT | KSFT | kbar | (2*$close-$high-$low)/$open |
| alpha158_KSFT2 | KSFT2 | kbar | (2*$close-$high-$low)/($high-$low+1e-12) |
| alpha158_OPEN0 | OPEN0 | price_volume_lag | $open/$close |
| alpha158_HIGH0 | HIGH0 | price_volume_lag | $high/$close |
| alpha158_LOW0 | LOW0 | price_volume_lag | $low/$close |
| alpha158_VWAP0 | VWAP0 | price_volume_lag | $vwap/$close |
| alpha158_ROC5 | ROC5 | rolling_price | Ref($close, 5)/$close |
| alpha158_ROC10 | ROC10 | rolling_price | Ref($close, 10)/$close |
| alpha158_ROC20 | ROC20 | rolling_price | Ref($close, 20)/$close |
| alpha158_ROC30 | ROC30 | rolling_price | Ref($close, 30)/$close |
| alpha158_ROC60 | ROC60 | rolling_price | Ref($close, 60)/$close |
| alpha158_MA5 | MA5 | rolling_price | Mean($close, 5)/$close |
| alpha158_MA10 | MA10 | rolling_price | Mean($close, 10)/$close |

## Coverage

| factor | coverage | missing_rate | valid_rows | total_rows |
| --- | --- | --- | --- | --- |
| alpha158_KMID | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KLEN | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KMID2 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KUP | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KUP2 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KLOW | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KLOW2 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KSFT | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_KSFT2 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_OPEN0 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_HIGH0 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_LOW0 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_VWAP0 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_ROC5 | 0.995139 | 0.004861 | 1596064 | 1603860 |
| alpha158_ROC10 | 0.994550 | 0.005450 | 1595119 | 1603860 |
| alpha158_ROC20 | 0.994235 | 0.005765 | 1594613 | 1603860 |
| alpha158_ROC30 | 0.994231 | 0.005769 | 1594608 | 1603860 |
| alpha158_ROC60 | 0.994271 | 0.005729 | 1594671 | 1603860 |
| alpha158_MA5 | 0.996408 | 0.003592 | 1598099 | 1603860 |
| alpha158_MA10 | 0.996408 | 0.003592 | 1598099 | 1603860 |

## Output Files

- `factor_frame.pkl`
- `expression_table.csv`
- `expression_frame_summary.csv`
- `expression_frame_sample.csv`
- `expression_frame_manifest.json`
