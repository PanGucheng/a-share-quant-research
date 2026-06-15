# Factor Exposure Report

This report explains whether a factor's apparent signal is mostly standalone residual signal or exposure to liquidity, volatility, and amount proxies.

## Interpretation

| base_factor | expected_direction | raw_directional_rank_ic | directional_rank_icir | joint_residual_directional_rank_ic | joint_residual_delta | dominant_exposure | dominant_exposure_corr | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | negative | 0.109863 | 0.594628 | 0.004954 | -0.104909 | volatility_bucket | 0.979796 | exposure_dominated |
| std_20 | negative | 0.094345 | 0.563278 | -0.005890 | -0.100235 | amplitude_20 | 0.903193 | exposure_dominated |
| downside_std_20 | negative | 0.065157 | 0.410552 | -0.026763 | -0.091920 | std_20 | 0.816805 | exposure_dominated |
| rev_20_exclude_5 | positive | 0.053765 | 0.397930 | 0.009602 | -0.044163 | std_20 | -0.254198 | watch_after_controls |
| max_drawdown_20 | negative | 0.030714 | 0.221064 | -0.034758 | -0.065472 | std_20 | 0.559589 | watch_after_controls |
| amount_cv_20 | negative | 0.019981 | 0.203076 | 0.005720 | -0.014261 | std_20 | 0.389458 | watch |
| rev_5 | positive | 0.019598 | 0.147822 | 0.018371 | -0.001227 | log_amount_mean_20 | 0.148324 | watch |
| ret_20 | watch |  |  |  |  | std_20 | 0.242217 | watch |
| amount_mean_20 | watch |  |  |  |  | log_amount_mean_20 | 1.000000 | watch |
| corr_ret_amount_20 | watch |  |  |  |  | amplitude_20 | 0.010527 | watch |

## Strongest Exposure Correlations

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
| main_research_2021_2023 | std_20 | log_amount_mean_20 | 0.353378 | 0.353378 | 726 |
| main_research_2021_2023 | amount_mean_20 | std_20 | 0.353378 | 0.353378 | 726 |
| recent_oos_2024_2026 | amount_cv_20 | volatility_bucket | 0.336256 | 0.348904 | 586 |
| recent_oos_2024_2026 | rev_20_exclude_5 | std_20 | -0.262099 | 0.343784 | 586 |
| recent_oos_2024_2026 | ret_20 | std_20 | 0.258964 | 0.339843 | 586 |
| main_research_2021_2023 | downside_std_20 | log_amount_mean_20 | 0.339001 | 0.339799 | 726 |
| recent_oos_2024_2026 | rev_20_exclude_5 | amplitude_20 | -0.258367 | 0.337937 | 586 |
| recent_oos_2024_2026 | ret_20 | amplitude_20 | 0.245112 | 0.328870 | 586 |
| recent_oos_2024_2026 | rev_20_exclude_5 | volatility_bucket | -0.248944 | 0.328502 | 586 |
| recent_oos_2024_2026 | ret_20 | volatility_bucket | 0.236280 | 0.319772 | 586 |

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
| rev_5 | cs_rank | 0.019598 | 0.019598 | 0.000000 | similar |
| rev_5 | cs_zscore | 0.019598 | 0.019542 | -0.000056 | similar |
| rev_5 | liquidity_volatility_residual | 0.019598 | 0.018371 | -0.001227 | similar |
| rev_5 | liquidity_bucket_zscore | 0.019598 | 0.009001 | -0.010597 | weakened |
| std_20 | cs_rank | 0.094345 | 0.094345 | 0.000000 | similar |
| std_20 | cs_zscore | 0.094345 | 0.094313 | -0.000032 | similar |
| std_20 | liquidity_bucket_zscore | 0.094345 | 0.068754 | -0.025591 | weakened |
| std_20 | amount_proxy_residual | 0.094345 | 0.061777 | -0.032568 | weakened |
| std_20 | volatility_bucket_zscore | 0.094345 | 0.011942 | -0.082403 | weakened |
| std_20 | liquidity_volatility_residual | 0.094345 | -0.005890 | -0.100235 | weakened |
