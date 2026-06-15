# Factor Research V3 Report

- Provider URI: `E:/qlib_prj/qlib_data/cn_data_community_20260609_derived`
- Market: `all_stock_shsz_liquid2000`
- Labels: `label_20d_t1`
- Base factors: `amplitude_20,std_20,rev_5,ret_20,amount_mean_20,downside_std_20,max_drawdown_20,rev_20_exclude_5,amount_cv_20,corr_ret_amount_20`
- Tradable filter: `can_buy == true`, `liquidity_bucket >= 3`, `tradability_score >= 75.0`

## Main Neutralized Summary

| window | label | factor | expected_direction | coverage | directional_mean_rank_ic | directional_rank_icir | ic_win_rate | ic_dates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| main_research_2021_2023 | label_20d_t1 | amplitude_20__raw | negative | 0.990451 | 0.109863 | 0.594628 | 0.680441 | 726 |
| main_research_2021_2023 | label_20d_t1 | amplitude_20__cs_rank | negative | 0.990451 | 0.109863 | 0.594628 | 0.680441 | 726 |
| main_research_2021_2023 | label_20d_t1 | amplitude_20__cs_zscore | negative | 0.990451 | 0.109818 | 0.594416 | 0.680441 | 726 |
| main_research_2021_2023 | label_20d_t1 | std_20__cs_rank | negative | 0.990084 | 0.094345 | 0.563278 | 0.687328 | 726 |
| main_research_2021_2023 | label_20d_t1 | std_20__raw | negative | 0.990084 | 0.094345 | 0.563278 | 0.687328 | 726 |
| main_research_2021_2023 | label_20d_t1 | std_20__cs_zscore | negative | 0.990084 | 0.094313 | 0.563055 | 0.685950 | 726 |
| main_research_2021_2023 | label_20d_t1 | amplitude_20__liquidity_bucket_zscore | negative | 0.990451 | 0.085272 | 0.476693 | 0.661157 | 726 |
| main_research_2021_2023 | label_20d_t1 | amplitude_20__amount_proxy_residual | negative | 0.990451 | 0.076147 | 0.426710 | 0.639118 | 726 |
| main_research_2021_2023 | label_20d_t1 | std_20__liquidity_bucket_zscore | negative | 0.990084 | 0.068754 | 0.427753 | 0.658402 | 726 |
| main_research_2021_2023 | label_20d_t1 | downside_std_20__raw | negative | 0.990084 | 0.065157 | 0.410552 | 0.643251 | 726 |
| main_research_2021_2023 | label_20d_t1 | downside_std_20__cs_rank | negative | 0.990084 | 0.065157 | 0.410552 | 0.643251 | 726 |
| main_research_2021_2023 | label_20d_t1 | downside_std_20__cs_zscore | negative | 0.990084 | 0.065121 | 0.410374 | 0.643251 | 726 |
| main_research_2021_2023 | label_20d_t1 | std_20__amount_proxy_residual | negative | 0.990084 | 0.061777 | 0.383253 | 0.636364 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_20_exclude_5__cs_rank | positive | 0.995221 | 0.053765 | 0.397930 | 0.666667 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_20_exclude_5__raw | positive | 0.995221 | 0.053765 | 0.397930 | 0.666667 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_20_exclude_5__cs_zscore | positive | 0.995221 | 0.053679 | 0.397275 | 0.666667 | 726 |
| main_research_2021_2023 | label_20d_t1 | amplitude_20__volatility_bucket_zscore | negative | 0.990451 | 0.046659 | 0.674235 | 0.758953 | 726 |
| main_research_2021_2023 | label_20d_t1 | downside_std_20__liquidity_bucket_zscore | negative | 0.990084 | 0.045943 | 0.302795 | 0.617080 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_20_exclude_5__liquidity_bucket_zscore | positive | 0.995221 | 0.042894 | 0.324963 | 0.632231 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_20_exclude_5__amount_proxy_residual | positive | 0.990084 | 0.038830 | 0.288724 | 0.607438 | 726 |
| main_research_2021_2023 | label_20d_t1 | amount_cv_20__amount_proxy_residual | negative | 0.990451 | 0.038497 | 0.447479 | 0.694215 | 726 |
| main_research_2021_2023 | label_20d_t1 | max_drawdown_20__cs_zscore | negative | 0.990451 | 0.030747 | 0.221280 | 0.599174 | 726 |
| main_research_2021_2023 | label_20d_t1 | max_drawdown_20__cs_rank | negative | 0.990451 | 0.030714 | 0.221064 | 0.599174 | 726 |
| main_research_2021_2023 | label_20d_t1 | max_drawdown_20__raw | negative | 0.990451 | 0.030714 | 0.221064 | 0.599174 | 726 |
| main_research_2021_2023 | label_20d_t1 | downside_std_20__amount_proxy_residual | negative | 0.990084 | 0.029761 | 0.200719 | 0.584022 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_5__amount_proxy_residual | positive | 0.990451 | 0.029749 | 0.229657 | 0.579890 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_5__volatility_bucket_zscore | positive | 0.990451 | 0.023577 | 0.191733 | 0.578512 | 726 |
| main_research_2021_2023 | label_20d_t1 | amount_cv_20__liquidity_bucket_zscore | negative | 0.990451 | 0.022557 | 0.241084 | 0.596419 | 726 |
| main_research_2021_2023 | label_20d_t1 | rev_20_exclude_5__volatility_bucket_zscore | positive | 0.990084 | 0.021687 | 0.180158 | 0.570248 | 726 |
| main_research_2021_2023 | label_20d_t1 | max_drawdown_20__liquidity_bucket_zscore | negative | 0.990451 | 0.020433 | 0.152537 | 0.570248 | 726 |

## Neutralization Change Log

| base_factor | neutralization | raw_directional_rank_ic | directional_mean_rank_ic | delta_directional_rank_ic | effect |
| --- | --- | --- | --- | --- | --- |
| amount_cv_20 | amount_proxy_residual | 0.019981 | 0.038497 | 0.018516 | improved |
| amount_cv_20 | liquidity_bucket_zscore | 0.019981 | 0.022557 | 0.002576 | similar |
| amount_cv_20 | cs_rank | 0.019981 | 0.019981 | 0.000000 | similar |
| amount_cv_20 | cs_zscore | 0.019981 | 0.019901 | -0.000080 | similar |
| amount_cv_20 | liquidity_volatility_residual | 0.019981 | 0.005720 | -0.014261 | weakened |
| amount_cv_20 | volatility_bucket_zscore | 0.019981 | -0.004968 | -0.024948 | weakened |
| amount_mean_20 | cs_rank |  |  |  | similar |
| amount_mean_20 | cs_zscore |  |  |  | similar |
| amount_mean_20 | liquidity_bucket_zscore |  |  |  | similar |
| amount_mean_20 | volatility_bucket_zscore |  |  |  | similar |
| amount_mean_20 | amount_proxy_residual |  |  |  | similar |
| amount_mean_20 | liquidity_volatility_residual |  |  |  | similar |
| amplitude_20 | cs_rank | 0.109863 | 0.109863 | 0.000000 | similar |
| amplitude_20 | cs_zscore | 0.109863 | 0.109818 | -0.000045 | similar |
| amplitude_20 | liquidity_bucket_zscore | 0.109863 | 0.085272 | -0.024592 | weakened |
| amplitude_20 | amount_proxy_residual | 0.109863 | 0.076147 | -0.033717 | weakened |
| amplitude_20 | volatility_bucket_zscore | 0.109863 | 0.046659 | -0.063205 | weakened |
| amplitude_20 | liquidity_volatility_residual | 0.109863 | 0.004954 | -0.104909 | weakened |
| corr_ret_amount_20 | cs_rank |  |  |  | similar |
| corr_ret_amount_20 | cs_zscore |  |  |  | similar |
| corr_ret_amount_20 | liquidity_bucket_zscore |  |  |  | similar |
| corr_ret_amount_20 | volatility_bucket_zscore |  |  |  | similar |
| corr_ret_amount_20 | amount_proxy_residual |  |  |  | similar |
| corr_ret_amount_20 | liquidity_volatility_residual |  |  |  | similar |
| downside_std_20 | cs_rank | 0.065157 | 0.065157 | 0.000000 | similar |
| downside_std_20 | cs_zscore | 0.065157 | 0.065121 | -0.000036 | similar |
| downside_std_20 | liquidity_bucket_zscore | 0.065157 | 0.045943 | -0.019214 | weakened |
| downside_std_20 | amount_proxy_residual | 0.065157 | 0.029761 | -0.035396 | weakened |
| downside_std_20 | volatility_bucket_zscore | 0.065157 | -0.015638 | -0.080795 | weakened |
| downside_std_20 | liquidity_volatility_residual | 0.065157 | -0.026763 | -0.091920 | weakened |
| max_drawdown_20 | cs_zscore | 0.030714 | 0.030747 | 0.000033 | similar |
| max_drawdown_20 | cs_rank | 0.030714 | 0.030714 | 0.000000 | similar |
| max_drawdown_20 | liquidity_bucket_zscore | 0.030714 | 0.020433 | -0.010281 | weakened |
| max_drawdown_20 | amount_proxy_residual | 0.030714 | -0.000163 | -0.030877 | weakened |
| max_drawdown_20 | volatility_bucket_zscore | 0.030714 | -0.027149 | -0.057863 | weakened |
| max_drawdown_20 | liquidity_volatility_residual | 0.030714 | -0.034758 | -0.065472 | weakened |
| ret_20 | cs_rank |  |  |  | similar |
| ret_20 | cs_zscore |  |  |  | similar |
| ret_20 | liquidity_bucket_zscore |  |  |  | similar |
| ret_20 | volatility_bucket_zscore |  |  |  | similar |
| ret_20 | amount_proxy_residual |  |  |  | similar |
| ret_20 | liquidity_volatility_residual |  |  |  | similar |
| rev_20_exclude_5 | cs_rank | 0.053765 | 0.053765 | 0.000000 | similar |
| rev_20_exclude_5 | cs_zscore | 0.053765 | 0.053679 | -0.000085 | similar |
| rev_20_exclude_5 | liquidity_bucket_zscore | 0.053765 | 0.042894 | -0.010871 | weakened |
| rev_20_exclude_5 | amount_proxy_residual | 0.053765 | 0.038830 | -0.014935 | weakened |
| rev_20_exclude_5 | volatility_bucket_zscore | 0.053765 | 0.021687 | -0.032077 | weakened |
| rev_20_exclude_5 | liquidity_volatility_residual | 0.053765 | 0.009602 | -0.044163 | weakened |
| rev_5 | amount_proxy_residual | 0.019598 | 0.029749 | 0.010152 | improved |
| rev_5 | volatility_bucket_zscore | 0.019598 | 0.023577 | 0.003980 | similar |

## Exposure Correlation

| window | factor | exposure | mean_spearman_corr | abs_mean_spearman_corr | corr_dates |
| --- | --- | --- | --- | --- | --- |
| recent_oos_2024_2026 | amount_mean_20 | log_amount_mean_20 | 1.000000 | 1.000000 | 586 |
| main_research_2021_2023 | amount_mean_20 | log_amount_mean_20 | 1.000000 | 1.000000 | 726 |
| recent_oos_2024_2026 | amplitude_20 | volatility_bucket | 0.979796 | 0.979796 | 586 |
| main_research_2021_2023 | amplitude_20 | volatility_bucket | 0.979796 | 0.979796 | 726 |
| recent_oos_2024_2026 | amplitude_20 | std_20 | 0.920875 | 0.920875 | 586 |
| recent_oos_2024_2026 | std_20 | amplitude_20 | 0.920875 | 0.920875 | 586 |
| main_research_2021_2023 | amplitude_20 | std_20 | 0.903193 | 0.903193 | 726 |
| main_research_2021_2023 | std_20 | amplitude_20 | 0.903193 | 0.903193 | 726 |
| recent_oos_2024_2026 | std_20 | volatility_bucket | 0.900407 | 0.900407 | 586 |
| main_research_2021_2023 | std_20 | volatility_bucket | 0.881807 | 0.881807 | 726 |
| recent_oos_2024_2026 | downside_std_20 | std_20 | 0.861732 | 0.861732 | 586 |
| main_research_2021_2023 | downside_std_20 | std_20 | 0.816805 | 0.816805 | 726 |
| recent_oos_2024_2026 | downside_std_20 | amplitude_20 | 0.813359 | 0.813359 | 586 |
| recent_oos_2024_2026 | downside_std_20 | volatility_bucket | 0.793770 | 0.793770 | 586 |
| main_research_2021_2023 | amount_mean_20 | liquidity_bucket | 0.781756 | 0.781756 | 726 |
| recent_oos_2024_2026 | amount_mean_20 | liquidity_bucket | 0.776431 | 0.776431 | 586 |
| main_research_2021_2023 | downside_std_20 | amplitude_20 | 0.763392 | 0.763392 | 726 |
| main_research_2021_2023 | downside_std_20 | volatility_bucket | 0.741277 | 0.741277 | 726 |
| recent_oos_2024_2026 | max_drawdown_20 | std_20 | 0.645245 | 0.645245 | 586 |
| recent_oos_2024_2026 | max_drawdown_20 | amplitude_20 | 0.609767 | 0.609767 | 586 |
| recent_oos_2024_2026 | max_drawdown_20 | volatility_bucket | 0.592586 | 0.592586 | 586 |
| main_research_2021_2023 | max_drawdown_20 | std_20 | 0.559589 | 0.559589 | 726 |
| main_research_2021_2023 | max_drawdown_20 | amplitude_20 | 0.534142 | 0.534142 | 726 |
| main_research_2021_2023 | max_drawdown_20 | volatility_bucket | 0.514621 | 0.514621 | 726 |
| recent_oos_2024_2026 | amount_cv_20 | std_20 | 0.452062 | 0.453311 | 586 |
| main_research_2021_2023 | amount_cv_20 | std_20 | 0.389458 | 0.389458 | 726 |
| main_research_2021_2023 | amount_mean_20 | amplitude_20 | 0.364897 | 0.364897 | 726 |
| main_research_2021_2023 | amplitude_20 | log_amount_mean_20 | 0.364897 | 0.364897 | 726 |
| main_research_2021_2023 | amount_mean_20 | volatility_bucket | 0.355577 | 0.355577 | 726 |
| recent_oos_2024_2026 | amount_cv_20 | amplitude_20 | 0.341232 | 0.354628 | 586 |

## Raw Factor Slice Summary

| factor | slice_type | slice_value | coverage | directional_mean_rank_ic | directional_rank_icir | ic_win_rate | ic_dates |
| --- | --- | --- | --- | --- | --- | --- | --- |
| amount_cv_20__raw | liquidity_bucket | 3.0 | 0.989237 | 0.020386 | 0.237736 | 0.607438 | 726 |
| amount_cv_20__raw | liquidity_bucket | 4.0 | 0.990066 | 0.013657 | 0.139241 | 0.549587 | 726 |
| amount_cv_20__raw | liquidity_bucket | 5.0 | 0.992106 | 0.029467 | 0.210236 | 0.586777 | 726 |
| amount_cv_20__raw | market_state | down | 0.990146 | 0.002242 | 0.019213 | 0.543860 | 171 |
| amount_cv_20__raw | market_state | sideways | 0.991538 | 0.034387 | 0.344516 | 0.632411 | 253 |
| amount_cv_20__raw | market_state | unknown | 0.989113 | 0.148761 | 3.047341 | 1.000000 | 10 |
| amount_cv_20__raw | market_state | up | 0.989737 | 0.013477 | 0.167333 | 0.595890 | 292 |
| amount_cv_20__raw | volatility_bucket | 1.0 | 0.998585 | 0.013052 | 0.129226 | 0.548209 | 726 |
| amount_cv_20__raw | volatility_bucket | 2.0 | 0.998526 | -0.004441 | -0.041170 | 0.472452 | 726 |
| amount_cv_20__raw | volatility_bucket | 3.0 | 0.997840 | 0.005126 | 0.048131 | 0.506887 | 726 |
| amount_cv_20__raw | volatility_bucket | 4.0 | 0.997632 | -0.011289 | -0.090853 | 0.461433 | 726 |
| amount_cv_20__raw | volatility_bucket | 5.0 | 0.997545 | -0.026940 | -0.179318 | 0.435262 | 726 |
| amount_cv_20__raw | year_slice | 2021 | 0.987878 | -0.004892 | -0.050459 | 0.516529 | 242 |
| amount_cv_20__raw | year_slice | 2022 | 0.989373 | 0.031621 | 0.306537 | 0.665289 | 242 |
| amount_cv_20__raw | year_slice | 2023 | 0.994130 | 0.033213 | 0.367897 | 0.623967 | 242 |
| amount_mean_20__raw | liquidity_bucket | 3.0 | 0.989237 |  |  |  | 726 |
| amount_mean_20__raw | liquidity_bucket | 4.0 | 0.990066 |  |  |  | 726 |
| amount_mean_20__raw | liquidity_bucket | 5.0 | 0.992106 |  |  |  | 726 |
| amount_mean_20__raw | market_state | down | 0.990146 |  |  |  | 171 |
| amount_mean_20__raw | market_state | sideways | 0.991538 |  |  |  | 253 |
| amount_mean_20__raw | market_state | unknown | 0.989113 |  |  |  | 10 |
| amount_mean_20__raw | market_state | up | 0.989737 |  |  |  | 292 |
| amount_mean_20__raw | volatility_bucket | 1.0 | 0.998585 |  |  |  | 726 |
| amount_mean_20__raw | volatility_bucket | 2.0 | 0.998526 |  |  |  | 726 |
| amount_mean_20__raw | volatility_bucket | 3.0 | 0.997840 |  |  |  | 726 |
| amount_mean_20__raw | volatility_bucket | 4.0 | 0.997632 |  |  |  | 726 |
| amount_mean_20__raw | volatility_bucket | 5.0 | 0.997545 |  |  |  | 726 |
| amount_mean_20__raw | year_slice | 2021 | 0.987878 |  |  |  | 242 |
| amount_mean_20__raw | year_slice | 2022 | 0.989373 |  |  |  | 242 |
| amount_mean_20__raw | year_slice | 2023 | 0.994130 |  |  |  | 242 |
| amplitude_20__raw | liquidity_bucket | 3.0 | 0.989237 | 0.055146 | 0.320761 | 0.622590 | 726 |
| amplitude_20__raw | liquidity_bucket | 4.0 | 0.990066 | 0.082761 | 0.463711 | 0.662534 | 726 |
| amplitude_20__raw | liquidity_bucket | 5.0 | 0.992106 | 0.125203 | 0.557030 | 0.688705 | 726 |
| amplitude_20__raw | market_state | down | 0.990146 | 0.064530 | 0.312313 | 0.631579 | 171 |
| amplitude_20__raw | market_state | sideways | 0.991538 | 0.125050 | 0.693552 | 0.699605 | 253 |
| amplitude_20__raw | market_state | unknown | 0.989113 | 0.167479 | 2.476634 | 1.000000 | 10 |
| amplitude_20__raw | market_state | up | 0.989737 | 0.121281 | 0.698345 | 0.681507 | 292 |
| amplitude_20__raw | volatility_bucket | 1.0 | 0.998585 | 0.045531 | 0.275330 | 0.608815 | 726 |
| amplitude_20__raw | volatility_bucket | 2.0 | 0.998526 | 0.023033 | 0.274915 | 0.595041 | 726 |
| amplitude_20__raw | volatility_bucket | 3.0 | 0.997840 | 0.015237 | 0.208977 | 0.567493 | 726 |
| amplitude_20__raw | volatility_bucket | 4.0 | 0.997632 | 0.024435 | 0.302026 | 0.612948 | 726 |
| amplitude_20__raw | volatility_bucket | 5.0 | 0.997545 | 0.090549 | 0.725206 | 0.778237 | 726 |
| amplitude_20__raw | year_slice | 2021 | 0.987878 | 0.103859 | 0.610672 | 0.648760 | 242 |
| amplitude_20__raw | year_slice | 2022 | 0.989373 | 0.101775 | 0.626757 | 0.694215 | 242 |
| amplitude_20__raw | year_slice | 2023 | 0.994130 | 0.123957 | 0.571177 | 0.698347 | 242 |
| corr_ret_amount_20__raw | liquidity_bucket | 3.0 | 0.988785 |  |  |  | 726 |
| corr_ret_amount_20__raw | liquidity_bucket | 4.0 | 0.989714 |  |  |  | 726 |
| corr_ret_amount_20__raw | liquidity_bucket | 5.0 | 0.991809 |  |  |  | 726 |
| corr_ret_amount_20__raw | market_state | down | 0.989841 |  |  |  | 171 |
| corr_ret_amount_20__raw | market_state | sideways | 0.991273 |  |  |  | 253 |
| corr_ret_amount_20__raw | market_state | unknown | 0.988674 |  |  |  | 10 |
| corr_ret_amount_20__raw | market_state | up | 0.989246 |  |  |  | 292 |
| corr_ret_amount_20__raw | volatility_bucket | 1.0 | 0.998432 |  |  |  | 726 |
| corr_ret_amount_20__raw | volatility_bucket | 2.0 | 0.998299 |  |  |  | 726 |
| corr_ret_amount_20__raw | volatility_bucket | 3.0 | 0.997571 |  |  |  | 726 |
| corr_ret_amount_20__raw | volatility_bucket | 4.0 | 0.997278 |  |  |  | 726 |
| corr_ret_amount_20__raw | volatility_bucket | 5.0 | 0.996696 |  |  |  | 726 |
| corr_ret_amount_20__raw | year_slice | 2021 | 0.987386 |  |  |  | 242 |
| corr_ret_amount_20__raw | year_slice | 2022 | 0.988986 |  |  |  | 242 |
| corr_ret_amount_20__raw | year_slice | 2023 | 0.993907 |  |  |  | 242 |
| downside_std_20__raw | liquidity_bucket | 3.0 | 0.988785 | 0.033862 | 0.222317 | 0.588154 | 726 |
| downside_std_20__raw | liquidity_bucket | 4.0 | 0.989714 | 0.044616 | 0.289670 | 0.623967 | 726 |
| downside_std_20__raw | liquidity_bucket | 5.0 | 0.991809 | 0.066406 | 0.346227 | 0.657025 | 726 |
| downside_std_20__raw | market_state | down | 0.989841 | -0.007936 | -0.043857 | 0.502924 | 171 |
| downside_std_20__raw | market_state | sideways | 0.991273 | 0.082674 | 0.525449 | 0.656126 | 253 |
| downside_std_20__raw | market_state | unknown | 0.988674 | 0.163435 | 2.120601 | 1.000000 | 10 |
| downside_std_20__raw | market_state | up | 0.989246 | 0.089418 | 0.672616 | 0.702055 | 292 |
| downside_std_20__raw | volatility_bucket | 1.0 | 0.998432 | 0.019164 | 0.109681 | 0.549587 | 726 |
| downside_std_20__raw | volatility_bucket | 2.0 | 0.998299 | -0.017790 | -0.143957 | 0.447658 | 726 |
| downside_std_20__raw | volatility_bucket | 3.0 | 0.997571 | -0.034378 | -0.287003 | 0.409091 | 726 |
| downside_std_20__raw | volatility_bucket | 4.0 | 0.997278 | -0.040494 | -0.346017 | 0.378788 | 726 |
| downside_std_20__raw | volatility_bucket | 5.0 | 0.996696 | -0.006122 | -0.048101 | 0.487603 | 726 |
| downside_std_20__raw | year_slice | 2021 | 0.987386 | 0.066245 | 0.460627 | 0.615702 | 242 |
| downside_std_20__raw | year_slice | 2022 | 0.988986 | 0.036064 | 0.259040 | 0.582645 | 242 |
| downside_std_20__raw | year_slice | 2023 | 0.993907 | 0.093161 | 0.504742 | 0.731405 | 242 |
| max_drawdown_20__raw | liquidity_bucket | 3.0 | 0.989237 | 0.022327 | 0.155102 | 0.546832 | 726 |
| max_drawdown_20__raw | liquidity_bucket | 4.0 | 0.990066 | 0.024669 | 0.177230 | 0.573003 | 726 |
| max_drawdown_20__raw | liquidity_bucket | 5.0 | 0.992106 | 0.018095 | 0.112712 | 0.573003 | 726 |
| max_drawdown_20__raw | market_state | down | 0.990146 | -0.051664 | -0.335076 | 0.380117 | 171 |
| max_drawdown_20__raw | market_state | sideways | 0.991538 | 0.044473 | 0.321632 | 0.604743 | 253 |

## Output Files

- `factor_preprocess_summary.csv`
- `factor_neutralized_summary.csv`
- `factor_neutralized_group_return_summary.csv`
- `factor_neutralized_correlation.csv`
- `factor_slice_ic.csv`
- `factor_slice_group_return_summary.csv`
- `factor_exposure_correlation.csv`
- `factor_exposure_report.md`
- `factor_candidate_changelog.csv`
- Detail group-return CSVs are skipped by default. Use `--write-detail` to write them.
