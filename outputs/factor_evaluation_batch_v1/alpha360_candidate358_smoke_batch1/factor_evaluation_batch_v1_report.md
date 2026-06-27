# Factor Evaluation Batch V1 Report

- Config: `configs/factor_evaluation_batch_v1_alpha360_candidate358_smoke.yaml`
- Dry run: `false`
- Batch count: `1`
- Total selected factors: `5`

## Batch Status

| status | batch_count |
| --- | --- |
| pass | 1 |

## Batch Manifest

| batch_id | status | factor_count | factors | output_dir |
| --- | --- | --- | --- | --- |
| batch_001 | pass | 5 | alpha360_CLOSE59,alpha360_CLOSE58,alpha360_CLOSE57,alpha360_CLOSE56,alpha360_CLOSE55 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha360_candidate358_smoke_batch1\runs\batch_001 |

## Output Summary

| batch_id | status | factor_count | factors | evaluator_status_rows | failure_rows | metric_rows | context_metric_rows | output_dir |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batch_001 | pass | 5 | alpha360_CLOSE59,alpha360_CLOSE58,alpha360_CLOSE57,alpha360_CLOSE56,alpha360_CLOSE55 | 15 | 10 | 90 | 0 | E:\qlib_prj\qlib_baseline\outputs\factor_evaluation_batch_v1\alpha360_candidate358_smoke_batch1\runs\batch_001 |

## Output Files

- `factor_catalog_snapshot.csv`
- `selected_factor_catalog.csv`
- `factor_catalog_validation.csv`
- `generated_configs/batch_*.yaml`
- `batch_manifest.csv`
- `batch_output_summary.csv`
- `logs/batch_*.stdout.log`
- `logs/batch_*.stderr.log`
