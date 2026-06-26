# Alpha158 Candidate Expression Frame Validation V1

- Minimum coverage threshold: `0.99`

## Status

| check | status | detail |
| --- | --- | --- |
| factor_count_matches_candidates | pass | factor_columns=14, candidates=14 |
| all_candidates_present | pass |  |
| no_unexpected_factors | pass |  |
| duplicate_datetime_instrument | pass | 0 |
| date_range_non_empty | pass | 2024-01-02 00:00:00 to 2026-06-09 00:00:00 |
| date_range_inside_config | pass | 2024-01-02 00:00:00 to 2026-06-09 00:00:00; config=2024-01-01 to 2026-06-09 |
| min_factor_coverage | pass | 0.9958977624241606 |

## Coverage

| factor | valid_rows | total_rows | coverage | missing_rate | first_valid_date | last_valid_date |
| --- | --- | --- | --- | --- | --- | --- |
| alpha158_MIN60 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_QTLD60 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_ROC60 | 1091903 | 1096231 | 0.996052 | 0.003948 | 2024-01-02 | 2026-06-09 |
| alpha158_MIN30 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_ROC30 | 1091734 | 1096231 | 0.995898 | 0.004102 | 2024-01-02 | 2026-06-09 |
| alpha158_QTLD30 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_IMIN60 | 1096215 | 1096231 | 0.999985 | 0.000015 | 2024-01-02 | 2026-06-09 |
| alpha158_MIN10 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_IMIN30 | 1095986 | 1096231 | 0.999777 | 0.000223 | 2024-01-02 | 2026-06-09 |
| alpha158_MIN5 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_IMIN20 | 1095763 | 1096231 | 0.999573 | 0.000427 | 2024-01-02 | 2026-06-09 |
| alpha158_QTLD10 | 1093663 | 1096231 | 0.997657 | 0.002343 | 2024-01-02 | 2026-06-09 |
| alpha158_VSUMN60 | 1096214 | 1096231 | 0.999984 | 0.000016 | 2024-01-02 | 2026-06-09 |
| alpha158_ROC10 | 1091859 | 1096231 | 0.996012 | 0.003988 | 2024-01-02 | 2026-06-09 |

## Output Files

- `candidate_expression_validation_status.csv`
- `candidate_expression_validation_coverage.csv`
- `candidate_expression_validation_report.md`
