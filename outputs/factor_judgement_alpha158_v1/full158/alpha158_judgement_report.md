# Alpha158 Judgement Layer V1

This layer assigns explainable rule labels on top of the existing Alpha158 screening input.
It keeps source evaluator metrics intact and does not create a combined score.

## Rule Snapshot

| min_coverage | max_missing_rate | weak_abs_rank_ic | consistent_abs_rank_ic | strong_abs_rank_ic | consistent_abs_rank_icir | strong_abs_rank_icir | consistent_win_rate | strong_win_rate | min_direction_agreement_ratio | strong_direction_agreement_ratio | high_turnover_top1 | high_turnover_top5 | min_abs_monotonicity | context_flip_tolerance | redundancy_corr_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.990000 | 0.010000 | 0.015000 | 0.030000 | 0.050000 | 0.200000 | 0.350000 | 0.530000 | 0.580000 | 0.670000 | 0.830000 | 0.650000 | 0.800000 | 0.500000 | 0.005000 | 0.900000 |

## Judgement Counts

| judgement_label | count |
| --- | --- |
| consistent_signal | 4 |
| high_turnover | 33 |
| holdout | 3 |
| redundant | 55 |
| review | 33 |
| strong_signal | 10 |
| unstable_context | 16 |
| weak_signal | 4 |

## Signal Counts Before Issue Priority

| signal_label | count |
| --- | --- |
| consistent_signal | 10 |
| holdout | 3 |
| review | 77 |
| strong_signal | 18 |
| weak_signal | 50 |

## Issue Counts

| issue | count |
| --- | --- |
| high_turnover | 48 |
| unstable_context | 43 |
| low_monotonicity | 37 |
| redundant | 55 |

## Redundancy Clusters

| cluster_id | representative_factor | factor_count | factors | selection_policy |
| --- | --- | --- | --- | --- |
| C001 | alpha158_CNTP10 | 3 | alpha158_CNTD10,alpha158_CNTN10,alpha158_CNTP10 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C002 | alpha158_CNTP20 | 3 | alpha158_CNTD20,alpha158_CNTN20,alpha158_CNTP20 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C003 | alpha158_CNTN30 | 3 | alpha158_CNTD30,alpha158_CNTN30,alpha158_CNTP30 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C004 | alpha158_CNTP5 | 2 | alpha158_CNTD5,alpha158_CNTP5 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C005 | alpha158_CNTN60 | 3 | alpha158_CNTD60,alpha158_CNTN60,alpha158_CNTP60 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C006 | alpha158_KMID2 | 3 | alpha158_KMID,alpha158_KMID2,alpha158_OPEN0 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C007 | alpha158_VWAP0 | 2 | alpha158_KSFT,alpha158_VWAP0 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C008 | alpha158_QTLD10 | 3 | alpha158_MA10,alpha158_QTLD10,alpha158_QTLU10 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C009 | alpha158_QTLD30 | 10 | alpha158_MA20,alpha158_MA30,alpha158_QTLD20,alpha158_QTLD30,alpha158_QTLU20,alpha158_QTLU30,alpha158_ROC20,alpha158_SUMD20,alpha158_SUMN20,alpha158_SUMP20 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C010 | alpha158_QTLD5 | 3 | alpha158_MA5,alpha158_QTLD5,alpha158_QTLU5 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C011 | alpha158_QTLD60 | 5 | alpha158_MA60,alpha158_QTLD60,alpha158_QTLU60,alpha158_RANK60,alpha158_RSV60 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C012 | alpha158_MIN30 | 2 | alpha158_MIN20,alpha158_MIN30 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C013 | alpha158_RANK30 | 4 | alpha158_RANK20,alpha158_RANK30,alpha158_RSV20,alpha158_RSV30 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C014 | alpha158_ROC10 | 4 | alpha158_ROC10,alpha158_SUMD10,alpha158_SUMN10,alpha158_SUMP10 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C015 | alpha158_ROC30 | 4 | alpha158_ROC30,alpha158_SUMD30,alpha158_SUMN30,alpha158_SUMP30 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C016 | alpha158_ROC60 | 4 | alpha158_ROC60,alpha158_SUMD60,alpha158_SUMN60,alpha158_SUMP60 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C017 | alpha158_SUMP5 | 3 | alpha158_SUMD5,alpha158_SUMN5,alpha158_SUMP5 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C018 | alpha158_VMA20 | 2 | alpha158_VMA20,alpha158_VMA30 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C019 | alpha158_VSUMN10 | 3 | alpha158_VSUMD10,alpha158_VSUMN10,alpha158_VSUMP10 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C020 | alpha158_VSUMN20 | 3 | alpha158_VSUMD20,alpha158_VSUMN20,alpha158_VSUMP20 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C021 | alpha158_VSUMP30 | 3 | alpha158_VSUMD30,alpha158_VSUMN30,alpha158_VSUMP30 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C022 | alpha158_VSUMD5 | 3 | alpha158_VSUMD5,alpha158_VSUMN5,alpha158_VSUMP5 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |
| C023 | alpha158_VSUMN60 | 3 | alpha158_VSUMD60,alpha158_VSUMN60,alpha158_VSUMP60 | ordered:signal_label,issues,direction_agreement,rank_ic,icir,turnover,coverage |

## Cluster Representatives

| cluster_id | factor | judgement_label | consensus_direction | primary_rank_ic | max_abs_rank_icir | turnover_top1_max | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C008 | alpha158_QTLD10 | consistent_signal | positive | 0.038871 | 0.295639 | 0.440363 | 0.996408 |
| C014 | alpha158_ROC10 | consistent_signal | positive | 0.034488 | 0.258493 | 0.300255 | 0.994550 |
| C023 | alpha158_VSUMN60 | consistent_signal | positive | 0.035648 | 0.294496 | 0.411160 | 0.998805 |
| C001 | alpha158_CNTP10 | high_turnover | negative | -0.019673 | 0.175188 | 0.520977 | 1.000000 |
| C004 | alpha158_CNTP5 | high_turnover | negative | -0.012959 | 0.152885 | 0.953996 | 1.000000 |
| C006 | alpha158_KMID2 | high_turnover | negative | -0.005482 | 0.066755 | 0.837665 | 0.996408 |
| C007 | alpha158_VWAP0 | high_turnover | positive | 0.002391 | 0.019582 | 0.791158 | 0.996408 |
| C010 | alpha158_QTLD5 | high_turnover | positive | 0.027451 | 0.212243 | 0.622131 | 0.996408 |
| C017 | alpha158_SUMP5 | high_turnover | negative | -0.007081 | 0.093426 | 0.446206 | 0.997277 |
| C022 | alpha158_VSUMD5 | high_turnover | positive | 0.005412 | 0.061153 | 0.645728 | 0.997277 |
| C002 | alpha158_CNTP20 | review | negative | -0.035856 | 0.293866 | 0.277018 | 1.000000 |
| C013 | alpha158_RANK30 | review | negative | -0.042637 | 0.299652 | 0.446147 | 0.996408 |
| C021 | alpha158_VSUMP30 | review | negative | -0.019611 | 0.171630 | 0.477262 | 0.998666 |
| C009 | alpha158_QTLD30 | strong_signal | positive | 0.072863 | 0.491997 | 0.272703 | 0.996408 |
| C011 | alpha158_QTLD60 | strong_signal | positive | 0.097826 | 0.592976 | 0.221080 | 0.996408 |
| C012 | alpha158_MIN30 | strong_signal | positive | 0.083258 | 0.535300 | 0.306881 | 0.996408 |
| C015 | alpha158_ROC30 | strong_signal | positive | 0.080597 | 0.506381 | 0.213747 | 0.994231 |
| C016 | alpha158_ROC60 | strong_signal | positive | 0.083509 | 0.506687 | 0.184241 | 0.994271 |
| C003 | alpha158_CNTN30 | unstable_context | positive | 0.031541 | 0.235143 | 0.222365 | 1.000000 |
| C005 | alpha158_CNTN60 | unstable_context | positive | 0.033758 | 0.233239 | 0.175172 | 1.000000 |
| C018 | alpha158_VMA20 | unstable_context | negative | -0.002165 | 0.023893 | 0.454364 | 0.996408 |
| C019 | alpha158_VSUMN10 | unstable_context | negative | -0.004680 | 0.053609 | 0.490822 | 0.997975 |
| C020 | alpha158_VSUMN20 | unstable_context | positive | 0.006124 | 0.078564 | 0.452582 | 0.998453 |

## Signal Candidates

| factor | judgement_label | consensus_direction | primary_rank_ic | max_abs_rank_icir | max_rank_ic_win_rate | issue_tags | cluster_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| alpha158_IMIN20 | consistent_signal | positive | 0.040908 | 0.361384 | 0.625344 |  |  |
| alpha158_QTLD10 | consistent_signal | positive | 0.038871 | 0.295639 | 0.597796 | low_monotonicity | C008 |
| alpha158_ROC10 | consistent_signal | positive | 0.034488 | 0.258493 | 0.581267 | low_monotonicity | C014 |
| alpha158_VSUMN60 | consistent_signal | positive | 0.035648 | 0.294496 | 0.608815 | low_monotonicity | C023 |
| alpha158_MIN60 | strong_signal | positive | 0.099945 | 0.590823 | 0.691460 |  |  |
| alpha158_IMIN60 | strong_signal | positive | 0.068445 | 0.556612 | 0.663912 |  |  |
| alpha158_MIN10 | strong_signal | positive | 0.061041 | 0.446208 | 0.661157 |  |  |
| alpha158_IMIN30 | strong_signal | positive | 0.057858 | 0.456376 | 0.648760 |  |  |
| alpha158_MIN5 | strong_signal | positive | 0.055802 | 0.424455 | 0.655647 | low_monotonicity |  |
| alpha158_QTLD30 | strong_signal | positive | 0.072863 | 0.491997 | 0.665289 |  | C009 |
| alpha158_QTLD60 | strong_signal | positive | 0.097826 | 0.592976 | 0.703857 |  | C011 |
| alpha158_MIN30 | strong_signal | positive | 0.083258 | 0.535300 | 0.658402 |  | C012 |
| alpha158_ROC30 | strong_signal | positive | 0.080597 | 0.506381 | 0.666667 |  | C015 |
| alpha158_ROC60 | strong_signal | positive | 0.083509 | 0.506687 | 0.705234 |  | C016 |

## Holdouts

| factor | holdout_reason | failure_steps |
| --- | --- | --- |
| alpha158_RANK5 | alphalens=partial_pass | factor_alpha_beta,factor_returns,quantile_turnover |
| alpha158_IMAX5 | alphalens=partial_pass | factor_alpha_beta,factor_returns,quantile_turnover |
| alpha158_CNTN5 | alphalens=partial_pass | factor_alpha_beta,factor_returns,quantile_turnover |

## Output Files

- `alpha158_judgement_board.csv`
- `alpha158_redundancy_clusters.csv`
- `alpha158_redundancy_cluster_members.csv`
- `alpha158_judgement_report.md`

## Notes

- `redundant` means the factor is highly correlated with a selected cluster representative under the configured threshold.
- Representatives are selected by ordered criteria, not by a hidden aggregate score.
- `high_turnover` and `unstable_context` are issue-priority labels; the raw signal label is preserved in `signal_label`.
- This output is a research triage board, not a trading signal.
