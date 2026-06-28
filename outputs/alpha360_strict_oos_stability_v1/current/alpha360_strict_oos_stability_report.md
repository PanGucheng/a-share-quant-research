# Alpha360 Strict OOS Stability V1

- Scope: main vs recent OOS metric stability for 3 reviewed Alpha360 probes.
- Boundary: no model training, no strategy optimization, no evaluator definition changes.
- Main metric index: `outputs/factor_evaluation_batch_v1/alpha360_candidate358_execution/alpha360_candidate358_metric_index.csv`
- Recent metric index: `outputs/factor_evaluation_batch_v1/alpha360_strict_oos_recent/runs/batch_001/open_source_metric_index.csv`

## Contract Status

| check_id | status | detail |
| --- | --- | --- |
| strict_oos_contract_passed | pass | failed=0 |
| expected_factor_coverage | pass | factors=3, missing= |
| metric_pair_count | pass | metric_pairs=54 |
| recent_alphalens_mean_ic_positive | pass | min_recent_ic=0.0637364999740596 |
| recent_qlib_information_ratio_positive | pass | min_recent_ir=5.025120855312947 |
| no_signal_sign_flip | pass | signal_sign_flips=0, all_sign_flips=3 |
| no_training_side_effect | pass | stability_audit_only |
| factor_summary_rows | pass | summary_rows=3 |

## Factor Summary

| factor | metric_pairs | sign_flip_count | signal_sign_flip_count | positive_stable_or_improved_count | positive_but_weaker_count | min_recent_alphalens_mean_ic | mean_recent_alphalens_mean_ic | min_recent_qlib_information_ratio | mean_recent_qlib_information_ratio | min_retention_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alpha360_HIGH36 | 18 | 1 | 0 | 10 | 4 | 0.063736 | 0.067984 | 5.025121 | 5.657403 | 0.009696 |
| alpha360_HIGH37 | 18 | 1 | 0 | 10 | 4 | 0.065477 | 0.069275 | 5.153590 | 5.754125 | 0.007603 |
| alpha360_HIGH40 | 18 | 1 | 0 | 10 | 4 | 0.065851 | 0.069083 | 5.157218 | 5.728006 | 0.041135 |

## Label Counts

| stability_label | count |
| --- | --- |
| negative_but_weaker | 3 |
| negative_stable | 6 |
| positive_but_weaker | 12 |
| positive_stable_or_improved | 30 |
| sign_flip | 3 |

## Key Metrics

| factor | system | metric | horizon | main_value | recent_value | delta | retention_ratio | stability_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| alpha360_HIGH36 | alphalens_reloaded | mean_information_coefficient | 10D | 0.067448 | 0.063736 | -0.003711 | 0.944977 | positive_stable_or_improved |
| alpha360_HIGH36 | alphalens_reloaded | mean_information_coefficient | 20D | 0.077548 | 0.072231 | -0.005317 | 0.931441 | positive_stable_or_improved |
| alpha360_HIGH37 | alphalens_reloaded | mean_information_coefficient | 10D | 0.068568 | 0.065477 | -0.003091 | 0.954925 | positive_stable_or_improved |
| alpha360_HIGH37 | alphalens_reloaded | mean_information_coefficient | 20D | 0.078303 | 0.073073 | -0.005230 | 0.933205 | positive_stable_or_improved |
| alpha360_HIGH40 | alphalens_reloaded | mean_information_coefficient | 10D | 0.073413 | 0.065851 | -0.007562 | 0.896994 | positive_stable_or_improved |
| alpha360_HIGH40 | alphalens_reloaded | mean_information_coefficient | 20D | 0.082376 | 0.072314 | -0.010062 | 0.877854 | positive_stable_or_improved |
| alpha360_HIGH36 | qlib_eval | information_ratio | label_10d_t1 | 6.641171 | 5.025121 | -1.616050 | 0.756662 | positive_but_weaker |
| alpha360_HIGH36 | qlib_eval | information_ratio | label_20d_t1 | 8.640702 | 6.289686 | -2.351016 | 0.727914 | positive_but_weaker |
| alpha360_HIGH37 | qlib_eval | information_ratio | label_10d_t1 | 6.696397 | 5.153590 | -1.542807 | 0.769606 | positive_but_weaker |
| alpha360_HIGH37 | qlib_eval | information_ratio | label_20d_t1 | 8.592490 | 6.354661 | -2.237829 | 0.739560 | positive_but_weaker |
| alpha360_HIGH40 | qlib_eval | information_ratio | label_10d_t1 | 6.970457 | 5.157218 | -1.813238 | 0.739868 | positive_but_weaker |
| alpha360_HIGH40 | qlib_eval | information_ratio | label_20d_t1 | 8.588899 | 6.298794 | -2.290105 | 0.733365 | positive_but_weaker |

## Notes

- Positive recent-OOS stability is still a diagnostic, not training admission.
- Highly redundant Alpha360 high-window factors should remain represented by a small number of candidates.
