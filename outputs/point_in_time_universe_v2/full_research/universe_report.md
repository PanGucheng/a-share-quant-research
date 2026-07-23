# Point-In-Time Universe V2

- Profile: `full_research`
- Selection months: `65`
- Snapshot rows: `130000`
- Rolling interval rows: `6248`
- Lifecycle-clean interval rows: `6248`
- Corrected interval rows: `29`
- Removed illegal keys: `329`

| check_name | status | observed_value | required_value | severity | reason |
| --- | --- | --- | --- | --- | --- |
| point_in_time_audit | pass | pass | pass | critical | PIT lineage and intervals must be valid. |
| future_data_reference_count | pass | 0 | 0 | critical | No source date may exceed selection date. |
| invalid_interval_count | pass | 0 | 0 | critical | Intervals must satisfy the universe schema. |
| same_selection_effective_date_count | pass | 0 | 0 | critical | Membership must take effect on a later trading day. |
| qlib_instruments_load | pass | pass | pass | critical | Generated TSV must round-trip through the Qlib instrument file format. |
| historical_membership_mutation_count | pass | 0 | 0 | critical | Adding later observations must not change an earlier snapshot. |
| lifecycle_intersection_applied | pass | True | True | critical | Final membership must be the intersection of rolling-universe and source-lifecycle intervals. |
| lifecycle_violation_count | pass | 0 | 0 | critical | Every final membership interval must be contained in a source lifecycle interval. |
| overlapping_membership_interval_count | pass | 0 | 0 | critical | Final intervals for an instrument must not overlap. |
| removed_key_still_active_count | pass | 0 | 0 | critical | Every key removed by lifecycle intersection must be absent from final membership. |
| lifecycle_correction_interval_count | pass | 29 | >=0 | critical | Lifecycle corrections are evidence and do not fail an otherwise clean final universe. |
| removed_illegal_key_count | pass | 329 | >=0 | critical | Removed lifecycle-illegal keys must be disclosed. |
| selected_snapshot_rows | pass | 130000 | >0 | critical | At least one member snapshot is required. |
