# Qlib Alpha158 Catalog Audit V1

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Qlib source: `E:/qlib_prj/qlib_clone`
- Qlib commit: `d5379c520f66a39953bad76234a7019a72796fd0`
- Source function: `qlib.contrib.data.loader.Alpha158DL.get_feature_config`
- License: `MIT`

## Scope

This audit extracts Alpha158 formulas from the local Qlib source and checks whether their raw fields exist in the current provider. It does not run factor evaluation and does not mark Alpha158 entries as runnable yet.

## Status Summary

| field_status | factor_count |
| --- | --- |
| available | 158 |

## Category Summary

| category | field_status | factor_count |
| --- | --- | --- |
| kbar | available | 9 |
| price_momentum_balance | available | 30 |
| price_volume_correlation | available | 10 |
| price_volume_lag | available | 4 |
| rolling_price | available | 75 |
| volume_liquidity | available | 30 |

## Field Usage

| field | factor_count | provider_presence_rate |
| --- | --- | --- |
| close | 117 | 1.000000 |
| high | 28 | 1.000000 |
| low | 28 | 1.000000 |
| open | 9 | 1.000000 |
| volume | 40 | 1.000000 |
| vwap | 1 | 1.000000 |

## First Batch Preview

| factor_name | catalog_name | category | required_fields | field_status | expression |
| --- | --- | --- | --- | --- | --- |
| KMID | alpha158_KMID | kbar | $close,$open | available | ($close-$open)/$open |
| KLEN | alpha158_KLEN | kbar | $high,$low,$open | available | ($high-$low)/$open |
| KMID2 | alpha158_KMID2 | kbar | $close,$high,$low,$open | available | ($close-$open)/($high-$low+1e-12) |
| KUP | alpha158_KUP | kbar | $close,$high,$open | available | ($high-Greater($open, $close))/$open |
| KUP2 | alpha158_KUP2 | kbar | $close,$high,$low,$open | available | ($high-Greater($open, $close))/($high-$low+1e-12) |
| KLOW | alpha158_KLOW | kbar | $close,$low,$open | available | (Less($open, $close)-$low)/$open |
| KLOW2 | alpha158_KLOW2 | kbar | $close,$high,$low,$open | available | (Less($open, $close)-$low)/($high-$low+1e-12) |
| KSFT | alpha158_KSFT | kbar | $close,$high,$low,$open | available | (2*$close-$high-$low)/$open |
| KSFT2 | alpha158_KSFT2 | kbar | $close,$high,$low | available | (2*$close-$high-$low)/($high-$low+1e-12) |
| OPEN0 | alpha158_OPEN0 | price_volume_lag | $close,$open | available | $open/$close |
| HIGH0 | alpha158_HIGH0 | price_volume_lag | $close,$high | available | $high/$close |
| LOW0 | alpha158_LOW0 | price_volume_lag | $close,$low | available | $low/$close |
| VWAP0 | alpha158_VWAP0 | price_volume_lag | $close,$vwap | available | $vwap/$close |
| ROC5 | alpha158_ROC5 | rolling_price | $close | available | Ref($close, 5)/$close |
| ROC10 | alpha158_ROC10 | rolling_price | $close | available | Ref($close, 10)/$close |
| ROC20 | alpha158_ROC20 | rolling_price | $close | available | Ref($close, 20)/$close |
| ROC30 | alpha158_ROC30 | rolling_price | $close | available | Ref($close, 30)/$close |
| ROC60 | alpha158_ROC60 | rolling_price | $close | available | Ref($close, 60)/$close |
| MA5 | alpha158_MA5 | rolling_price | $close | available | Mean($close, 5)/$close |
| MA10 | alpha158_MA10 | rolling_price | $close | available | Mean($close, 10)/$close |

## Output Files

- `alpha158_formula_inventory.csv`
- `alpha158_field_usage.csv`
- `alpha158_catalog_all.yaml`
- `alpha158_catalog_first_batch.yaml`
- `alpha158_audit_report.md`

## Next Step

Build and validate a Qlib expression adapter before setting these entries to `runnable: true`.
