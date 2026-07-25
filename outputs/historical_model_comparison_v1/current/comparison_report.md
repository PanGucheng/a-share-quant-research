# Historical Model Comparison V1

- Historical research leader: `lightgbm`.
- Evidence class: `post_observation_research`.
- Five-method prediction comparison: complete.
- Five-method portfolio/NAV comparison: `blocked_execution_capability`.
- Blocker: `SZ300280` unpriceable held position on 2025-04-18.
- Production model selected: false.
- Authoritative execution: false.
- Unbiased final estimate: false.

## Equal-split summary

| method           |   equal_split_mean_daily_rank_ic |   equal_split_mean_daily_rank_ic_ir |   pooled_daily_mean_rank_ic |   pooled_positive_ic_day_ratio |   worst_split_mean_daily_rank_ic |   mean_split_rank |   split_rank_std |   minimum_split_prediction_coverage |   method_complexity |
|:-----------------|---------------------------------:|------------------------------------:|----------------------------:|-------------------------------:|---------------------------------:|------------------:|-----------------:|------------------------------------:|--------------------:|
| lightgbm         |                        0.090936  |                            0.513995 |                   0.0910789 |                       0.671196 |                        0.0518016 |           2.66667 |         1.69967  |                            0.995305 |                   5 |
| elastic_net      |                        0.0868875 |                            0.525591 |                   0.0869119 |                       0.665761 |                        0.057729  |           2.33333 |         0.942809 |                            0.995305 |                   4 |
| ridge            |                        0.0864699 |                            0.510043 |                   0.0865884 |                       0.668478 |                        0.0576444 |           3       |         0.816497 |                            0.995305 |                   3 |
| equal_weight     |                        0.0736777 |                            0.514804 |                   0.0738776 |                       0.6875   |                        0.0552936 |           3.33333 |         0.942809 |                            0.995305 |                   1 |
| stability_weight |                        0.0727596 |                            0.510242 |                   0.0729736 |                       0.690217 |                        0.0530721 |           3.66667 |         1.88562  |                            0.995305 |                   2 |
