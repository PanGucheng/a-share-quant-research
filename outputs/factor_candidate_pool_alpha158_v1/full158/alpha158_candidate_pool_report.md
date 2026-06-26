# Alpha158 Candidate Pool V1

- Pool name: `alpha158_full_v1`
- Source judgement board: `outputs\factor_judgement_alpha158_v1\full158\alpha158_judgement_board.csv`
- Source redundancy clusters: `outputs\factor_judgement_alpha158_v1\full158\alpha158_redundancy_clusters.csv`

## Role Counts

| role | count |
| --- | --- |
| alpha_candidate | 14 |
| excluded_high_turnover | 33 |
| excluded_redundant | 55 |
| excluded_unstable_context | 16 |
| holdout | 3 |
| monitor | 37 |

## Alpha Candidate Signal Counts

| judgement_label | consensus_direction | count |
| --- | --- | --- |
| consistent_signal | positive | 4 |
| strong_signal | positive | 10 |

## Alpha Candidates

| factor | judgement_label | consensus_direction | primary_rank_ic | max_abs_rank_icir | max_rank_ic_win_rate | cluster_id | issue_tags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| alpha158_MIN60 | strong_signal | positive | 0.099945 | 0.590823 | 0.691460 |  |  |
| alpha158_QTLD60 | strong_signal | positive | 0.097826 | 0.592976 | 0.703857 | C011 |  |
| alpha158_ROC60 | strong_signal | positive | 0.083509 | 0.506687 | 0.705234 | C016 |  |
| alpha158_MIN30 | strong_signal | positive | 0.083258 | 0.535300 | 0.658402 | C012 |  |
| alpha158_ROC30 | strong_signal | positive | 0.080597 | 0.506381 | 0.666667 | C015 |  |
| alpha158_QTLD30 | strong_signal | positive | 0.072863 | 0.491997 | 0.665289 | C009 |  |
| alpha158_IMIN60 | strong_signal | positive | 0.068445 | 0.556612 | 0.663912 |  |  |
| alpha158_MIN10 | strong_signal | positive | 0.061041 | 0.446208 | 0.661157 |  |  |
| alpha158_IMIN30 | strong_signal | positive | 0.057858 | 0.456376 | 0.648760 |  |  |
| alpha158_MIN5 | strong_signal | positive | 0.055802 | 0.424455 | 0.655647 |  | low_monotonicity |
| alpha158_IMIN20 | consistent_signal | positive | 0.040908 | 0.361384 | 0.625344 |  |  |
| alpha158_QTLD10 | consistent_signal | positive | 0.038871 | 0.295639 | 0.597796 | C008 | low_monotonicity |
| alpha158_VSUMN60 | consistent_signal | positive | 0.035648 | 0.294496 | 0.608815 | C023 | low_monotonicity |
| alpha158_ROC10 | consistent_signal | positive | 0.034488 | 0.258493 | 0.581267 | C014 | low_monotonicity |

## Alpha Candidates From Clusters

| factor | cluster_id | cluster_representative | is_cluster_representative |
| --- | --- | --- | --- |
| alpha158_QTLD60 | C011 | alpha158_QTLD60 | True |
| alpha158_ROC60 | C016 | alpha158_ROC60 | True |
| alpha158_MIN30 | C012 | alpha158_MIN30 | True |
| alpha158_ROC30 | C015 | alpha158_ROC30 | True |
| alpha158_QTLD30 | C009 | alpha158_QTLD30 | True |
| alpha158_QTLD10 | C008 | alpha158_QTLD10 | True |
| alpha158_VSUMN60 | C023 | alpha158_VSUMN60 | True |
| alpha158_ROC10 | C014 | alpha158_ROC10 | True |

## Excluded Or Monitor Summary

| role | pool_reason | count |
| --- | --- | --- |
| excluded_high_turnover | high_turnover_issue | 33 |
| excluded_redundant | non_representative_redundant_factor | 55 |
| excluded_unstable_context | context_instability_issue | 16 |
| holdout | evaluation_holdout | 3 |
| monitor | review_or_marginal_signal | 33 |
| monitor | weak_signal_monitor | 4 |

## Redundancy Cluster Snapshot

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

## Cluster Member Count

- Cluster rows: `23`
- Cluster member rows: `78`

## Output Files

- `alpha158_candidate_pool.csv`
- `alpha158_alpha_candidates.csv`
- `alpha158_candidate_pool.json`
- `alpha158_candidate_pool_report.md`

## Notes

- The candidate pool is a research interface, not a trading signal.
- `alpha_candidate` is intentionally conservative in V1.
- Low monotonicity is preserved as a warning in `issue_tags` and does not remove a factor in V1.
- Non-representative redundant factors are excluded from alpha candidates.
