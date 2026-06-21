# Provider Data Capability Inventory

- Provider: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Purpose: decide which open-source factor evaluation capabilities can be enabled without inventing missing data.

## Capability Inventory

| capability | status | available_items | use | next_action |
| --- | --- | --- | --- | --- |
| price_ohlc | available | close,high,low,open | price, momentum, reversal, volatility, drawdown factors | ready |
| volume_liquidity | available | amount,volume,vwap | liquidity, price-volume, turnover proxies | ready |
| adjustment | available | adjclose,factor | corporate-action-aware price research | validate semantics before custom adjusted factors |
| index_membership | available | csi1000,csi300,csi500,csi800,csiall | universe stability and cross-universe factor evaluation | ready |
| benchmark_returns | available | CSI300,CSI500,CSI1000 | benchmark-relative factor and portfolio diagnostics | add benchmark adapter |
| listing_lifecycle | available | instrument start/end intervals | listing age and point-in-time universe eligibility | derive listing_age_days |
| industry_classification | needs_external_source |  | industry IC, industry-neutral returns, group analysis | select point-in-time industry data source |
| market_cap | needs_external_source |  | size exposure, cap weighting, size-neutral evaluation | select total/float market-cap data source |
| fundamentals | needs_external_source |  | value, quality, profitability, growth factors | defer until source/licensing decision |
| tradability_constraints | available_external_layer | can_buy,can_sell,liquidity_bucket,tradability_score,data_quality_status | mandatory prefilter before all factor evaluation | continue reusing outputs/tradability and outputs/data_quality_tradability |

## Feature File Presence

| field | instrument_count | feature_instrument_count | file_presence_rate |
| --- | --- | --- | --- |
| adjclose | 6106 | 6106 | 1.0 |
| amount | 6106 | 6106 | 1.0 |
| change | 6106 | 6106 | 1.0 |
| close | 6106 | 6106 | 1.0 |
| factor | 6106 | 6106 | 1.0 |
| high | 6106 | 6106 | 1.0 |
| low | 6106 | 6106 | 1.0 |
| open | 6106 | 6106 | 1.0 |
| volume | 6106 | 6106 | 1.0 |
| vwap | 6106 | 6106 | 1.0 |

## Sample Coverage

| field | mean | min | max |
| --- | --- | --- | --- |
| adjclose | 1.0 | 1.0 | 1.0 |
| amount | 1.0 | 1.0 | 1.0 |
| close | 1.0 | 1.0 | 1.0 |
| factor | 1.0 | 1.0 | 1.0 |
| high | 1.0 | 1.0 | 1.0 |
| low | 1.0 | 1.0 | 1.0 |
| open | 1.0 | 1.0 | 1.0 |
| volume | 1.0 | 1.0 | 1.0 |
| vwap | 1.0 | 1.0 | 1.0 |

## Instrument Lists

| instrument_list | row_count | has_lifecycle_intervals | path |
| --- | --- | --- | --- |
| all | 6106 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/all.txt |
| all_stock_shsz | 5532 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/all_stock_shsz.txt |
| all_stock_shsz_liquid2000 | 2000 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/all_stock_shsz_liquid2000.txt |
| csi1000 | 32005 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/csi1000.txt |
| csi300 | 15898 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/csi300.txt |
| csi500 | 22000 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/csi500.txt |
| csi800 | 58404 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/csi800.txt |
| csiall | 119178 | True | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived/instruments/csiall.txt |
