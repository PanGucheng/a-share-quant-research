# Alpha158 Portfolio Diagnostics V1

- Base smoke output: `outputs\alpha158_candidate_portfolio_smoke_v1\main_2021_2023`
- Candidate pool: `outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv`
- Date range: `2021-01-01` to `2023-12-29`
- Base TopK: `100`
- Base cost bps: `10.0`

## Base Summary

| scenario | scenario_type | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined_base | base | 100 | 10.000000 | 14 | 700 | 35 | 0.060632 | 0.552843 | 0.824857 | -0.321708 | 1131.942857 | 100.000000 |

## Single Factor Summary

| scenario | scenario_type | factor | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alpha158_ROC30 | single_factor | alpha158_ROC30 | 100 | 10.000000 | 1 | 700 | 35 | 0.097575 | 0.803985 | 0.810571 | -0.286652 | 1129.971429 | 100.000000 |
| alpha158_ROC60 | single_factor | alpha158_ROC60 | 100 | 10.000000 | 1 | 700 | 35 | 0.087829 | 0.704626 | 0.661143 | -0.320786 | 1129.828571 | 100.000000 |
| alpha158_QTLD60 | single_factor | alpha158_QTLD60 | 100 | 10.000000 | 1 | 700 | 35 | 0.079824 | 0.692407 | 0.821714 | -0.313843 | 1131.942857 | 100.000000 |
| alpha158_QTLD30 | single_factor | alpha158_QTLD30 | 100 | 10.000000 | 1 | 700 | 35 | 0.061348 | 0.559905 | 0.912857 | -0.345110 | 1131.942857 | 100.000000 |
| alpha158_IMIN30 | single_factor | alpha158_IMIN30 | 100 | 10.000000 | 1 | 700 | 35 | 0.036981 | 0.405428 | 0.908857 | -0.303026 | 1131.942857 | 100.000000 |
| alpha158_QTLD10 | single_factor | alpha158_QTLD10 | 100 | 10.000000 | 1 | 700 | 35 | 0.035465 | 0.366456 | 0.937429 | -0.362356 | 1131.942857 | 100.000000 |
| alpha158_IMIN20 | single_factor | alpha158_IMIN20 | 100 | 10.000000 | 1 | 700 | 35 | 0.031721 | 0.360085 | 0.922571 | -0.308318 | 1131.942857 | 100.000000 |
| alpha158_ROC10 | single_factor | alpha158_ROC10 | 100 | 10.000000 | 1 | 700 | 35 | 0.025522 | 0.278601 | 0.916286 | -0.346846 | 1130.257143 | 100.000000 |
| alpha158_MIN30 | single_factor | alpha158_MIN30 | 100 | 10.000000 | 1 | 700 | 35 | 0.023221 | 0.265696 | 0.877714 | -0.328784 | 1131.942857 | 100.000000 |
| alpha158_VSUMN60 | single_factor | alpha158_VSUMN60 | 100 | 10.000000 | 1 | 700 | 35 | 0.015205 | 0.242834 | 0.855143 | -0.297184 | 1131.942857 | 100.000000 |
| alpha158_MIN60 | single_factor | alpha158_MIN60 | 100 | 10.000000 | 1 | 700 | 35 | 0.018146 | 0.219098 | 0.799429 | -0.307751 | 1131.942857 | 100.000000 |
| alpha158_MIN10 | single_factor | alpha158_MIN10 | 100 | 10.000000 | 1 | 700 | 35 | 0.010684 | 0.157793 | 0.903714 | -0.353978 | 1131.942857 | 100.000000 |
| alpha158_IMIN60 | single_factor | alpha158_IMIN60 | 100 | 10.000000 | 1 | 700 | 35 | 0.008426 | 0.133663 | 0.838571 | -0.309039 | 1131.942857 | 100.000000 |
| alpha158_MIN5 | single_factor | alpha158_MIN5 | 100 | 10.000000 | 1 | 700 | 35 | -0.004522 | -0.004575 | 0.902286 | -0.344627 | 1131.942857 | 100.000000 |

## TopK Sensitivity

| scenario | scenario_type | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| topk_50 | topk_sensitivity | 50 | 10.000000 | 14 | 700 | 35 | 0.086389 | 0.676352 | 0.889714 | -0.319957 | 1131.942857 | 50.000000 |
| topk_100 | topk_sensitivity | 100 | 10.000000 | 14 | 700 | 35 | 0.060632 | 0.552843 | 0.824857 | -0.321708 | 1131.942857 | 100.000000 |
| topk_200 | topk_sensitivity | 200 | 10.000000 | 14 | 700 | 35 | 0.035902 | 0.405610 | 0.715714 | -0.320719 | 1131.942857 | 200.000000 |

## Cost Sensitivity

| scenario | scenario_type | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cost_5bps | cost_sensitivity | 100 | 5.000000 | 14 | 700 | 35 | 0.066155 | 0.596277 | 0.824857 | -0.320601 | 1131.942857 | 100.000000 |
| cost_10bps | cost_sensitivity | 100 | 10.000000 | 14 | 700 | 35 | 0.060632 | 0.552843 | 0.824857 | -0.321708 | 1131.942857 | 100.000000 |
| cost_20bps | cost_sensitivity | 100 | 20.000000 | 14 | 700 | 35 | 0.049667 | 0.465720 | 0.824857 | -0.323920 | 1131.942857 | 100.000000 |

## Liquidity Bucket Exposure

| liquidity_bucket | position_count | position_share |
| --- | --- | --- |
| 3.000000 | 1212 | 0.346286 |
| 4.000000 | 1196 | 0.341714 |
| 5.000000 | 1092 | 0.312000 |

## Notes

- This diagnostic layer does not change candidate selection or optimize parameters.
- High turnover remains the main portfolio-level risk to address before strategy work.
- Recent OOS diagnostics require extending the Alpha158 expression frame beyond 2024-02-29.
