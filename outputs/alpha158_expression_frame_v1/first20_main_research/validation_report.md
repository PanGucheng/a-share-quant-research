# Alpha158 Expression Frame Validation V1

## Status

| check | status | detail | matched_rows | max_abs_error |
| --- | --- | --- | --- | --- |
| duplicate_datetime_instrument | pass | 0 |  |  |
| alpha158_KMID_manual_formula | pass |  | 1598099.0 | 0.0 |
| alpha158_KLEN_manual_formula | pass |  | 1598099.0 | 0.0 |
| all_selected_factors_have_values | pass | 0 |  |  |

## Coverage

| factor | valid_rows | total_rows | coverage | status |
| --- | --- | --- | --- | --- |
| alpha158_KMID | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KLEN | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KMID2 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KUP | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KUP2 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KLOW | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KLOW2 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KSFT | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_KSFT2 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_OPEN0 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_HIGH0 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_LOW0 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_VWAP0 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_ROC5 | 1596064 | 1603860 | 0.995139 | pass |
| alpha158_ROC10 | 1595119 | 1603860 | 0.994550 | pass |
| alpha158_ROC20 | 1594613 | 1603860 | 0.994235 | pass |
| alpha158_ROC30 | 1594608 | 1603860 | 0.994231 | pass |
| alpha158_ROC60 | 1594671 | 1603860 | 0.994271 | pass |
| alpha158_MA5 | 1598099 | 1603860 | 0.996408 | pass |
| alpha158_MA10 | 1598099 | 1603860 | 0.996408 | pass |

## Missing Window Summary

| factor | first_valid_date | min_daily_coverage | mean_daily_coverage |
| --- | --- | --- | --- |
| alpha158_KMID | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KLEN | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KMID2 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KUP | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KUP2 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KLOW | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KLOW2 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KSFT | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_KSFT2 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_OPEN0 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_HIGH0 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_LOW0 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_VWAP0 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_ROC5 | 2020-10-09 | 0.968448 | 0.995167 |
| alpha158_ROC10 | 2020-10-09 | 0.966921 | 0.994580 |
| alpha158_ROC20 | 2020-10-09 | 0.967413 | 0.994264 |
| alpha158_ROC30 | 2020-10-09 | 0.970483 | 0.994260 |
| alpha158_ROC60 | 2020-10-09 | 0.969466 | 0.994300 |
| alpha158_MA5 | 2020-10-09 | 0.971501 | 0.996431 |
| alpha158_MA10 | 2020-10-09 | 0.971501 | 0.996431 |

## Output Files

- `validation_status.csv`
- `validation_factor_coverage.csv`
- `validation_manual_formula.csv`
- `validation_missing_window.csv`
