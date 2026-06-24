# Alpha158 First20 Evaluation Summary

- Output: `E:/qlib_prj/qlib_baseline/outputs/factor_evaluation_v4/alpha158_first20_smoke`
- Metric index rows: `4200`

## Evaluator Status

| system | status | count |
| --- | --- | --- |
| alphalens_reloaded | pass | 20 |
| jqfactor_analyzer | partial_pass | 20 |
| qlib_eval | pass | 20 |

## Context Status

| status | count |
| --- | --- |
| pass | 240 |
| skipped_non_informative | 80 |

## External Factor Coverage

| factor | valid_rows | total_rows | coverage |
| --- | --- | --- | --- |
| alpha158_KMID | 824291 | 824291 | 1.000000 |
| alpha158_KLEN | 824291 | 824291 | 1.000000 |
| alpha158_KMID2 | 824291 | 824291 | 1.000000 |
| alpha158_KUP | 824291 | 824291 | 1.000000 |
| alpha158_KUP2 | 824291 | 824291 | 1.000000 |
| alpha158_KLOW | 824291 | 824291 | 1.000000 |
| alpha158_KLOW2 | 824291 | 824291 | 1.000000 |
| alpha158_KSFT | 824291 | 824291 | 1.000000 |
| alpha158_KSFT2 | 824291 | 824291 | 1.000000 |
| alpha158_OPEN0 | 824291 | 824291 | 1.000000 |
| alpha158_HIGH0 | 824291 | 824291 | 1.000000 |
| alpha158_LOW0 | 824291 | 824291 | 1.000000 |
| alpha158_VWAP0 | 824291 | 824291 | 1.000000 |
| alpha158_ROC5 | 823397 | 824291 | 0.998915 |
| alpha158_ROC10 | 822935 | 824291 | 0.998355 |
| alpha158_ROC20 | 822913 | 824291 | 0.998328 |
| alpha158_ROC30 | 822893 | 824291 | 0.998304 |
| alpha158_ROC60 | 822776 | 824291 | 0.998162 |
| alpha158_MA5 | 824291 | 824291 | 1.000000 |
| alpha158_MA10 | 824291 | 824291 | 1.000000 |

## Mean IC Snapshot

| system | factor | horizon | metric | value |
| --- | --- | --- | --- | --- |
| alphalens_reloaded | alpha158_ROC60 | 10D | mean_information_coefficient | 0.065208 |
| alphalens_reloaded | alpha158_KLEN | 10D | mean_information_coefficient | -0.062591 |
| alphalens_reloaded | alpha158_ROC30 | 10D | mean_information_coefficient | 0.060496 |
| alphalens_reloaded | alpha158_KUP | 10D | mean_information_coefficient | -0.043388 |
| alphalens_reloaded | alpha158_ROC20 | 10D | mean_information_coefficient | 0.042715 |
| alphalens_reloaded | alpha158_HIGH0 | 10D | mean_information_coefficient | -0.039927 |
| alphalens_reloaded | alpha158_LOW0 | 10D | mean_information_coefficient | 0.039788 |
| alphalens_reloaded | alpha158_KLOW | 10D | mean_information_coefficient | -0.034812 |
| alphalens_reloaded | alpha158_ROC10 | 10D | mean_information_coefficient | 0.033251 |
| alphalens_reloaded | alpha158_MA10 | 10D | mean_information_coefficient | 0.029219 |
| alphalens_reloaded | alpha158_ROC5 | 10D | mean_information_coefficient | 0.026074 |
| alphalens_reloaded | alpha158_MA5 | 10D | mean_information_coefficient | 0.017176 |
| alphalens_reloaded | alpha158_KMID | 10D | mean_information_coefficient | -0.012212 |
| alphalens_reloaded | alpha158_OPEN0 | 10D | mean_information_coefficient | 0.012212 |
| alphalens_reloaded | alpha158_KUP2 | 10D | mean_information_coefficient | -0.011183 |
| alphalens_reloaded | alpha158_KMID2 | 10D | mean_information_coefficient | -0.008635 |
| alphalens_reloaded | alpha158_KSFT2 | 10D | mean_information_coefficient | -0.003599 |
| alphalens_reloaded | alpha158_KSFT | 10D | mean_information_coefficient | -0.002177 |
| alphalens_reloaded | alpha158_VWAP0 | 10D | mean_information_coefficient | 0.000972 |
| alphalens_reloaded | alpha158_KLOW2 | 10D | mean_information_coefficient | 0.000306 |
| alphalens_reloaded | alpha158_ROC60 | 20D | mean_information_coefficient | 0.083509 |
| alphalens_reloaded | alpha158_ROC30 | 20D | mean_information_coefficient | 0.080597 |
| alphalens_reloaded | alpha158_KLEN | 20D | mean_information_coefficient | -0.077333 |
| alphalens_reloaded | alpha158_ROC20 | 20D | mean_information_coefficient | 0.058682 |
| alphalens_reloaded | alpha158_KUP | 20D | mean_information_coefficient | -0.049112 |
| alphalens_reloaded | alpha158_HIGH0 | 20D | mean_information_coefficient | -0.049053 |
| alphalens_reloaded | alpha158_LOW0 | 20D | mean_information_coefficient | 0.048481 |
| alphalens_reloaded | alpha158_KLOW | 20D | mean_information_coefficient | -0.045397 |
| alphalens_reloaded | alpha158_ROC10 | 20D | mean_information_coefficient | 0.034488 |
| alphalens_reloaded | alpha158_MA10 | 20D | mean_information_coefficient | 0.024459 |
| alphalens_reloaded | alpha158_ROC5 | 20D | mean_information_coefficient | 0.019751 |
| alphalens_reloaded | alpha158_MA5 | 20D | mean_information_coefficient | 0.012760 |
| alphalens_reloaded | alpha158_KMID | 20D | mean_information_coefficient | -0.009878 |
| alphalens_reloaded | alpha158_OPEN0 | 20D | mean_information_coefficient | 0.009878 |
| alphalens_reloaded | alpha158_KUP2 | 20D | mean_information_coefficient | -0.008785 |
| alphalens_reloaded | alpha158_KMID2 | 20D | mean_information_coefficient | -0.005482 |
| alphalens_reloaded | alpha158_KSFT2 | 20D | mean_information_coefficient | -0.003554 |
| alphalens_reloaded | alpha158_KLOW2 | 20D | mean_information_coefficient | -0.002889 |
| alphalens_reloaded | alpha158_VWAP0 | 20D | mean_information_coefficient | 0.002391 |
| alphalens_reloaded | alpha158_KSFT | 20D | mean_information_coefficient | -0.002134 |

## Failure Counts

| system | step | count |
| --- | --- | --- |
| jqfactor_analyzer | factor_alpha_beta | 20 |
| jqfactor_analyzer | factor_returns | 20 |

## Notes

- This summary does not create a combined score.
- jqfactor_analyzer partial-pass is expected in the current pandas 2.x environment for known factor-return and alpha/beta steps.
- Context metrics remain separated from raw open-source metrics.
