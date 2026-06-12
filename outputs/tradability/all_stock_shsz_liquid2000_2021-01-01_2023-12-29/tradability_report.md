# A-share Tradability Label Report

## Scope

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Date range: `2021-01-01` to `2023-12-29`
- Data quality directory: `outputs/data_quality_tradability/all_stock_shsz_liquid2000_2021-01-01_2023-12-29`
- Liquidity source used: `amount`

## Overall Tradability

| metric | value |
| --- | --- |
| market | all_stock_shsz_liquid2000 |
| start_time | 2021-01-01 |
| end_time | 2023-12-29 |
| provider_uri | E:/qlib_prj/qlib_data/cn_data_community_20260609_derived |
| rows | 1414832 |
| instruments | 1977 |
| dates | 727 |
| can_buy_rate | 0.5854928358985377 |
| can_sell_rate | 0.9913381942166986 |
| avg_tradability_score | 89.0552411876463 |
| liquidity_source | amount |
| warning_count | 2 |
| is_suspended_rate | 0.003500768995894919 |
| is_suspended_count | 4953 |
| is_limit_up_rate | 0.012141370848270324 |
| is_limit_up_count | 17178 |
| is_limit_down_rate | 0.0032753005303809922 |
| is_limit_down_count | 4634 |
| is_one_price_limit_up_rate | 0.0007781842649869383 |
| is_one_price_limit_up_count | 1101 |
| is_one_price_limit_down_rate | 0.0002593947549956461 |
| is_one_price_limit_down_count | 367 |
| is_low_liquidity_rate | 0.3987038743822588 |
| is_low_liquidity_count | 564099 |
| is_new_listing_rate | 0.0 |
| is_new_listing_count | 0 |
| has_price_anomaly_rate | 0.0 |
| has_price_anomaly_count | 0 |
| has_volume_anomaly_rate | 0.0 |
| has_volume_anomaly_count | 0 |
| has_core_missing_rate | 0.003500768995894919 |
| has_core_missing_count | 4953 |

## Disabled Reasons

| reason | count |
| --- | --- |
| low_liquidity | 564099 |
| limit_up | 17178 |
| unknown_limit | 7621 |
| core_missing | 4953 |
| suspended | 4953 |
| unknown_liquidity | 4953 |
| limit_down | 4634 |
| one_price_limit_up | 1101 |
| one_price_limit_down | 367 |

## Date Coverage

| datetime | instrument_count | can_buy_count | can_sell_count | can_buy_rate | can_sell_rate | avg_tradability_score | suspended_count | limit_up_count | limit_down_count | low_liquidity_count | core_missing_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021-01-04 | 1977 | 0 | 0 | 0.000000 | 0.000000 | 69.506829 | 14 | 0 | 0 | 785 | 14 |
| 2021-01-05 | 1977 | 1138 | 1952 | 0.575620 | 0.987355 | 88.275164 | 13 | 43 | 11 | 786 | 13 |
| 2021-01-06 | 1977 | 1158 | 1956 | 0.585736 | 0.989378 | 88.821447 | 12 | 22 | 8 | 786 | 12 |
| 2021-01-07 | 1977 | 1159 | 1955 | 0.586242 | 0.988872 | 88.930197 | 11 | 20 | 10 | 787 | 11 |
| 2021-01-08 | 1977 | 1153 | 1954 | 0.583207 | 0.988366 | 88.707638 | 11 | 30 | 12 | 787 | 11 |
| 2021-01-11 | 1977 | 1162 | 1935 | 0.587759 | 0.978756 | 88.449671 | 15 | 19 | 27 | 785 | 15 |
| 2021-01-12 | 1977 | 1140 | 1957 | 0.576631 | 0.989884 | 88.469904 | 15 | 42 | 4 | 785 | 15 |
| 2021-01-13 | 1977 | 1159 | 1954 | 0.586242 | 0.988366 | 88.836621 | 15 | 19 | 8 | 785 | 15 |
| 2021-01-14 | 1977 | 1151 | 1936 | 0.582195 | 0.979262 | 88.176530 | 18 | 30 | 23 | 784 | 18 |
| 2021-01-15 | 1977 | 1143 | 1947 | 0.578149 | 0.984825 | 88.275164 | 20 | 33 | 10 | 783 | 20 |

## Lowest Instrument Scores

| instrument | row_count | can_buy_rate | can_sell_rate | avg_tradability_score | suspended_rate | low_liquidity_rate | core_missing_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SZ002260 | 350 | 0.000000 | 0.045714 | 3.700000 | 0.914286 | 0.085714 | 0.914286 |
| SZ002450 | 96 | 0.020833 | 0.093750 | 8.125000 | 0.687500 | 0.291667 | 0.687500 |
| SZ000760 | 134 | 0.000000 | 0.119403 | 9.402985 | 0.776119 | 0.223881 | 0.776119 |
| SZ002359 | 134 | 0.000000 | 0.156716 | 12.164179 | 0.776119 | 0.223881 | 0.776119 |
| SZ002711 | 128 | 0.000000 | 0.164062 | 12.500000 | 0.765625 | 0.234375 | 0.765625 |
| SH600891 | 79 | 0.000000 | 0.215190 | 17.468354 | 0.620253 | 0.379747 | 0.620253 |
| SH600701 | 75 | 0.000000 | 0.266667 | 18.333333 | 0.600000 | 0.400000 | 0.600000 |
| SH600086 | 43 | 0.023256 | 0.465116 | 36.744186 | 0.302326 | 0.674419 | 0.302326 |
| SZ000662 | 64 | 0.000000 | 0.484375 | 38.046875 | 0.406250 | 0.593750 | 0.406250 |
| SZ000670 | 727 | 0.404402 | 0.429161 | 42.503439 | 0.559835 | 0.012380 | 0.559835 |
| SZ300330 | 577 | 0.121317 | 0.857886 | 67.686308 | 0.136915 | 0.738302 | 0.136915 |
| SH600781 | 596 | 0.035235 | 0.892617 | 68.145973 | 0.098993 | 0.865772 | 0.098993 |
| SH600090 | 360 | 0.086111 | 0.886111 | 68.916667 | 0.108333 | 0.805556 | 0.108333 |
| SH600555 | 364 | 0.002747 | 0.914835 | 68.983516 | 0.079670 | 0.917582 | 0.079670 |
| SZ000613 | 358 | 0.103352 | 0.888268 | 69.078212 | 0.094972 | 0.779330 | 0.094972 |
| SH600093 | 350 | 0.331429 | 0.808571 | 69.428571 | 0.174286 | 0.485714 | 0.174286 |
| SZ000502 | 356 | 0.008427 | 0.921348 | 69.620787 | 0.061798 | 0.929775 | 0.061798 |
| SZ002499 | 554 | 0.001805 | 0.931408 | 69.972924 | 0.064982 | 0.933213 | 0.064982 |
| SZ300367 | 359 | 0.036212 | 0.916435 | 70.111421 | 0.072423 | 0.891365 | 0.072423 |
| SH600870 | 355 | 0.019718 | 0.932394 | 70.267606 | 0.059155 | 0.921127 | 0.059155 |

## Impact Notes

- Suspensions: `4953` rows.
- Limit up/down: `17178` limit-up rows, `4634` limit-down rows.
- One-price limits: `1101` one-price limit-up rows, `367` one-price limit-down rows.
- Low liquidity: `564099` rows.
- New listing filter: `0` rows.
- Data quality impact: price anomalies `0`, volume anomalies `0`, core missing `4953`.

## Warnings

| warning |
| --- |
| price_anomalies unavailable or empty; price anomaly flags may be incomplete. |
| volume_amount_anomalies unavailable or empty; volume anomaly flags may be incomplete. |
