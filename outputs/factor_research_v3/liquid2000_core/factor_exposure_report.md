# Factor Exposure Report

This report explains whether a factor's apparent signal is mostly standalone residual signal or exposure to liquidity, volatility, and amount proxies.

## Interpretation

| base_factor | expected_direction | raw_directional_rank_ic | directional_rank_icir | joint_residual_directional_rank_ic | joint_residual_delta | dominant_exposure | dominant_exposure_corr | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| amplitude_20 | negative | 0.109863 | 0.594628 | 0.004954 | -0.104909 | volatility_bucket | 0.979796 | exposure_dominated |
| std_20 | negative | 0.094345 | 0.563278 | -0.005890 | -0.100235 | amplitude_20 | 0.903193 | exposure_dominated |
| rev_5 | positive | 0.019598 | 0.147822 | 0.018371 | -0.001227 | log_amount_mean_20 | 0.148324 | watch |
| ret_20 | watch |  |  |  |  | std_20 | 0.242217 | watch |
| amount_mean_20 | watch |  |  |  |  | log_amount_mean_20 | 1.000000 | watch |

## Strongest Exposure Correlations

| window | factor | exposure | mean_spearman_corr | abs_mean_spearman_corr | corr_dates |
| --- | --- | --- | --- | --- | --- |
| recent_oos_2024_2026 | amount_mean_20 | log_amount_mean_20 | 1.000000 | 1.000000 | 586 |
| main_research_2021_2023 | amount_mean_20 | log_amount_mean_20 | 1.000000 | 1.000000 | 726 |
| recent_oos_2024_2026 | amplitude_20 | volatility_bucket | 0.979796 | 0.979796 | 586 |
| main_research_2021_2023 | amplitude_20 | volatility_bucket | 0.979796 | 0.979796 | 726 |
| recent_oos_2024_2026 | std_20 | amplitude_20 | 0.920875 | 0.920875 | 586 |
| recent_oos_2024_2026 | amplitude_20 | std_20 | 0.920875 | 0.920875 | 586 |
| main_research_2021_2023 | std_20 | amplitude_20 | 0.903193 | 0.903193 | 726 |
| main_research_2021_2023 | amplitude_20 | std_20 | 0.903193 | 0.903193 | 726 |
| recent_oos_2024_2026 | std_20 | volatility_bucket | 0.900407 | 0.900407 | 586 |
| main_research_2021_2023 | std_20 | volatility_bucket | 0.881807 | 0.881807 | 726 |
| main_research_2021_2023 | amount_mean_20 | liquidity_bucket | 0.781756 | 0.781756 | 726 |
| recent_oos_2024_2026 | amount_mean_20 | liquidity_bucket | 0.776431 | 0.776431 | 586 |
| main_research_2021_2023 | amount_mean_20 | amplitude_20 | 0.364897 | 0.364897 | 726 |
| main_research_2021_2023 | amplitude_20 | log_amount_mean_20 | 0.364897 | 0.364897 | 726 |
| main_research_2021_2023 | amount_mean_20 | volatility_bucket | 0.355577 | 0.355577 | 726 |
| main_research_2021_2023 | amount_mean_20 | std_20 | 0.353378 | 0.353378 | 726 |
| main_research_2021_2023 | std_20 | log_amount_mean_20 | 0.353378 | 0.353378 | 726 |
| recent_oos_2024_2026 | ret_20 | std_20 | 0.258964 | 0.339843 | 586 |
| recent_oos_2024_2026 | ret_20 | amplitude_20 | 0.245112 | 0.328870 | 586 |
| recent_oos_2024_2026 | ret_20 | volatility_bucket | 0.236280 | 0.319772 | 586 |
| main_research_2021_2023 | std_20 | liquidity_bucket | 0.284761 | 0.284761 | 726 |
| main_research_2021_2023 | amplitude_20 | liquidity_bucket | 0.276948 | 0.276948 | 726 |
| recent_oos_2024_2026 | std_20 | log_amount_mean_20 | 0.252261 | 0.274794 | 586 |
| recent_oos_2024_2026 | amount_mean_20 | std_20 | 0.252261 | 0.274794 | 586 |
| recent_oos_2024_2026 | amount_mean_20 | amplitude_20 | 0.252454 | 0.270114 | 586 |
| recent_oos_2024_2026 | amplitude_20 | log_amount_mean_20 | 0.252454 | 0.270114 | 586 |
| recent_oos_2024_2026 | amount_mean_20 | volatility_bucket | 0.246405 | 0.263401 | 586 |
| main_research_2021_2023 | ret_20 | std_20 | 0.242217 | 0.253061 | 726 |
| main_research_2021_2023 | ret_20 | amplitude_20 | 0.217955 | 0.239026 | 726 |
| main_research_2021_2023 | ret_20 | volatility_bucket | 0.210940 | 0.231931 | 726 |
| recent_oos_2024_2026 | ret_20 | liquidity_bucket | 0.219525 | 0.221959 | 586 |
| recent_oos_2024_2026 | std_20 | liquidity_bucket | 0.194578 | 0.213886 | 586 |
| recent_oos_2024_2026 | amplitude_20 | liquidity_bucket | 0.182673 | 0.197866 | 586 |
| recent_oos_2024_2026 | rev_5 | std_20 | -0.006746 | 0.196161 | 586 |
| recent_oos_2024_2026 | rev_5 | amplitude_20 | 0.003706 | 0.189216 | 586 |
| recent_oos_2024_2026 | rev_5 | volatility_bucket | 0.002738 | 0.185381 | 586 |
| main_research_2021_2023 | ret_20 | liquidity_bucket | 0.169189 | 0.176208 | 726 |
| main_research_2021_2023 | rev_5 | log_amount_mean_20 | 0.148324 | 0.171332 | 726 |
| recent_oos_2024_2026 | rev_5 | log_amount_mean_20 | 0.129265 | 0.162878 | 586 |
| recent_oos_2024_2026 | rev_5 | liquidity_bucket | -0.144496 | 0.157046 | 586 |

## Neutralization Change Log

| base_factor | neutralization | raw_directional_rank_ic | directional_mean_rank_ic | delta_directional_rank_ic | effect |
| --- | --- | --- | --- | --- | --- |
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
| ret_20 | cs_rank |  |  |  | similar |
| ret_20 | cs_zscore |  |  |  | similar |
| ret_20 | liquidity_bucket_zscore |  |  |  | similar |
| ret_20 | volatility_bucket_zscore |  |  |  | similar |
| ret_20 | amount_proxy_residual |  |  |  | similar |
| ret_20 | liquidity_volatility_residual |  |  |  | similar |
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
