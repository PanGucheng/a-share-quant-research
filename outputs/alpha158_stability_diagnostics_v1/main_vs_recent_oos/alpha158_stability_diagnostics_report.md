# Alpha158 Stability Diagnostics V1

- Main diagnostics: `outputs\alpha158_portfolio_diagnostics_v1\main_2021_2023`
- Recent diagnostics: `outputs\alpha158_portfolio_diagnostics_v1\recent_oos_2024_2026`

## Stability Label Counts

| stability_label | count |
| --- | --- |
| main_only | 2 |
| oos_improved | 1 |
| positive_but_weaker_oos | 3 |
| weak_or_negative_oos | 8 |

## Single Factor Stability

| factor | issue_tags | main_net_excess_ir | main_net_annualized_excess | main_average_turnover | main_net_max_drawdown | main_rank | issue_tags_recent | recent_net_excess_ir | recent_net_annualized_excess | recent_average_turnover | recent_net_max_drawdown | recent_rank | rank_change | net_excess_ir_delta | turnover_delta | stability_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alpha158_VSUMN60 | low_monotonicity | 0.242834 | 0.015205 | 0.855143 | -0.297184 | 10.000000 | low_monotonicity | 0.814553 | 0.064216 | 0.844643 | -0.201931 | 1.000000 | -9.000000 | 0.571719 | -0.010500 | oos_improved |
| alpha158_ROC60 |  | 0.704626 | 0.087829 | 0.661143 | -0.320786 | 2.000000 |  | 0.462744 | 0.052048 | 0.690357 | -0.230331 | 2.000000 | 0.000000 | -0.241882 | 0.029214 | positive_but_weaker_oos |
| alpha158_ROC30 |  | 0.803985 | 0.097575 | 0.810571 | -0.286652 | 1.000000 |  | 0.315209 | 0.031904 | 0.849643 | -0.187536 | 3.000000 | 2.000000 | -0.488777 | 0.039071 | positive_but_weaker_oos |
| alpha158_QTLD60 |  | 0.692407 | 0.079824 | 0.821714 | -0.313843 | 3.000000 |  | 0.144946 | 0.010375 | 0.794286 | -0.162560 | 4.000000 | 1.000000 | -0.547461 | -0.027429 | main_only |
| alpha158_ROC10 | low_monotonicity | 0.278601 | 0.025522 | 0.916286 | -0.346846 | 8.000000 | low_monotonicity | 0.073616 | 0.001253 | 0.925714 | -0.224766 | 5.000000 | -3.000000 | -0.204984 | 0.009429 | positive_but_weaker_oos |
| alpha158_QTLD30 |  | 0.559905 | 0.061348 | 0.912857 | -0.345110 | 4.000000 |  | 0.026421 | -0.004183 | 0.885357 | -0.165602 | 6.000000 | 2.000000 | -0.533484 | -0.027500 | main_only |
| alpha158_IMIN30 |  | 0.405428 | 0.036981 | 0.908857 | -0.303026 | 5.000000 |  | -0.064103 | -0.009503 | 0.897143 | -0.171249 | 7.000000 | 2.000000 | -0.469531 | -0.011714 | weak_or_negative_oos |
| alpha158_QTLD10 | low_monotonicity | 0.366456 | 0.035465 | 0.937429 | -0.362356 | 6.000000 | low_monotonicity | -0.367497 | -0.048051 | 0.924643 | -0.175456 | 8.000000 | 2.000000 | -0.733954 | -0.012786 | weak_or_negative_oos |
| alpha158_IMIN20 |  | 0.360085 | 0.031721 | 0.922571 | -0.308318 | 7.000000 |  | -0.380616 | -0.036785 | 0.911429 | -0.146426 | 9.000000 | 2.000000 | -0.740701 | -0.011143 | weak_or_negative_oos |
| alpha158_IMIN60 |  | 0.133663 | 0.008426 | 0.838571 | -0.309039 | 13.000000 |  | -0.410004 | -0.048852 | 0.796786 | -0.254672 | 10.000000 | -3.000000 | -0.543667 | -0.041786 | weak_or_negative_oos |

## TopK Delta

| topk | net_excess_ir_main | net_annualized_excess_main | average_turnover_main | net_max_drawdown_main | net_excess_ir_recent | net_annualized_excess_recent | average_turnover_recent | net_max_drawdown_recent | net_excess_ir_delta | net_annualized_excess_delta | average_turnover_delta | net_max_drawdown_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | 0.676352 | 0.086389 | 0.889714 | -0.319957 | 0.081597 | 0.001339 | 0.860000 | -0.150571 | -0.594755 | -0.085050 | -0.029714 | 0.169386 |
| 100 | 0.552843 | 0.060632 | 0.824857 | -0.321708 | 0.221295 | 0.019804 | 0.799286 | -0.153772 | -0.331548 | -0.040828 | -0.025571 | 0.167936 |
| 200 | 0.405610 | 0.035902 | 0.715714 | -0.320719 | -0.113919 | -0.016444 | 0.695714 | -0.159904 | -0.519529 | -0.052346 | -0.020000 | 0.160816 |

## Cost Delta

| cost_bps | net_excess_ir_main | net_annualized_excess_main | average_turnover_main | net_max_drawdown_main | net_excess_ir_recent | net_annualized_excess_recent | average_turnover_recent | net_max_drawdown_recent | net_excess_ir_delta | net_annualized_excess_delta | average_turnover_delta | net_max_drawdown_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5.000000 | 0.596277 | 0.066155 | 0.824857 | -0.320601 | 0.262459 | 0.024951 | 0.799286 | -0.151671 | -0.333818 | -0.041203 | -0.025571 | 0.168930 |
| 10.000000 | 0.552843 | 0.060632 | 0.824857 | -0.321708 | 0.221295 | 0.019804 | 0.799286 | -0.153772 | -0.331548 | -0.040828 | -0.025571 | 0.167936 |
| 20.000000 | 0.465720 | 0.049667 | 0.824857 | -0.323920 | 0.138893 | 0.009582 | 0.799286 | -0.157962 | -0.326827 | -0.040085 | -0.025571 | 0.165958 |

## Liquidity Bucket Exposure Delta

| liquidity_bucket | position_share_main | position_share_recent | position_share_delta |
| --- | --- | --- | --- |
| 3.000000 | 0.346286 | 0.409643 | 0.063357 |
| 4.000000 | 0.341714 | 0.336071 | -0.005643 |
| 5.000000 | 0.312000 | 0.254286 | -0.057714 |

## Notes

- Recent OOS is materially weaker than the 2021-2023 main window for the combined candidate portfolio.
- Candidate ranking is not stable enough to move directly into strategy optimization.
- The next stage should diagnose risk exposures and consider lower-turnover score construction.
