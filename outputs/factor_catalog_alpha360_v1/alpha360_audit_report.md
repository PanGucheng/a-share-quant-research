# Qlib Alpha360 Catalog Audit V1

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Qlib source: `E:/qlib_prj/qlib_clone`
- Qlib commit: `d5379c520f66a39953bad76234a7019a72796fd0`
- Source function: `qlib.contrib.data.loader.Alpha360DL.get_feature_config`
- License: `MIT`

## Scope

This audit extracts the 360 normalized price/volume lag expressions from the local Qlib source and checks whether their raw fields exist in the current provider. It does not mark Alpha360 entries as runnable.

## Status Summary

| field_status | factor_count |
| --- | --- |
| available | 360 |

## Family Summary

| family | field_status | factor_count |
| --- | --- | --- |
| CLOSE | available | 60 |
| HIGH | available | 60 |
| LOW | available | 60 |
| OPEN | available | 60 |
| VOLUME | available | 60 |
| VWAP | available | 60 |

## Field Usage

| field | factor_count | provider_presence_rate |
| --- | --- | --- |
| close | 300 | 1.000000 |
| high | 60 | 1.000000 |
| low | 60 | 1.000000 |
| open | 60 | 1.000000 |
| volume | 60 | 1.000000 |
| vwap | 60 | 1.000000 |

## Smoke Catalog Preview

| factor_name | catalog_name | family | lag | required_fields | field_status | expression |
| --- | --- | --- | --- | --- | --- | --- |
| CLOSE0 | alpha360_CLOSE0 | CLOSE | 0 | $close | available | $close/$close |
| CLOSE5 | alpha360_CLOSE5 | CLOSE | 5 | $close | available | Ref($close, 5)/$close |
| CLOSE20 | alpha360_CLOSE20 | CLOSE | 20 | $close | available | Ref($close, 20)/$close |
| CLOSE59 | alpha360_CLOSE59 | CLOSE | 59 | $close | available | Ref($close, 59)/$close |
| OPEN0 | alpha360_OPEN0 | OPEN | 0 | $close,$open | available | $open/$close |
| OPEN5 | alpha360_OPEN5 | OPEN | 5 | $close,$open | available | Ref($open, 5)/$close |
| OPEN20 | alpha360_OPEN20 | OPEN | 20 | $close,$open | available | Ref($open, 20)/$close |
| OPEN59 | alpha360_OPEN59 | OPEN | 59 | $close,$open | available | Ref($open, 59)/$close |
| HIGH0 | alpha360_HIGH0 | HIGH | 0 | $close,$high | available | $high/$close |
| HIGH5 | alpha360_HIGH5 | HIGH | 5 | $close,$high | available | Ref($high, 5)/$close |
| HIGH20 | alpha360_HIGH20 | HIGH | 20 | $close,$high | available | Ref($high, 20)/$close |
| HIGH59 | alpha360_HIGH59 | HIGH | 59 | $close,$high | available | Ref($high, 59)/$close |
| LOW0 | alpha360_LOW0 | LOW | 0 | $close,$low | available | $low/$close |
| LOW5 | alpha360_LOW5 | LOW | 5 | $close,$low | available | Ref($low, 5)/$close |
| LOW20 | alpha360_LOW20 | LOW | 20 | $close,$low | available | Ref($low, 20)/$close |
| LOW59 | alpha360_LOW59 | LOW | 59 | $close,$low | available | Ref($low, 59)/$close |
| VWAP0 | alpha360_VWAP0 | VWAP | 0 | $close,$vwap | available | $vwap/$close |
| VWAP5 | alpha360_VWAP5 | VWAP | 5 | $close,$vwap | available | Ref($vwap, 5)/$close |
| VWAP20 | alpha360_VWAP20 | VWAP | 20 | $close,$vwap | available | Ref($vwap, 20)/$close |
| VWAP59 | alpha360_VWAP59 | VWAP | 59 | $close,$vwap | available | Ref($vwap, 59)/$close |
| VOLUME0 | alpha360_VOLUME0 | VOLUME | 0 | $volume | available | $volume/($volume+1e-12) |
| VOLUME5 | alpha360_VOLUME5 | VOLUME | 5 | $volume | available | Ref($volume, 5)/($volume+1e-12) |
| VOLUME20 | alpha360_VOLUME20 | VOLUME | 20 | $volume | available | Ref($volume, 20)/($volume+1e-12) |
| VOLUME59 | alpha360_VOLUME59 | VOLUME | 59 | $volume | available | Ref($volume, 59)/($volume+1e-12) |

## Output Files

- `provider_field_presence.csv`
- `alpha360_formula_inventory.csv`
- `alpha360_field_usage.csv`
- `alpha360_catalog_all.yaml`
- `alpha360_catalog_smoke.yaml`
- `alpha360_audit_report.md`

## Next Step

Build a small Qlib expression frame from `alpha360_catalog_smoke.yaml`, then run V4 smoke evaluation before any promotion.
