# Factor Evaluation Batch V1 Report

- Config: `configs/factor_evaluation_batch_v1_smoke.yaml`
- Dry run: `true`
- Batch count: `2`
- Total selected factors: `2`

## Batch Status

| status | batch_count |
| --- | --- |
| planned | 2 |

## Batch Manifest

| batch_id | status | factor_count | factors | output_dir |
| --- | --- | --- | --- | --- |
| batch_001 | planned | 1 | rev_5 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\smoke_dry_run\runs\batch_001 |
| batch_002 | planned | 1 | std_20 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\smoke_dry_run\runs\batch_002 |

## Output Summary

| batch_id | status | factor_count | factors | evaluator_status_rows | failure_rows | metric_rows | context_metric_rows | output_dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_001 | planned | 1 | rev_5 | 0 | 0 | 0 | 0 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\smoke_dry_run\runs\batch_001 |
| batch_002 | planned | 1 | std_20 | 0 | 0 | 0 | 0 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\smoke_dry_run\runs\batch_002 |

## Output Files

- `factor_catalog_snapshot.csv`
- `selected_factor_catalog.csv`
- `factor_catalog_validation.csv`
- `generated_configs/batch_*.yaml`
- `batch_manifest.csv`
- `batch_output_summary.csv`
- `logs/batch_*.stdout.log`
- `logs/batch_*.stderr.log`
