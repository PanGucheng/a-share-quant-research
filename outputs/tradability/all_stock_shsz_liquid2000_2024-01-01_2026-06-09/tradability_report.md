# A-share Tradability Label Report

## Scope

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2024-01-01` to `2026-06-09`
- Data quality directory: `outputs/data_quality_tradability/all_stock_shsz_liquid2000_2024-01-01_2026-06-09`
- Liquidity source used: `amount`

## Overall Tradability

| metric | value |
| --- | --- |
| market | all_stock_shsz_liquid2000 |
| start_time | 2024-01-01 |
| end_time | 2026-06-09 |
| provider_uri | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived |
| rows | 1096231 |
| instruments | 1904 |
| dates | 587 |
| can_buy_rate | 0.5835959756657128 |
| can_sell_rate | 0.9895733654676797 |
| avg_tradability_score | 88.91877715554477 |
| liquidity_source | amount |
| warning_count | 2 |
| is_suspended_rate | 0.002342571957917629 |
| is_suspended_count | 2568 |
| is_limit_up_rate | 0.0155651500459301 |
| is_limit_up_count | 17063 |
| is_limit_down_rate | 0.005880147523651493 |
| is_limit_down_count | 6446 |
| is_one_price_limit_up_rate | 0.0011804081439039764 |
| is_one_price_limit_up_count | 1294 |
| is_one_price_limit_down_rate | 0.0003867797936748733 |
| is_one_price_limit_down_count | 424 |
| is_low_liquidity_rate | 0.3991686058868979 |
| is_low_liquidity_count | 437581 |
| is_new_listing_rate | 0.0 |
| is_new_listing_count | 0 |
| has_price_anomaly_rate | 0.0 |
| has_price_anomaly_count | 0 |
| has_volume_anomaly_rate | 0.0 |
| has_volume_anomaly_count | 0 |
| has_core_missing_rate | 0.002342571957917629 |
| has_core_missing_count | 2568 |

## Disabled Reasons

| reason | count |
| --- | --- |
| low_liquidity | 437581 |
| limit_up | 17063 |
| limit_down | 6446 |
| unknown_limit | 4984 |
| core_missing | 2568 |
| suspended | 2568 |
| unknown_liquidity | 2568 |
| one_price_limit_up | 1294 |
| one_price_limit_down | 424 |

## Date Coverage

| datetime | instrument_count | can_buy_count | can_sell_count | can_buy_rate | can_sell_rate | avg_tradability_score | suspended_count | limit_up_count | limit_down_count | low_liquidity_count | core_missing_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-01-02 | 1904 | 0 | 0 | 0.000000 | 0.000000 | 69.852941 | 4 | 0 | 0 | 760 | 4 |
| 2024-01-03 | 1904 | 1129 | 1896 | 0.592962 | 0.995798 | 89.503676 | 4 | 11 | 4 | 760 | 4 |
| 2024-01-04 | 1904 | 1130 | 1900 | 0.593487 | 0.997899 | 89.595588 | 4 | 10 | 0 | 760 | 4 |
| 2024-01-05 | 1904 | 1133 | 1896 | 0.595063 | 0.995798 | 89.624475 | 3 | 6 | 4 | 761 | 3 |
| 2024-01-08 | 1904 | 1129 | 1900 | 0.592962 | 0.997899 | 89.629727 | 3 | 11 | 1 | 761 | 3 |
| 2024-01-09 | 1902 | 1130 | 1899 | 0.594111 | 0.998423 | 89.723975 | 1 | 10 | 2 | 761 | 1 |
| 2024-01-10 | 1902 | 1128 | 1894 | 0.593060 | 0.995794 | 89.637224 | 0 | 12 | 7 | 761 | 0 |
| 2024-01-11 | 1902 | 1119 | 1901 | 0.588328 | 0.999474 | 89.534700 | 0 | 23 | 1 | 761 | 0 |
| 2024-01-12 | 1902 | 1133 | 1899 | 0.595689 | 0.998423 | 89.718717 | 2 | 8 | 1 | 760 | 2 |
| 2024-01-15 | 1902 | 1130 | 1897 | 0.594111 | 0.997371 | 89.692429 | 1 | 9 | 3 | 761 | 1 |

## Lowest Instrument Scores

| instrument | row_count | can_buy_rate | can_sell_rate | avg_tradability_score | suspended_rate | low_liquidity_rate | core_missing_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SH600290 | 5 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 0.000000 | 1.000000 |
| SZ002776 | 5 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 0.000000 | 1.000000 |
| SZ000976 | 136 | 0.080882 | 0.654412 | 51.911765 | 0.330882 | 0.588235 | 0.330882 |
| SH600647 | 115 | 0.008696 | 0.686957 | 52.869565 | 0.286957 | 0.704348 | 0.286957 |
| SZ002433 | 121 | 0.033058 | 0.743802 | 56.942149 | 0.239669 | 0.727273 | 0.239669 |
| SZ000040 | 299 | 0.153846 | 0.698997 | 57.357860 | 0.277592 | 0.568562 | 0.277592 |
| SZ000996 | 116 | 0.000000 | 0.767241 | 58.232759 | 0.206897 | 0.793103 | 0.206897 |
| SZ002308 | 156 | 0.346154 | 0.641026 | 58.685897 | 0.288462 | 0.314103 | 0.288462 |
| SZ002087 | 116 | 0.000000 | 0.775862 | 58.836207 | 0.206897 | 0.793103 | 0.206897 |
| SH600766 | 115 | 0.000000 | 0.773913 | 59.043478 | 0.200000 | 0.800000 | 0.200000 |
| SZ000413 | 150 | 0.373333 | 0.680000 | 61.100000 | 0.300000 | 0.320000 | 0.300000 |
| SH600387 | 363 | 0.008264 | 0.909091 | 68.842975 | 0.082645 | 0.909091 | 0.082645 |
| SZ002656 | 587 | 0.005111 | 0.913118 | 68.986371 | 0.080068 | 0.914821 | 0.080068 |
| SZ300208 | 373 | 0.158177 | 0.871314 | 69.772118 | 0.104558 | 0.726542 | 0.104558 |
| SH600289 | 587 | 0.054514 | 0.906303 | 69.804089 | 0.085179 | 0.860307 | 0.085179 |
| SZ000584 | 367 | 0.122616 | 0.893733 | 70.449591 | 0.098093 | 0.779292 | 0.098093 |
| SZ300280 | 428 | 0.675234 | 0.712617 | 70.981308 | 0.268692 | 0.046729 | 0.268692 |
| SH603377 | 587 | 0.105622 | 0.909710 | 71.448041 | 0.073254 | 0.809199 | 0.073254 |
| SH600193 | 587 | 0.093697 | 0.921635 | 71.516184 | 0.045997 | 0.851789 | 0.045997 |
| SH600599 | 587 | 0.042589 | 0.948893 | 72.717206 | 0.042589 | 0.913118 | 0.042589 |

## Impact Notes

- Suspensions: `2568` rows.
- Limit up/down: `17063` limit-up rows, `6446` limit-down rows.
- One-price limits: `1294` one-price limit-up rows, `424` one-price limit-down rows.
- Low liquidity: `437581` rows.
- New listing filter: `0` rows.
- Data quality impact: price anomalies `0`, volume anomalies `0`, core missing `2568`.

## Warnings

| warning |
| --- |
| price_anomalies unavailable or empty; price anomaly flags may be incomplete. |
| volume_amount_anomalies unavailable or empty; volume anomaly flags may be incomplete. |
