# Factor Candidate Pool

This file summarizes the current factor candidates produced by factor research V2.

## Decision Counts

| run_name | label | decision | count |
| --- | --- | --- | --- |
| liquid2000_default | label_10d_t1 | promote | 1 |
| liquid2000_default | label_10d_t1 | reject | 1 |
| liquid2000_default | label_10d_t1 | watch | 8 |
| liquid2000_default | label_20d_t1 | promote | 1 |
| liquid2000_default | label_20d_t1 | reject | 1 |
| liquid2000_default | label_20d_t1 | watch | 8 |

## Promote

| run_name | label | factor | category | expected_direction | main_directional_rank_ic | main_ic_win_rate | oos_directional_rank_ic | mean_top_quantile_turnover | stability_score | monotonicity_score | directional_spread | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| liquid2000_default | label_10d_t1 | amplitude_20 | risk | negative | 0.087936 | 0.668044 | 0.068054 | 0.111795 | 1.000000 | 0.800000 | 0.006657 | passes_rules |
| liquid2000_default | label_20d_t1 | amplitude_20 | risk | negative | 0.109863 | 0.680441 | 0.075408 | 0.111795 | 1.000000 | 1.000000 | 0.013217 | passes_rules |

## Watch

| run_name | label | factor | category | expected_direction | main_directional_rank_ic | main_ic_win_rate | oos_directional_rank_ic | mean_top_quantile_turnover | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| liquid2000_default | label_10d_t1 | rev_5 | reversal | positive | 0.025876 | 0.546832 | 0.034651 | 0.391654 | insufficient_evidence |
| liquid2000_default | label_10d_t1 | ret_5 | momentum | watch |  |  |  | 0.398787 | watch_direction |
| liquid2000_default | label_10d_t1 | ret_10 | momentum | watch |  |  |  | 0.302616 | watch_direction |
| liquid2000_default | label_10d_t1 | ret_20 | momentum | watch |  |  |  | 0.235884 | watch_direction |
| liquid2000_default | label_10d_t1 | amount_mean_20 | liquidity | watch |  |  |  | 0.042955 | watch_direction |
| liquid2000_default | label_10d_t1 | amount_std_20 | liquidity | watch |  |  |  | 0.065733 | watch_direction |
| liquid2000_default | label_10d_t1 | volume_ratio_5_20 | liquidity | watch |  |  |  | 0.265482 | watch_direction |
| liquid2000_default | label_10d_t1 | corr_ret_volume_20 | price_volume | watch |  |  |  | 0.237294 | watch_direction |
| liquid2000_default | label_20d_t1 | rev_5 | reversal | positive | 0.019598 | 0.550964 | 0.035178 | 0.391654 | insufficient_evidence |
| liquid2000_default | label_20d_t1 | ret_5 | momentum | watch |  |  |  | 0.398787 | watch_direction |
| liquid2000_default | label_20d_t1 | ret_10 | momentum | watch |  |  |  | 0.302616 | watch_direction |
| liquid2000_default | label_20d_t1 | ret_20 | momentum | watch |  |  |  | 0.235884 | watch_direction |
| liquid2000_default | label_20d_t1 | amount_mean_20 | liquidity | watch |  |  |  | 0.042955 | watch_direction |
| liquid2000_default | label_20d_t1 | amount_std_20 | liquidity | watch |  |  |  | 0.065733 | watch_direction |
| liquid2000_default | label_20d_t1 | volume_ratio_5_20 | liquidity | watch |  |  |  | 0.265482 | watch_direction |
| liquid2000_default | label_20d_t1 | corr_ret_volume_20 | price_volume | watch |  |  |  | 0.237294 | watch_direction |

## Reject

| run_name | label | factor | category | expected_direction | main_directional_rank_ic | main_ic_win_rate | oos_directional_rank_ic | mean_top_quantile_turnover | reason | redundancy_group |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| liquid2000_default | label_10d_t1 | std_20 | risk | negative | 0.078755 | 0.684573 | 0.063243 | 0.131880 | passes_rules|redundant_weak | amplitude_20 |
| liquid2000_default | label_20d_t1 | std_20 | risk | negative | 0.094345 | 0.687328 | 0.068258 | 0.131880 | passes_rules|redundant_weak | amplitude_20 |

## How To Use

- Treat `promote` as a research-pool signal, not a live-trading signal.
- Add new candidate factors to the registry and rerun V2 before touching model or portfolio logic.
- Use `watch` rows to decide whether a factor needs a direction hypothesis, neutralization, or decomposition.
