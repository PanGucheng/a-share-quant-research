# Research Data Contracts V1

Pandera-backed, read-only validation for current compact research outputs. New label and universe outputs must use explicit point-in-time fields; the legacy gaps below are compatibility exceptions, not waivers for new modules.

## Validation Results

| dataset_id | schema | status | row_count | column_count | validated_row_count | reason |
| --- | --- | --- | --- | --- | --- | --- |
| residualized_factor_frame | factor_frame | pass | 89000 | 48 | 89000 | schema validation passed |
| residualized_tradability_frame | tradability_frame | pass | 89000 | 48 | 89000 | schema validation passed |
| multi_source_screening | screening_frame | pass | 679 | 41 | 679 | schema validation passed |
| multi_source_judgement | judgement_frame | pass | 679 | 44 | 679 | schema validation passed |
| existing_factor_labels | label_frame | compatibility_exception | 0 | 0 | 0 | Existing factor frames encode labels by name and do not expose feature_time, label_start_time, and label_end_time columns; all new rolling-validation outputs must use the explicit label contract. |
| existing_static_liquid2000 | universe_interval | compatibility_exception | 0 | 0 | 0 | The current static liquid2000 universe is a text instrument list without selection/effective lineage; phase 2 replaces it only for the experimental PIT path. |

## Contract

| check_name | status | observed_value | required_value | severity | reason |
| --- | --- | --- | --- | --- | --- |
| configured_datasets | pass | 4 | >=4 | critical | Core factor, tradability, screening, and judgement frames must be audited. |
| dataset_validation_failures | pass | 0 | 0 | critical | Configured existing outputs must pass their applicable schemas. |
| compatibility_exceptions | warning | 2 | recorded | warning | Legacy label/universe gaps are explicitly scoped and cannot be inherited by new outputs. |
| schema_inventory_rows | pass | 181 | >0 | critical | Every audited dataset column must be inventoried. |
| input_lineage | pass | 4 | 4 | critical | Every validated input must have a SHA256 lineage hash. |
| existing_defaults_modified | pass | 0 | 0 | critical | Schema audit is read-only and does not modify source frames or defaults. |
