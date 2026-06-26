# Alpha158 Portfolio Diagnostics V1

- Base smoke output: `outputs\alpha158_candidate_portfolio_smoke_v1\recent_oos_2024_2026`
- Candidate pool: `outputs\factor_candidate_pool_alpha158_v1\full158\alpha158_alpha_candidates.csv`
- Date range: `2024-01-01` to `2026-06-09`
- Base TopK: `100`
- Base cost bps: `10.0`

## Base Summary

| scenario | scenario_type | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined_base | base | 100 | 10.000000 | 14 | 560 | 28 | 0.019804 | 0.221295 | 0.799286 | -0.153772 | 1071.285714 | 100.000000 |

## Single Factor Summary

| scenario | scenario_type | factor | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alpha158_VSUMN60 | single_factor | alpha158_VSUMN60 | 100 | 10.000000 | 1 | 560 | 28 | 0.064216 | 0.814553 | 0.844643 | -0.201931 | 1071.285714 | 100.000000 |
| alpha158_ROC60 | single_factor | alpha158_ROC60 | 100 | 10.000000 | 1 | 560 | 28 | 0.052048 | 0.462744 | 0.690357 | -0.230331 | 1069.678571 | 100.000000 |
| alpha158_ROC30 | single_factor | alpha158_ROC30 | 100 | 10.000000 | 1 | 560 | 28 | 0.031904 | 0.315209 | 0.849643 | -0.187536 | 1069.750000 | 100.000000 |
| alpha158_QTLD60 | single_factor | alpha158_QTLD60 | 100 | 10.000000 | 1 | 560 | 28 | 0.010375 | 0.144946 | 0.794286 | -0.162560 | 1071.285714 | 100.000000 |
| alpha158_ROC10 | single_factor | alpha158_ROC10 | 100 | 10.000000 | 1 | 560 | 28 | 0.001253 | 0.073616 | 0.925714 | -0.224766 | 1069.714286 | 100.000000 |
| alpha158_QTLD30 | single_factor | alpha158_QTLD30 | 100 | 10.000000 | 1 | 560 | 28 | -0.004183 | 0.026421 | 0.885357 | -0.165602 | 1071.285714 | 100.000000 |
| alpha158_IMIN30 | single_factor | alpha158_IMIN30 | 100 | 10.000000 | 1 | 560 | 28 | -0.009503 | -0.064103 | 0.897143 | -0.171249 | 1071.285714 | 100.000000 |
| alpha158_QTLD10 | single_factor | alpha158_QTLD10 | 100 | 10.000000 | 1 | 560 | 28 | -0.048051 | -0.367497 | 0.924643 | -0.175456 | 1071.285714 | 100.000000 |
| alpha158_IMIN20 | single_factor | alpha158_IMIN20 | 100 | 10.000000 | 1 | 560 | 28 | -0.036785 | -0.380616 | 0.911429 | -0.146426 | 1071.285714 | 100.000000 |
| alpha158_IMIN60 | single_factor | alpha158_IMIN60 | 100 | 10.000000 | 1 | 560 | 28 | -0.048852 | -0.410004 | 0.796786 | -0.254672 | 1071.285714 | 100.000000 |
| alpha158_MIN30 | single_factor | alpha158_MIN30 | 100 | 10.000000 | 1 | 560 | 28 | -0.081157 | -0.623538 | 0.817143 | -0.130768 | 1071.285714 | 100.000000 |
| alpha158_MIN60 | single_factor | alpha158_MIN60 | 100 | 10.000000 | 1 | 560 | 28 | -0.089477 | -0.641784 | 0.708214 | -0.141471 | 1071.285714 | 100.000000 |
| alpha158_MIN10 | single_factor | alpha158_MIN10 | 100 | 10.000000 | 1 | 560 | 28 | -0.079689 | -0.680742 | 0.874643 | -0.147462 | 1071.285714 | 100.000000 |
| alpha158_MIN5 | single_factor | alpha158_MIN5 | 100 | 10.000000 | 1 | 560 | 28 | -0.092607 | -0.840351 | 0.873214 | -0.153942 | 1071.285714 | 100.000000 |

## TopK Sensitivity

| scenario | scenario_type | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| topk_50 | topk_sensitivity | 50 | 10.000000 | 14 | 560 | 28 | 0.001339 | 0.081597 | 0.860000 | -0.150571 | 1071.285714 | 50.000000 |
| topk_100 | topk_sensitivity | 100 | 10.000000 | 14 | 560 | 28 | 0.019804 | 0.221295 | 0.799286 | -0.153772 | 1071.285714 | 100.000000 |
| topk_200 | topk_sensitivity | 200 | 10.000000 | 14 | 560 | 28 | -0.016444 | -0.113919 | 0.695714 | -0.159904 | 1071.285714 | 200.000000 |

## Cost Sensitivity

| scenario | scenario_type | topk | cost_bps | candidate_count | trading_days | executed_rebalances | net_annualized_excess | net_excess_ir | average_turnover | net_max_drawdown | average_eligible_count | average_selected_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cost_5bps | cost_sensitivity | 100 | 5.000000 | 14 | 560 | 28 | 0.024951 | 0.262459 | 0.799286 | -0.151671 | 1071.285714 | 100.000000 |
| cost_10bps | cost_sensitivity | 100 | 10.000000 | 14 | 560 | 28 | 0.019804 | 0.221295 | 0.799286 | -0.153772 | 1071.285714 | 100.000000 |
| cost_20bps | cost_sensitivity | 100 | 20.000000 | 14 | 560 | 28 | 0.009582 | 0.138893 | 0.799286 | -0.157962 | 1071.285714 | 100.000000 |

## Liquidity Bucket Exposure

| liquidity_bucket | position_count | position_share |
| --- | --- | --- |
| 3.000000 | 1147 | 0.409643 |
| 4.000000 | 941 | 0.336071 |
| 5.000000 | 712 | 0.254286 |

## Notes

- This diagnostic layer does not change candidate selection or optimize parameters.
- High turnover remains the main portfolio-level risk to address before strategy work.
- Recent OOS diagnostics require extending the Alpha158 expression frame beyond 2024-02-29.
